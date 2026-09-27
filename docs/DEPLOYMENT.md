# RecallScope deployment record

## Current release candidate: v0.2.0 (not deployed)

The current source adds the authority registry and authority-bound evidence mode. It is not live yet. The v0.1.0 deployment and lifecycle below are historical and must not be represented as v0.2.0 evidence.

For release, deploy `RecallAuthorityRegistry` first, then deploy `RecallScope` with the registry address as its constructor argument. Use GenLayer Studionet chain ID `61999`, verify both deployments reach finality with successful GenVM execution, retrieve both deployed sources, and compare their exact bytes and SHA-256 values to the frozen repository files. Then register a clearly synthetic demo authority and complete a signed `AUTHORITY_BOUND` case through semantic review and designated-consumer acknowledgement. Do not describe a synthetic fixture as a real recall or real-world authority.

The registry administrator is its deployer and a root of trust. A signer key registered for the demo proves only control of that key and its signed manifest; it does not prove real-world identity. Keep production authority signing keys offline and do not use the synthetic test key embedded in Direct Mode tests.

Release commands from the repository root (Python 3.12+, pinned requirements):

```powershell
python -m pip install -r requirements.txt
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/recallscope.py --json
genvm-lint schema contracts/recallscope.py --output artifacts/recallscope.abi.json
genvm-lint check contracts/authority_registry.py --json
genvm-lint schema contracts/authority_registry.py --output artifacts/authority_registry.abi.json
```

## Historical deployment: v0.1.0 on Studionet

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

This historical deployment does not contain the v0.2.0 authority-bound changes. Its synthetic application lifecycle is recorded below and remains valid only for that old source.

The optional label image is committed by raw-byte SHA-256 and sent through the documented `gl.nondet.exec_prompt(images=[...])` interface only after hash, size, and JPEG/PNG framing checks. Vision-provider support is an external runtime assumption and can cause a review to remain inconclusive. Escrow is intentionally excluded: a safety warning should not depend on payment, and no beneficiary is selected by the protocol.

## Live application evidence

### Synthetic demo-only case

This is a protocol demonstration using fictional artifacts, not a real recall, product, manufacturer, or safety warning. The artifacts say `DEMO ONLY` and explicitly disclaim real products.

- Case ID: `live-demo-20260927-02`
- Proposer and designated consumer: `0x2cd419603eBa593074653930Ddc4073d4FD8fc60`
- Summary: `Synthetic demo-only recall case. No real product is represented.`
- Product record: [commit-pinned raw artifact](https://raw.githubusercontent.com/Bibidee/recall-scope/93e557b6a1d922accdd9f24c35684189ded583f0/evidence/demo-product-record.txt)
- Product record raw-byte SHA-256: `0xcfdbf92bcd9dc04f19b37faa0bdf6ea2049038481086806c450be982e7e8f3bf`
- Recall notice: [commit-pinned raw artifact](https://raw.githubusercontent.com/Bibidee/recall-scope/93e557b6a1d922accdd9f24c35684189ded583f0/evidence/demo-recall-notice.txt)
- Recall notice raw-byte SHA-256: `0xea5615a7076449ea31238834ac20d00dcf1e807dad227b72ebf314e5838ffeb5`

Both URLs returned HTTP 200; fetched raw bytes matched the local files exactly before proposal.

| Step | Transaction | Final result | Verified state |
| --- | --- | --- | --- |
| Propose | [0x7596ad290f75ed3d2971f9ccb5f9d8d7f618a00c7e1fa36829c3fc1cd2f3f931](https://explorer-studio.genlayer.com/tx/0x7596ad290f75ed3d2971f9ccb5f9d8d7f618a00c7e1fa36829c3fc1cd2f3f931) | `FINALIZED`, `MAJORITY_AGREE`, leader GenVM `SUCCESS` | Canonical read `pending`; proposer, consumer, URLs, hashes, and summary matched |
| Review | [0xf79392db4e59b03ebe0f5e10a45a0b813fa0e92c06d5f71bcec27c3f1739ba40](https://explorer-studio.genlayer.com/tx/0xf79392db4e59b03ebe0f5e10a45a0b813fa0e92c06d5f71bcec27c3f1739ba40) | `FINALIZED`, `MAJORITY_AGREE`, leader GenVM `SUCCESS` | `recall_applies`; applicability `applies`; action `stop_use`; confidence `100`; rationale: “The recall notice explicitly references Northstar Demo Heater, model H-TEST-1, batch DEMO-RECALL-001, market ZZ, and instructs to stop use immediately.” |
| Designated-consumer acknowledgement | [0x03b75bfd136b0766ff212c72d695e555309142bbc029afb1f34a1909bbebebb7](https://explorer-studio.genlayer.com/tx/0x03b75bfd136b0766ff212c72d695e555309142bbc029afb1f34a1909bbebebb7) | `FINALIZED`, `MAJORITY_AGREE`, leader GenVM `SUCCESS` | Canonical read `acknowledged`; acknowledged by the designated consumer above |

Final canonical state: `acknowledged` (`submitted_at=1790544839`, `reviewed_at=1790544920`, `acknowledged_at=1790545018`). These timestamps are chain-recorded contract values; the acknowledgement is not evidence of a physical safety action.

### Preliminary failed call (not lifecycle evidence)

An earlier proposal attempt, [0x41c03ba1d4e127a80dc59317a3775b62563ae9a7ce3d0a0e03ec2ac51851e020](https://explorer-studio.genlayer.com/tx/0x41c03ba1d4e127a80dc59317a3775b62563ae9a7ce3d0a0e03ec2ac51851e020), finalized `MAJORITY_AGREE` at the transaction layer but its leader GenVM execution was `ERROR`: the SDK passed the consumer as a plain string rather than a typed GenLayer `Address`. It created no case state. The successful proposal above used `CalldataAddress`; the contract source was not changed.
