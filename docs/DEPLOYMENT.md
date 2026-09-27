# RecallScope deployment record

## Current deployment: v0.1.0 on Studionet

- Contract: [0x58117a2D5a6332dDe2e303a5128D939c54270664](https://explorer-studio.genlayer.com/address/0x58117a2D5a6332dDe2e303a5128D939c54270664)
- Deployment transaction: [0x2db9b6d748c185bd7767ffaeade07235d114de86ec4745228b445a822100e32e](https://explorer-studio.genlayer.com/tx/0x2db9b6d748c185bd7767ffaeade07235d114de86ec4745228b445a822100e32e)
- Network: GenLayer Studionet
- Finality: `FINALIZED`
- Consensus: `MAJORITY_AGREE`
- Leader GenVM execution: `SUCCESS`
- Deployment source commit: `5e50bb34719d6bc799f924abbcc4c743bf3699d3`
- Local and deployed source SHA-256: `b0bf0ed02d5e13aec238af3e88cfd5cc5e464ff7c4358d7d1c34e6a402465d31`
- Local and deployed source length: 24,023 bytes each; byte-for-byte comparison: **MATCH**
- `get_info()`: `name=RecallScope`, `version=0.1.0`, `minimum_confidence=75`, `max_artifact_bytes=16000`, `max_label_image_bytes=1000000`, `max_cases_per_submitter_lifetime=64`

Deployment evidence does not demonstrate application lifecycle behavior. No live case submission, semantic review, or consumer acknowledgement is recorded yet.

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

## Live application evidence

None yet. No live case proposal, review, or consumer acknowledgement has been executed. The source-parity proof above is limited to the deployed source comparison.
