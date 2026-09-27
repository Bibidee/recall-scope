import base64
import hashlib
import json
import os
import tempfile
import threading
import time

import pytest


CONTRACT = "contracts/recallscope.py"
GENVM_VERSION = "v0.2.12"
PRODUCT_URL = "https://records.example.org/product.txt"
NOTICE_URL = "https://recalls.example.net/notice.txt"
IMAGE_URL = "https://records.example.org/label.png"
PRODUCT = b"Northstar kettle model K-17 batch B-204 was sold in market US-CA."
NOTICE = b"Recall notice: Northstar kettle model K-17 batch B-204 in US-CA must stop use due to an overheating hazard."
LABEL_IMAGE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a3ioAAAAASUVORK5CYII="
)


def _patch_windows_genlayer_test_temp_cleanup():
    """Defer SDK message-file deletion until Direct Mode restores fd 0 on Windows."""
    if os.name != "nt":
        return
    from gltest.direct import loader

    if getattr(loader, "_recallscope_windows_temp_patch", False):
        return

    def inject_message(vm):
        from genlayer.py import calldata
        from genlayer.py.types import Address

        sender = vm.sender
        if isinstance(sender, bytes):
            sender = Address(sender)
        contract_address = vm._contract_address
        if isinstance(contract_address, bytes):
            contract_address = Address(contract_address)
        origin = vm.origin
        if isinstance(origin, bytes):
            origin = Address(origin)
        encoded = calldata.encode({
            "contract_address": contract_address,
            "sender_address": sender,
            "origin_address": origin,
            "stack": [],
            "value": vm._value,
            "datetime": vm._datetime,
            "is_init": False,
            "chain_id": vm._chain_id,
            "entry_kind": 0,
            "entry_data": b"",
            "entry_stage_data": None,
        })
        fd, path = tempfile.mkstemp()
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
        finally:
            os.close(fd)

        def remove_after_stdin_restore():
            for _ in range(400):
                try:
                    os.unlink(path)
                    return
                except PermissionError:
                    time.sleep(0.025)

        threading.Thread(target=remove_after_stdin_restore, daemon=True).start()

    loader._inject_message_to_fd0 = inject_message
    loader._recallscope_windows_temp_patch = True


_patch_windows_genlayer_test_temp_cleanup()


def digest(raw):
    return "0x" + hashlib.sha256(raw).hexdigest()


def deployed(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    direct_vm.check_pickling = True
    return direct_deploy(CONTRACT, sdk_version=GENVM_VERSION)


def submit(contract, direct_alice, direct_bob, case_id="case-1", product=PRODUCT, notice=NOTICE,
           product_url=PRODUCT_URL, notice_url=NOTICE_URL, summary="Recall scope fixture",
           label_image=b""):
    contract.submit_case(
        case_id,
        "Northstar kettle",
        "K-17",
        "B-204",
        "US-CA",
        direct_bob,
        product_url,
        digest(product),
        notice_url,
        digest(notice),
        IMAGE_URL if label_image else "",
        digest(label_image) if label_image else "",
        summary,
    )


def mocks(direct_vm, result=None, product=PRODUCT, notice=NOTICE, product_status=200, notice_status=200,
          label_image=None, image_status=200):
    direct_vm.mock_web(r"records\.example\.org/product\.txt", {"status": product_status, "body": product})
    direct_vm.mock_web(r"recalls\.example\.net/notice\.txt", {"status": notice_status, "body": notice})
    if label_image is not None:
        direct_vm.mock_web(r"records\.example\.org/label\.png", {"status": image_status, "body": label_image})
    if result is None:
        result = {
            "applicability": "applies",
            "required_action": "stop_use",
            "confidence": 93,
            "rationale": "The notice covers the exact model, batch, and US-CA market and directs users to stop use.",
        }
    direct_vm.mock_llm(r"Return exactly one JSON object with keys applicability", json.dumps(result))


def test_submit_read_scope_and_info(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    row = contract.get_case("case-1", direct_alice)
    assert row["status"] == "pending"
    assert row["proposer"].lower() == ("0x" + direct_alice.hex()).lower()
    assert row["consumer"].lower() == ("0x" + direct_bob.hex()).lower()
    assert row["product_record_hash"] == digest(PRODUCT)
    assert row["recall_notice_hash"] == digest(NOTICE)
    assert row["label_image_url"] == ""
    assert row["label_image_hash"] == ""
    assert row["confidence"] == 0
    assert row["rationale"] == ""
    assert contract.is_action_required_for("case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA") is False
    assert contract.get_info()["version"] == "0.1.0"


def test_unknown_case_fails(direct_vm, direct_deploy, direct_alice):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Recall case not found"):
        contract.get_case("missing", direct_alice)


@pytest.mark.parametrize("case_id", ["", "bad id", "../case", "x" * 97])
def test_invalid_id_rejected(direct_vm, direct_deploy, direct_alice, direct_bob, case_id):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Invalid case_id"):
        submit(contract, direct_alice, direct_bob, case_id=case_id)


def test_duplicate_id_is_rejected_per_submitter_and_namespaced(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    with direct_vm.expect_revert("Case unavailable"):
        submit(contract, direct_alice, direct_bob)
    with direct_vm.prank(direct_bob):
        submit(contract, direct_bob, direct_alice)
    assert contract.get_case("case-1", direct_bob)["status"] == "pending"


@pytest.mark.parametrize("url", [
    "http://records.example.org/a", "https://localhost/a", "https://127.0.0.1/a",
    "https://10.0.0.1/a", "https://192.168.1.2/a", "https://172.16.0.3/a",
    "https://[::1]/a", "https://user@records.example.org/a", "https://records.example.org:8443/a",
    "https://service.internal/a", "https://records.example.org/a#frag",
])
def test_unsafe_url_rejected(direct_vm, direct_deploy, direct_alice, direct_bob, url):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert():
        submit(contract, direct_alice, direct_bob, product_url=url)


@pytest.mark.parametrize("bad_hash", ["", "0x12", "0x" + "G" * 64])
def test_bad_hash_rejected(direct_vm, direct_deploy, direct_alice, direct_bob, bad_hash):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Invalid SHA-256"):
        contract.submit_case("case-1", "Kettle", "K-17", "B-204", "US-CA", direct_bob,
                             PRODUCT_URL, bad_hash, NOTICE_URL, digest(NOTICE), "", "", "summary")


def test_zero_consumer_and_blank_or_oversized_text_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("Zero consumer"):
        submit(contract, direct_alice, bytes(20))
    for value in ("", "  \n", "x" * 321):
        with direct_vm.expect_revert("Invalid summary"):
            submit(contract, direct_alice, direct_bob, summary=value)


def test_valid_approved_semantic_review_and_designated_acknowledgement(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm)
    contract.review_case("case-1", direct_alice)
    row = contract.get_case("case-1", direct_alice)
    assert row["status"] == "recall_applies"
    assert row["required_action"] == "stop_use"
    assert row["confidence"] == 93
    assert contract.is_action_required_for("case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA") is True
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("Designated consumer only"):
            contract.acknowledge_action("case-1", direct_alice)
    with direct_vm.prank(direct_bob):
        contract.acknowledge_action("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "acknowledged"
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("No unacknowledged"):
            contract.acknowledge_action("case-1", direct_alice)


def test_hash_verified_label_image_can_be_included_in_vision_review(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob, label_image=LABEL_IMAGE)
    mocks(direct_vm, label_image=LABEL_IMAGE)
    contract.review_case("case-1", direct_alice)
    row = contract.get_case("case-1", direct_alice)
    assert row["status"] == "recall_applies"
    assert row["label_image_hash"] == digest(LABEL_IMAGE)


def test_label_image_hash_mismatch_fails_closed(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob, label_image=LABEL_IMAGE)
    mocks(direct_vm, label_image=LABEL_IMAGE + b"tampered")
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"


@pytest.mark.parametrize("image,image_status", [
    (LABEL_IMAGE, 404),
    (b"", 200),
    (b"not an image", 200),
    (b"\x89PNG\r\n\x1a\n" + b"x" * 1000001, 200),
], ids=["http-error", "empty", "invalid-format", "oversized"])
def test_bad_label_image_never_authorizes(direct_vm, direct_deploy, direct_alice, direct_bob, image, image_status):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob, label_image=LABEL_IMAGE)
    mocks(direct_vm, label_image=image, image_status=image_status)
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"


def test_image_url_and_hash_must_be_committed_together(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    with direct_vm.expect_revert("provided together"):
        contract.submit_case("case-1", "Kettle", "K-17", "B-204", "US-CA", direct_bob,
                             PRODUCT_URL, digest(PRODUCT), NOTICE_URL, digest(NOTICE), IMAGE_URL, "", "summary")


@pytest.mark.parametrize("result,expected", [
    ({"applicability": "not_applicable", "required_action": "none", "confidence": 92, "rationale": "Batch excluded."}, "not_applicable"),
    ({"applicability": "unclear", "required_action": "unclear", "confidence": 95, "rationale": "Region unclear."}, "inconclusive"),
    ({"applicability": "applies", "required_action": "stop_use", "confidence": 74, "rationale": "Below threshold."}, "inconclusive"),
])
def test_non_authorizing_results(direct_vm, direct_deploy, direct_alice, direct_bob, result, expected):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm, result=result)
    contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == expected
    assert contract.is_action_required_for("case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA") is False


@pytest.mark.parametrize("result", [
    {"applicability": "applies", "required_action": "stop_use", "confidence": 95},
    {"applicability": "applies", "required_action": "stop_use", "confidence": 95, "rationale": "ok", "extra": 1},
    {"applicability": "yes", "required_action": "stop_use", "confidence": 95, "rationale": "ok"},
    {"applicability": "applies", "required_action": "stop_use", "confidence": True, "rationale": "ok"},
    {"applicability": "applies", "required_action": "stop_use", "confidence": 101, "rationale": "ok"},
    {"applicability": "applies", "required_action": "none", "confidence": 95, "rationale": "Contradiction."},
    {"applicability": "applies", "required_action": "stop_use", "confidence": 95, "rationale": " "},
    {"applicability": "applies", "required_action": "stop_use", "confidence": 95, "rationale": "x" * 401},
])
def test_malformed_model_output_never_approves(direct_vm, direct_deploy, direct_alice, direct_bob, result):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm, result=result)
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"
    assert contract.is_action_required_for("case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA") is False


@pytest.mark.parametrize("product,notice,product_status,notice_status", [
    (PRODUCT, NOTICE, 503, 200), (PRODUCT, NOTICE, 200, 404),
    (b"", NOTICE, 200, 200), (PRODUCT, b"", 200, 200),
    (b"x" * 16001, NOTICE, 200, 200), (PRODUCT, b"x" * 16001, 200, 200),
    (b"\xff", NOTICE, 200, 200), (PRODUCT, b"\xff", 200, 200),
], ids=["product-http-error", "notice-http-error", "empty-product",
        "empty-notice", "oversized-product", "oversized-notice", "invalid-utf8-product",
        "invalid-utf8-notice"])
def test_artifact_failures_never_approve(direct_vm, direct_deploy, direct_alice, direct_bob, product, notice, product_status, notice_status):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob, product=product, notice=notice)
    mocks(direct_vm, product=product, notice=notice, product_status=product_status, notice_status=notice_status)
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"


def test_artifact_hash_mismatch_never_authorizes(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm, product=b"different bytes than the committed product record")
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"


def test_hash_mismatch_does_not_mutate_pending_case(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm, product=b"different committed bytes")
    with direct_vm.expect_revert():
        contract.review_case("case-1", direct_alice)
    assert contract.get_case("case-1", direct_alice)["status"] == "pending"


def test_validator_must_agree_on_final_decision_and_applied_action(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    leader = {"applicability": "applies", "required_action": "stop_use", "confidence": 95, "rationale": "Overheating hazard."}
    mocks(direct_vm, result=leader)
    contract.review_case("case-1", direct_alice)
    direct_vm.clear_mocks()
    mocks(direct_vm, result={"applicability": "applies", "required_action": "repair", "confidence": 95, "rationale": "Repair is sufficient."})
    assert direct_vm.run_validator() is False


def test_validator_different_not_applicable_reasons_remain_safe_equivalence(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm, result={"applicability": "not_applicable", "required_action": "none", "confidence": 92, "rationale": "Different model."})
    contract.review_case("case-1", direct_alice)
    direct_vm.clear_mocks()
    mocks(direct_vm, result={"applicability": "not_applicable", "required_action": "none", "confidence": 81, "rationale": "Different batch."})
    assert direct_vm.run_validator() is True
    assert contract.get_case("case-1", direct_alice)["status"] == "not_applicable"


def test_cancel_pending_only_and_review_only_once(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert():
            contract.cancel_case("case-1")
    contract.cancel_case("case-1")
    assert contract.get_case("case-1", direct_alice)["status"] == "cancelled"
    with direct_vm.expect_revert("Case is not reviewable"):
        contract.review_case("case-1", direct_alice)
    with direct_vm.expect_revert("Only proposer"):
        contract.cancel_case("case-1")
