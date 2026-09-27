import base64
import hashlib
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone

import pytest


CONTRACT = "contracts/recallscope.py"
REGISTRY = "contracts/authority_registry.py"
TEST_REGISTRY_ADDRESS = bytes.fromhex("99" * 20)
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
    return direct_deploy(CONTRACT, TEST_REGISTRY_ADDRESS, sdk_version=GENVM_VERSION)


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


# Synthetic-only 2048-bit RSA key. The private exponent is a test fixture, never a production authority key.
TEST_RSA_N = "d28cf61a568751cf8fd04c1fcdd2add57a93287ab9c76f05754726e60ff2515d0e07ad6c9a0b0017613764516aaf4f24fe2d83f3f925e4278c9ba65809472cc8c3ff963e045dd7b254381ad9998ba135f07367c1dfbf2ba818117af8ed09a2e7776bae855130e8a9f886b1f489345748981e18f1bd6070bfd70cd1bc350e327b150cc314190dc70f17537baf9201202e46f8f84ed974a4657713cd78d4fee76cb27757b979ea3a090d6a6124953b6695d85c5c16a2a7a2d49cd183fff901fed6064c2795a8952b14e733c9d47acdb1782b5f7340817cd4d61a1a2d31f59b2f92b89e999fd4fe5df3cf8e968294485dc4806ac77a917a898dbbdbc550e6b3b617"
TEST_RSA_D = "576bb5c74bc415c0d39a8df0ea999e19b43223ad8933783250f680fd2703daaa8367c6a6fff2af5005ca64f9b50d23145e00f1f7bbabf2e644e85f91d0106054dfa460725187d14636d7b0b6469d860b0a5230737bfe39172b1f1eeafa28751e1c2476aade022ba85f0b361a2d59b11ff0211704503819b85d86f2126e08fe0601e73421afe9c6a62d41146fe66d9cb9b6ba4fe919da197ee5b281ce8bd60dadd57cec069bad9baba850ebc79fc1a0c6ea8eea41accf158a02285e8c9f0b28050c27b8ae1aa738c21ebd7f858e18f454c439d11f235c89fc0c7e4a5170b73bc0337e66be8dccd4e1137488f69399b00a872e1a7d1b103d773383fa4dcd021349"
AUTHORITY_ID = "DEMO-REGULATOR-01"
NOTICE_DOMAIN = "recalls.example.net"


def _test_manifest_bytes(direct_vm, case_id, revision, notice_hash, product_name, model, batch, market, issued, expires, reference, registry_address=TEST_REGISTRY_ADDRESS):
    fields = [
        "RECALLSCOPE_AUTHORITY_MANIFEST_V1",
        str(direct_vm._chain_id),
        "0x" + direct_vm._contract_address.hex(),
        "0x" + registry_address.hex(),
        case_id,
        AUTHORITY_ID,
        str(revision),
        notice_hash.lower(),
        product_name,
        model,
        batch,
        market,
        str(issued),
        str(expires),
        reference,
    ]
    return b"".join(str(len(value.encode("utf-8"))).encode("ascii") + b":" + value.encode("utf-8") for value in fields)


def _test_signature(message):
    digest_hex = hashlib.sha256(message).hexdigest()
    digest_info = "3031300d060960864801650304020105000420" + digest_hex
    encoded_hex = "0001" + ("ff" * ((512 - 6 - len(digest_info)) // 2)) + "00" + digest_info
    signature_value = pow(int(encoded_hex, 16), int(TEST_RSA_D, 16), int(TEST_RSA_N, 16))
    return "0x" + format(signature_value, "0512x")


def _authority_record(active=True, **overrides):
    import hashlib

    record = {
        "authority_id": AUTHORITY_ID,
        "name": "Synthetic Demo Safety Office",
        "signer_modulus": "0x" + TEST_RSA_N,
        "signer_fingerprint": "0x" + hashlib.sha256(TEST_RSA_N.encode("ascii")).hexdigest(),
        "domains": NOTICE_DOMAIN,
        "markets": "US-CA",
        "products": "Northstar kettle",
        "active": active,
        "revision": 1,
        "created_at": 1,
        "revoked_at": 0,
    }
    record.update(overrides)
    return record


def _install_authority(contract, record):
    contract._registry_authority = lambda authority_id: record if record.get("authority_id") == authority_id else {}


def _submit_authority_case(direct_vm, contract, direct_bob, case_id="authority-case-1", **overrides):
    product_name = overrides.get("product_name", "Northstar kettle")
    model = overrides.get("model", "K-17")
    batch = overrides.get("batch", "B-204")
    market = overrides.get("market", "US-CA")
    notice_hash = overrides.get("notice_hash", digest(NOTICE))
    issued = overrides.get("issued", int(time.time()) - 10)
    expires = overrides.get("expires", int(time.time()) + 86400)
    reference = overrides.get("recall_reference", "DEMO-RECALL-001")
    registry_address = overrides.get("registry_address", TEST_REGISTRY_ADDRESS)
    signature = overrides.get("signature") or _test_signature(
        _test_manifest_bytes(direct_vm, case_id, overrides.get("revision", 1), notice_hash,
                             product_name, model, batch, market, issued, expires, reference,
                             registry_address=registry_address)
    )
    contract.submit_authority_bound_case(
        case_id, product_name, model, batch, market, direct_bob,
        PRODUCT_URL, digest(PRODUCT), NOTICE_URL, notice_hash, "", "",
        "Synthetic demo-only authority-bound fixture.",
        overrides.get("authority_id", AUTHORITY_ID), reference, issued, expires, signature,
    )
    return signature


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
    assert contract.get_info()["version"] == "0.2.0"


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


def test_registry_is_admin_managed_bounded_and_revocation_is_irreversible(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    registry = direct_deploy(REGISTRY, sdk_version=GENVM_VERSION)
    modulus = "0x" + TEST_RSA_N
    args = (AUTHORITY_ID, "Synthetic Demo Safety Office", modulus, NOTICE_DOMAIN, "US-CA", "Northstar kettle")
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("administrator only"):
            registry.register_authority(*args)
    with direct_vm.prank(direct_alice):
        registry.register_authority(*args)
        with direct_vm.expect_revert("already registered"):
            registry.register_authority(*args)
        registry.revoke_authority(AUTHORITY_ID)
        with direct_vm.expect_revert("Active authority not found"):
            registry.revoke_authority(AUTHORITY_ID)
    record = registry.get_authority(AUTHORITY_ID)
    assert record["active"] is False
    assert record["revision"] == 1
    assert record["domains"] == NOTICE_DOMAIN
    assert registry.get_info()["revocation_irreversible"] is True


def test_authority_bound_manifest_is_verified_and_stronger_helper_requires_active_registry(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    pending = contract.get_case("authority-case-1", direct_alice)
    assert pending["evidence_mode"] == "AUTHORITY_BOUND"
    assert pending["authority_id"] == AUTHORITY_ID
    assert pending["authority_signer_fingerprint"] == _authority_record()["signer_fingerprint"]
    assert pending["authority_verified"] is True
    assert pending["signed_notice_hash"] == digest(NOTICE)
    assert pending["manifest_hash"].startswith("0x")
    assert pending["manifest_signature"].startswith("0x")
    mocks(direct_vm)
    contract.review_case("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "recall_applies"
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is True
    _install_authority(contract, _authority_record(active=False))
    assert contract.is_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False


def test_open_evidence_positive_never_satisfies_authority_helper(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    submit(contract, direct_alice, direct_bob)
    mocks(direct_vm)
    contract.review_case("case-1", direct_alice)
    assert contract.is_action_required_for("case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA") is True
    assert contract.is_authoritative_action_required_for(
        "case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False
    assert contract.get_case("case-1", direct_alice)["evidence_mode"] == "OPEN_EVIDENCE"


@pytest.mark.parametrize("record,overrides,error", [
    (None, {}, "Unknown authority"),
    ({"active": False}, {}, "inactive or revoked"),
    ({"authority_id": "OTHER"}, {}, "Unknown authority"),
    ({"products": "Northstar kettle"}, {"product_name": "Other product"}, "Product is outside"),
    ({"markets": "US-CA"}, {"market": "GB"}, "Market is outside"),
])
def test_authority_scope_and_registry_fail_closed(direct_vm, direct_deploy, direct_alice, direct_bob, record, overrides, error):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    configured = {} if record is None else _authority_record(**record)
    _install_authority(contract, configured)
    with direct_vm.expect_revert(error):
        _submit_authority_case(direct_vm, contract, direct_bob, **overrides)
    assert contract.get_submitter_case_count(direct_alice) == 0


def test_proposer_cannot_self_register_and_domain_scope_is_exact(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, {})
    with direct_vm.expect_revert("Unknown authority"):
        _submit_authority_case(direct_vm, contract, direct_bob)
    _install_authority(contract, _authority_record(domains="other.example.net"))
    with direct_vm.expect_revert("Notice domain"):
        _submit_authority_case(direct_vm, contract, direct_bob)


def test_forged_wrong_signer_and_mutated_manifest_are_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    bad_sig = "0x" + "11" * 256
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(direct_vm, contract, direct_bob, signature=bad_sig)

    wrong_modulus = "8" + TEST_RSA_N[1:]
    _install_authority(contract, _authority_record(signer_modulus="0x" + wrong_modulus))
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(direct_vm, contract, direct_bob)

    _install_authority(contract, _authority_record())
    normal_issued = int(time.time()) - 10
    normal_expires = int(time.time()) + 86400
    altered_manifest = _test_signature(_test_manifest_bytes(
        direct_vm, "authority-case-1", 1, digest(NOTICE), "Northstar kettle", "K-17",
        "B-204", "US-CA", normal_issued, normal_expires, "OTHER-REFERENCE",
    ))
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(direct_vm, contract, direct_bob, signature=altered_manifest)


def test_wrong_signed_notice_hash_malformed_signature_and_expiry_fail_closed(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    issued = int(time.time()) - 10
    expires = int(time.time()) + 86400
    signature_for_other_hash = _test_signature(_test_manifest_bytes(
        direct_vm, "authority-case-1", 1, digest(b"different notice"), "Northstar kettle", "K-17",
        "B-204", "US-CA", issued, expires, "DEMO-RECALL-001",
    ))
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(direct_vm, contract, direct_bob, signature=signature_for_other_hash)
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(direct_vm, contract, direct_bob, signature="0x1234")
    with direct_vm.expect_revert("expired"):
        _submit_authority_case(direct_vm, contract, direct_bob, expires=int(time.time()) - 1)


def test_manifest_signature_cannot_be_replayed_for_another_case_id(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    issued = int(time.time()) - 10
    expires = int(time.time()) + 86400
    signature = _submit_authority_case(
        direct_vm, contract, direct_bob, case_id="authority-case-1", issued=issued, expires=expires,
    )
    with direct_vm.expect_revert("Authority signature invalid"):
        _submit_authority_case(
            direct_vm, contract, direct_bob, case_id="authority-case-2", signature=signature,
            issued=issued, expires=expires,
        )


def test_stale_manifest_wrong_authority_id_and_missing_scope_are_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    with direct_vm.expect_revert("issue time"):
        _submit_authority_case(direct_vm, contract, direct_bob, issued=1)
    with direct_vm.expect_revert("Unknown authority"):
        _submit_authority_case(direct_vm, contract, direct_bob, authority_id="OTHER-AUTHORITY")
    with direct_vm.expect_revert("outside authority scope"):
        _install_authority(contract, _authority_record(products="Other product"))
        _submit_authority_case(direct_vm, contract, direct_bob)


@pytest.mark.parametrize("result,expected", [
    ({"applicability": "not_applicable", "required_action": "none", "confidence": 99, "rationale": "Scope excluded."}, "not_applicable"),
    ({"applicability": "applies", "required_action": "stop_use", "confidence": 74, "rationale": "Low confidence."}, "inconclusive"),
])
def test_authority_proof_does_not_override_non_authorizing_semantic_result(direct_vm, direct_deploy, direct_alice, direct_bob, result, expected):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    mocks(direct_vm, result=result)
    contract.review_case("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == expected
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False


def test_authority_revoked_after_submission_freezes_pending_case(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    _install_authority(contract, _authority_record(active=False))
    contract.review_case("authority-case-1", direct_alice)
    row = contract.get_case("authority-case-1", direct_alice)
    assert row["status"] == "authority_revoked"
    assert row["authority_status"] == "authority_revoked"
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False


def test_authority_scope_snapshot_cannot_be_silently_rewritten(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    original = _authority_record()
    _install_authority(contract, original)
    _submit_authority_case(direct_vm, contract, direct_bob)
    changed = _authority_record(domains="attacker.example.net", products="Other product")
    _install_authority(contract, changed)
    row = contract.get_case("authority-case-1", direct_alice)
    assert row["authority_domains_snapshot"] == NOTICE_DOMAIN
    assert row["authority_products_snapshot"] == "Northstar kettle"
    assert row["authority_status"] == "revoked_or_changed"
    contract.review_case("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "authority_revoked"


def test_authority_semantic_disagreement_still_fails_consensus(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    mocks(direct_vm, result={"applicability": "applies", "required_action": "stop_use", "confidence": 95, "rationale": "Stop use."})
    contract.review_case("authority-case-1", direct_alice)
    direct_vm.clear_mocks()
    mocks(direct_vm, result={"applicability": "applies", "required_action": "repair", "confidence": 95, "rationale": "Repair instead."})
    assert direct_vm.run_validator() is False
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "recall_applies"


def test_authority_bound_acknowledgement_is_designated_consumer_only(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    mocks(direct_vm)
    contract.review_case("authority-case-1", direct_alice)
    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("Designated consumer only"):
            contract.acknowledge_action("authority-case-1", direct_alice)
    with direct_vm.prank(direct_bob):
        contract.acknowledge_action("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "acknowledged"


def test_revocation_before_acknowledgement_blocks_authority_bound_action(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    _submit_authority_case(direct_vm, contract, direct_bob)
    mocks(direct_vm)
    contract.review_case("authority-case-1", direct_alice)
    _install_authority(contract, _authority_record(active=False))
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("Authority is no longer active"):
            contract.acknowledge_action("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "recall_applies"
    assert contract.is_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False


def test_manifest_expired_before_review_becomes_terminal_non_authorizing(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deployed(direct_vm, direct_deploy, direct_alice)
    _install_authority(contract, _authority_record())
    expires = int(time.time()) + 3600
    _submit_authority_case(direct_vm, contract, direct_bob, expires=expires)
    direct_vm._datetime = datetime.fromtimestamp(expires + 1, timezone.utc).isoformat().replace("+00:00", "Z")
    contract.review_case("authority-case-1", direct_alice)
    assert contract.get_case("authority-case-1", direct_alice)["status"] == "authority_expired"
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False
    _install_authority(contract, _authority_record(active=False))
    assert contract.is_authoritative_action_required_for(
        "authority-case-1", direct_alice, "Northstar kettle", "K-17", "B-204", "US-CA"
    ) is False
