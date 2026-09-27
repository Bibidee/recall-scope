# RecallScope deployment record

## Current deployment: v0.2.0 on Studionet (chain 61999)

Frozen contract-source commit: `ddb57863692f1984e3bd6ad1bb77e001d387e063`. Both sources were unchanged between this commit and deployment.

| Contract | Address | Deployment transaction | Final result | Local/deployed raw SHA-256 | Bytes |
| --- | --- | --- | --- | --- | ---: |
| RecallAuthorityRegistry | [0xFDF61b362aEd0aC9D90Aef4117f97DA087AF5187](https://explorer-studio.genlayer.com/address/0xFDF61b362aEd0aC9D90Aef4117f97DA087AF5187) | [0x8b96335b8053c6087a6ae84f7a16ab84caf4829530e5878c092221dba9534df6](https://explorer-studio.genlayer.com/tx/0x8b96335b8053c6087a6ae84f7a16ab84caf4829530e5878c092221dba9534df6) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | `02e55e0fb92d3038cb46343081efa119ef0be467f144564822d07cc648269bfe` | 6,249 |
| RecallScope | [0x23BAd5BFE52e2748c2ba1b013Ed0795D77e98572](https://explorer-studio.genlayer.com/address/0x23BAd5BFE52e2748c2ba1b013Ed0795D77e98572) | [0x0fe297236923d9054ed7d7edf50364697a4ca6b7d7a100451ab4101a1ad61346](https://explorer-studio.genlayer.com/tx/0x0fe297236923d9054ed7d7edf50364697a4ca6b7d7a100451ab4101a1ad61346) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | `8c5cd21904adad4aa0eff3ac3cd32b5dff72452ec8bdcd67d119e6603af6bc98` | 40,463 |

Parity was checked using `gen_getContractCode`: the finalized-status query form was unavailable on this Studionet gateway, so the deployment transaction was first confirmed `FINALIZED`, then the legacy bare-address code query was decoded from base64. Both deployed byte arrays matched their local source exactly, including byte length and SHA-256.

`RecallScope.get_info()` returned: `name=RecallScope`, `version=0.2.0`, `authority_registry=0xfdf61b362aed0ac9d90aef4117f97da087af5187`, evidence modes `[OPEN_EVIDENCE, AUTHORITY_BOUND]`, minimum confidence `75`, max artifact bytes `16000`, max image bytes `1000000`, and max lifetime cases per submitter `64`. `RecallAuthorityRegistry.get_info()` returned: `name=RecallAuthorityRegistry`, `version=0.2.0`, admin `0x2cd419603eba593074653930ddc4073d4fd8fc60`, maximum lifetime authorities `32`, immutable records, irreversible revocation, and `RSA-2048-PKCS1-v1_5-SHA256`.

The release gate ran locally: **75 Direct Mode tests passed**, Python compile passed, GenVM lint passed for both contracts (3 diagnostics checks each, no findings), and both ABI schemas generated. GitHub Actions run [36355446050](https://github.com/Bibidee/recall-scope/actions/runs/36355446050) for the exact frozen source commit completed successfully.

The registry administrator is its deployer and a root of trust. A signer key registered for the demo proves only control of that key and its signed manifest; it does not prove real-world identity. Production authority signing keys must be managed offline. The live demonstration key was generated only in process memory and was not persisted.

## v0.2.0 live authority-bound evidence

This is a fully synthetic protocol fixture—not a real recall, product, manufacturer, regulator, or safety warning. The immutable artifacts explicitly say “DEMO ONLY” and disclaim real products. Both exact raw bytes were fetched, UTF-8 decoded without normalization, and matched the committed SHA-256 values before use:

- Case ID: `live-authority-demo-1790549117660`
- Registry authority ID: `DEMO-AUTH-1790549071933` (synthetic; now irreversibly revoked after the demo)
- Proposer and designated consumer: `0x2cd419603eBa593074653930Ddc4073d4FD8fc60`
- Product record: [commit-pinned raw artifact](https://raw.githubusercontent.com/Bibidee/recall-scope/93e557b6a1d922accdd9f24c35684189ded583f0/evidence/demo-product-record.txt); SHA-256 `0xcfdbf92bcd9dc04f19b37faa0bdf6ea2049038481086806c450be982e7e8f3bf`
- Recall notice: [commit-pinned raw artifact](https://raw.githubusercontent.com/Bibidee/recall-scope/93e557b6a1d922accdd9f24c35684189ded583f0/evidence/demo-recall-notice.txt); SHA-256 `0xea5615a7076449ea31238834ac20d00dcf1e807dad227b72ebf314e5838ffeb5`
- Canonical signed-manifest SHA-256: `0x55dffcb7c3450342133708deb90b472904b68de1c2fd890abe37cda63a98a1f5`
- Synthetic demo signer fingerprint: `0x967aff9494d1dde318407c1750b9f74c5d3b62eb9914a839d91eb05b74bccc77`
- The manifest bound chain ID `61999`, both contract addresses, case and authority IDs, registry revision, notice hash, product/model/batch/market, issue/expiry timestamps, and reference `DEMO-RECALL-001`.

| Step | Transaction | Final result | Canonical result |
| --- | --- | --- | --- |
| Register synthetic authority | [0x12c811a28a80ef6fcf6052b9c831b81229ae2b8ee6e4edf40ad7cdcd105dfdb8](https://explorer-studio.genlayer.com/tx/0x12c811a28a80ef6fcf6052b9c831b81229ae2b8ee6e4edf40ad7cdcd105dfdb8) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | Authority active, revision 1, product `Northstar Demo Heater`, market `ZZ`, host `raw.githubusercontent.com` |
| Submit authority-bound case | [0xa6ed0d0a209cf2da6b212fb742b9f95dd70956dec2268e55fa41ce33939bd949](https://explorer-studio.genlayer.com/tx/0xa6ed0d0a209cf2da6b212fb742b9f95dd70956dec2268e55fa41ce33939bd949) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | `pending`; stored mode `AUTHORITY_BOUND`, verified proof, signer fingerprint, notice hash, scope, proposer, and consumer matched |
| Semantic review | [0xb03d3a0599c6f419d29f6ef57ec3926940953012b827ec974dcbb08b59df3a85](https://explorer-studio.genlayer.com/tx/0xb03d3a0599c6f419d29f6ef57ec3926940953012b827ec974dcbb08b59df3a85) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | `recall_applies`; action `stop_use`; confidence `100`; rationale: “The product name, model number, batch code, and market in the product record exactly match the identifiers specified in the recall notice, which explicitly commands to stop use.” The authority-aware helper returned `true` while the synthetic authority was active. |
| Designated-consumer acknowledgement | [0x43753cc23a3fd9a65fcb147c0864ff1fa57cb06201403b641a4d5616b7f9146a](https://explorer-studio.genlayer.com/tx/0x43753cc23a3fd9a65fcb147c0864ff1fa57cb06201403b641a4d5616b7f9146a) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | `acknowledged`; exact stored consumer acknowledged |
| Revoke one-time synthetic authority | [0x9279ceea4e08a393ee4f9518d37f4a7f24f5ecca6dedb9bc5ca15908d74c66f2](https://explorer-studio.genlayer.com/tx/0x9279ceea4e08a393ee4f9518d37f4a7f24f5ecca6dedb9bc5ca15908d74c66f2) | `FINALIZED`, `MAJORITY_AGREE`, GenVM `SUCCESS` | The ephemeral signer was not retained. Case remains historically `acknowledged`, authority status reads `revoked_or_changed`, and `is_authoritative_action_required_for(...)` returns `false` after revocation. |

The demonstrated state path was `pending -> recall_applies -> acknowledged`; after revoking the synthetic signing key, the acknowledgement remained recorded while the live authority-aware gate became false. This illustrates that authority revocation blocks future authorization without erasing past acknowledgements.

For transparency, two earlier synthetic authority keys were registered while debugging the SDK address encoding, then irreversibly revoked because their generated private keys were intentionally not persisted. Registration/revocation transactions: [register 1](https://explorer-studio.genlayer.com/tx/0x73c8c3b20dc0e3ecd10ea7a221bcab86dc72f09ab52116b88cdb12c5b64db89f), [revoke 1](https://explorer-studio.genlayer.com/tx/0x65dbcc30843d098885e33f3a339a9a93c71ccd6f9e241bf009a214429d9e39cf), [register 2](https://explorer-studio.genlayer.com/tx/0xd85abe09e81bad2d1e6d928e7ea507d1795aa85a882c75adc1cdb80678bf0202), [revoke 2](https://explorer-studio.genlayer.com/tx/0xb8ded08f772e77f5b749fcaf3653070cced76875a8bbb0f95d768c4eddf3dfb1). A first signed-case submission failed with a GenVM `AttributeError` because the SDK passed a plain string instead of typed `Address`; [that finalized error transaction](https://explorer-studio.genlayer.com/tx/0xe2dac24b5282ba2c9f7efedaeb4c5d4baefd761674b8771089edf5bd07f0d4d6) created no case. The live script was corrected to use GenLayer `CalldataAddress`; the corrected path above succeeded. The registry is permanent and bounded, so its three demo IDs remain as immutable records and consume 3 of 32 lifetime slots; all three have now been revoked.

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
