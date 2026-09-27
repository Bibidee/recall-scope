# RecallScope

RecallScope is a standalone GenLayer recall-scope primitive. It binds product records and recall notices to exact SHA-256 digests, then asks independent validators to decide whether a notice applies to a particular product, model, batch, and market. Optional product-label images are supported and hash-checked before visual interpretation.

This v0.2.0 release candidate adds an optional authority-provenance layer without removing the existing open-evidence flow:

- `OPEN_EVIDENCE` preserves the prior behavior: consensus over the exact submitted artifacts, without cryptographic proof of who issued the notice.
- `AUTHORITY_BOUND` additionally requires a registry record, a valid RSA-2048 PKCS#1 v1.5/SHA-256 signature over a canonical scope manifest, an exact notice hash match, an allowed notice hostname, and an active non-revoked registry entry before semantic review can occur.

The trust chain is explicit: the registry identifies a recognized signing key; deterministic code verifies the signature and its scope; SHA-256 binds the notice bytes; GenLayer validators independently fetch and interpret the exact artifacts; deterministic logic derives the outcome. The registry administrator is a root of trust: registration does not prove that a key belongs to a real-world regulator or manufacturer.

## Why GenLayer?

Hashing establishes artifact identity, not whether a recall covers a particular model, batch, and market. A single centralized verifier could selectively interpret the evidence. RecallScope instead runs independent artifact fetch and semantic review through GenLayer consensus. Validators must agree on the exact required action for an applicable result; disagreement, malformed output, low confidence, artifact-integrity failure, or unavailable evidence cannot authorize an action.

The new authority layer does not ask the model to decide whether a signer is registered or whether a signature is valid. Those checks are deterministic. The model only evaluates whether the verified product evidence and hash-bound notice apply to the exact product scope. GenLayer documents synchronous view calls between Intelligent Contracts; RecallScope uses that mechanism to read the separate bounded registry. [GenLayer IC interaction documentation](https://docs.genlayer.com/developers/intelligent-contracts/features/interacting-with-intelligent-contracts).

## Lifecycle and downstream use

```text
OPEN_EVIDENCE:   submit_case -> pending -> recall_applies -> acknowledged
                                      -> not_applicable / inconclusive / cancelled

AUTHORITY_BOUND: submit_authority_bound_case
                 -> deterministic registry/scope/signature checks
                 -> pending -> recall_applies -> acknowledged
                            -> not_applicable / inconclusive / authority_revoked / authority_expired
```

Both modes preserve exact raw-byte SHA-256 verification for product text, notice text, and optional PNG/JPEG label images. All input bounds, output schema checks, confidence threshold (75), validator equivalence rules, proposer cancellation rules, and designated-consumer acknowledgement rules remain in force.

Downstream contracts that only need a semantic recall signal may use `is_action_required_for(...)`. That helper does not assert publisher authority. A downstream contract requiring signed provenance must use `is_authoritative_action_required_for(...)`; it returns true only for a live `AUTHORITY_BOUND` case with a verified signature, unrevoked matching registry snapshot, exact scope match, `recall_applies`, confidence at least 75, and a concrete action.

```python
if not recallscope.is_authoritative_action_required_for(
    case_id, proposer, product_name, model, batch, market
):
    raise gl.vm.UserError("No active authority-bound recall signal for this exact scope")

# The consumer acknowledgment is a separate one-time authorization check.
recallscope.acknowledge_action(case_id, proposer)
```

Acknowledgement records an on-chain action by the designated consumer; it does not prove physical notification, repair, refund, or product removal.

## Authority registry and manifest

`RecallAuthorityRegistry` is a second, independent Intelligent Contract. Its deployer is its permanent administrator. The administrator can register at most 32 authorities and irreversibly revoke records; entries cannot be edited, reactivated, or deleted. Key/scope changes require a new authority ID. Each record is bounded to eight exact hostnames, markets, and product names. Case proposers cannot register or alter authorities.

An authority-bound manifest signs 15 fixed-order UTF-8 fields using unambiguous decimal-byte-length prefixes (`length:` immediately followed by field bytes, concatenated with no extra delimiter): protocol label `RECALLSCOPE_AUTHORITY_MANIFEST_V1`, chain ID, RecallScope address, registry address, case ID, authority ID, authority revision, notice SHA-256, product name, model, batch, market, issued-at, expiry (zero means no expiry), and recall reference. Text values are the contract's whitespace-normalized values. The signature is a 256-byte RSA-2048 signature over those canonical bytes using PKCS#1 v1.5 with SHA-256; the public exponent is fixed at 65537. The resulting manifest commitment is SHA-256 of the canonical bytes.

The signature binds the chain, both contract addresses, case namespace, authority record revision, exact notice digest, product/model/batch/market scope, and time fields. Replays across cases, chains, contracts, registries, or altered scope therefore fail. Authority records are immutable except for irreversible revocation. Revocation prevents new cases, makes pending cases terminal `authority_revoked`, disables both action helpers for reviewed authority-bound cases, and blocks an unrecorded consumer acknowledgment. It does not erase a previously recorded acknowledgment or reverse an already completed physical action.

## Security boundary and limitations

- The registry administrator is the root of trust. On-chain registration proves that a manifest was signed by the key the administrator registered—not that the key belongs to a real-world authority. Secure administrator and signer-key custody remain external responsibilities.
- RSA signatures are checked deterministically by the contract. The model never judges signer identity or signature validity.
- A domain allowlist is defense in depth, not proof of publisher authority. HTTPS hostname parsing cannot prove DNS resolution, prevent DNS rebinding, or guarantee redirect behavior in GenVM. Authority-bound mode also requires the cryptographic signature and exact notice hash.
- SHA-256 binds the exact fetched bytes, not the truth of the content. All evidence and summaries remain untrusted input; prompt-injection handling is defensive, not absolute.
- Evidence availability, validator/provider behavior, and visual interpretation are external dependencies. Network failures and disagreement remain retryable/inconclusive; RecallScope does not promise to eliminate `UNDETERMINED` results.
- Caller-supplied product labels, markets, and consumer addresses are protocol identifiers, not real-world identity proofs. This is not legal, medical, manufacturer, or regulator advice.
- Cases remain stored; each proposer has a 64-case lifetime limit. The authority registry has a 32-record lifetime limit.
- No escrow is included. Safety action should not be conditioned on payment, and the protocol has no principled recall-verdict payee.

## Deployment status

The current v0.2.0 deployment is on GenLayer Studionet (chain 61999): [RecallScope](https://explorer-studio.genlayer.com/address/0x23BAd5BFE52e2748c2ba1b013Ed0795D77e98572), deployed by [transaction](https://explorer-studio.genlayer.com/tx/0x0fe297236923d9054ed7d7edf50364697a4ca6b7d7a100451ab4101a1ad61346); and its [RecallAuthorityRegistry](https://explorer-studio.genlayer.com/address/0xFDF61b362aEd0aC9D90Aef4117f97DA087AF5187), deployed by [transaction](https://explorer-studio.genlayer.com/tx/0x8b96335b8053c6087a6ae84f7a16ab84caf4829530e5878c092221dba9534df6). Both deployments finalized with `MAJORITY_AGREE` and GenVM `SUCCESS`. The frozen source commit is `ddb57863692f1984e3bd6ad1bb77e001d387e063`; deployed source was retrieved through `gen_getContractCode` after finalized-status confirmation and compared byte-for-byte. SHA-256 values: RecallScope `8c5cd21904adad4aa0eff3ac3cd32b5dff72452ec8bdcd67d119e6603af6bc98` (40,463 bytes); registry `02e55e0fb92d3038cb46343081efa119ef0be467f144564822d07cc648269bfe` (6,249 bytes). Exact `get_info()`, parity, live authority-bound flow, and release evidence are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

The v0.1.0 deployment is historical and does not contain the authority-bound changes: [historical contract](https://explorer-studio.genlayer.com/address/0x58117a2D5a6332dDe2e303a5128D939c54270664), [deployment transaction](https://explorer-studio.genlayer.com/tx/0x2db9b6d748c185bd7767ffaeade07235d114de86ec4745228b445a822100e32e). Its separate synthetic open-evidence lifecycle remains preserved in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Build and test

Requires Python 3.12+. Install the pinned tools and run:

```powershell
python -m pip install -r requirements.txt
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/recallscope.py --json
genvm-lint schema contracts/recallscope.py --output artifacts/recallscope.abi.json
genvm-lint check contracts/authority_registry.py --json
genvm-lint schema contracts/authority_registry.py --output artifacts/authority_registry.abi.json
```

Preflight requires exactly two deployable sources, syntax validity, all Direct Mode tests, GenVM lint, and ABI/schema generation for both contracts. Test-only signing keys are synthetic and must never be used as real authority keys.
