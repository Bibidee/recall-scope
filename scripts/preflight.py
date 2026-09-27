"""Fail-closed release gate for the RecallScope standalone contract."""

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "recallscope.py"
EXPECTED_SOURCES = {"recallscope.py"}
os.environ["GENVM_VERSION"] = "v0.2.12"


def run(command):
    print("+", " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


sources = {path.name for path in (ROOT / "contracts").glob("*.py")}
if sources != EXPECTED_SOURCES:
    raise SystemExit(f"Expected exactly one deployable source {sorted(EXPECTED_SOURCES)}, got {sorted(sources)}")

source = CONTRACT.read_text(encoding="utf-8")
ast.parse(source, filename=str(CONTRACT))
required = (
    'VERSION = "0.1.0"',
    "hashlib.sha256(raw).hexdigest()",
    "def fetch_verified(",
    "def fetch_verified_image(",
    'gl.nondet.exec_prompt(prompt, response_format="json")',
    "gl.vm.run_nondet_unsafe(leader, validator)",
    "class RecallScope(gl.Contract):",
    'MIN_CONFIDENCE = 75',
    "MAX_CASES_PER_SUBMITTER = 64",
    "def acknowledge_action(",
    "def is_action_required_for(",
    "images=[label_image[\"bytes\"]]",
)
missing = [token for token in required if token not in source]
if missing:
    raise SystemExit(f"Contract invariant markers missing: {missing}")
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
run([lint, "check", str(CONTRACT), "--json"])
schema_path = artifacts / "recallscope.abi.json"
run([lint, "schema", str(CONTRACT), "--output", str(schema_path)])
schema = json.loads(schema_path.read_text(encoding="utf-8"))
if not isinstance(schema, dict) or not schema:
    raise SystemExit("ABI/schema output is empty or unexpected")
print("RecallScope preflight PASS: one contract source, syntax, Direct Mode, GenVM lint and ABI/schema")
print("Contract SHA-256:", hashlib.sha256(CONTRACT.read_bytes()).hexdigest())
