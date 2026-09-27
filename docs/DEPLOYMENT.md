# RecallScope deployment record

## Current state

RecallScope v0.1.0 is an undeployed development candidate. No chain address or deployment transaction is recorded. Do not treat another project's deployment as RecallScope evidence.

The optional label image is committed by raw-byte SHA-256 and sent through the documented `gl.nondet.exec_prompt(images=[...])` interface only after hash, size, and JPEG/PNG framing checks. Vision-provider support is an external runtime assumption and can cause a review to remain inconclusive. Escrow is intentionally excluded: a safety warning should not depend on payment, and no beneficiary is selected by the protocol.

## Pre-deployment release gate

From the RecallScope repository root, using Python 3.12+:

```powershell
python -m pip install -r requirements.txt
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/recallscope.py --json
genvm-lint schema contracts/recallscope.py --output artifacts/recallscope.abi.json
```

Freeze source only after every check passes. Record the source commit and SHA-256 before deployment. Deploy only with the user's explicit instruction, then record the finalized deployment transaction, contract address, `get_info()` result, and deployed-source byte-for-byte parity if source retrieval is supported.

## Live evidence

None yet. No live proposal, review, consumer acknowledgement, or source-parity claim is made.
