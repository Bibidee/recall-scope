"""Fail-closed release gate for RecallScope and its authority registry."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {
    "recallscope.py": ROOT / "contracts" / "recallscope.py",
    "authority_registry.py": ROOT / "contracts" / "authority_registry.py",
}
EXPECTED_SOURCES = set(CONTRACTS)
os.environ["GENVM_VERSION"] = "v0.2.12"


def run(command):
    print("+", " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


sources = {path.name for path in (ROOT / "contracts").glob("*.py")}
if sources != EXPECTED_SOURCES:
    raise SystemExit(f"Expected exactly these deployable sources {sorted(EXPECTED_SOURCES)}, got {sorted(sources)}")

required_markers = {
    "recallscope.py": (
        'VERSION = "0.2.0"',
        "hashlib.sha256(raw).hexdigest()",
        "def fetch_verified(",
        "def fetch_verified_image(",
        'gl.nondet.exec_prompt(prompt, response_format="json")',
        "gl.vm.run_nondet_unsafe(leader, validator)",
        "class RecallScope(gl.Contract):",
        "def submit_authority_bound_case(",
        "def is_authoritative_action_required_for(",
        "rsa_pkcs1_v15_sha256_verify(",
        'images=[label_image["bytes"]]',
    ),
    "authority_registry.py": (
        'VERSION = "0.2.0"',
        "MAX_AUTHORITIES = 32",
        "class RecallAuthorityRegistry(gl.Contract):",
        "def register_authority(",
        "def revoke_authority(",
    ),
}
for name, contract in CONTRACTS.items():
    source = contract.read_text(encoding="utf-8")
    ast.parse(source, filename=str(contract))
    missing = [token for token in required_markers[name] if token not in source]
    if missing:
        raise SystemExit(f"{name} invariant markers missing: {missing}")
    if "import pytest" in source or "from pytest" in source:
        raise SystemExit("Test dependencies must not appear in deployable source")

lint = shutil.which("genvm-lint") or shutil.which("genvm-lint.exe")
if lint is None:
    executable = "genvm-lint.exe" if sys.platform == "win32" else "genvm-lint"
    for candidate in (Path(sys.executable).parent / executable, Path(sys.executable).parent / "Scripts" / executable):
        if candidate.exists():
            lint = str(candidate)
            break
if lint is None:
    raise SystemExit("genvm-lint not found; install pinned requirements; lint is required")

run([sys.executable, "-m", "compileall", "-q", str(ROOT / "contracts")])
run([sys.executable, "-m", "pytest", "tests/direct", "-q"])
artifacts = ROOT / "artifacts"
artifacts.mkdir(exist_ok=True)
for name, contract in CONTRACTS.items():
    run([lint, "check", str(contract), "--json"])
    schema_path = artifacts / (name.removesuffix(".py") + ".abi.json")
    run([lint, "schema", str(contract), "--output", str(schema_path)])
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict) or not schema:
        raise SystemExit(f"ABI/schema output is empty or unexpected for {name}")
    print(name + " SHA-256:", hashlib.sha256(contract.read_bytes()).hexdigest())
print("RecallScope preflight PASS: two contract sources, syntax, Direct Mode, GenVM lint and both ABI schemas")
