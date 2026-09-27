# RecallScope

RecallScope is a standalone GenLayer Intelligent Contract primitive for assessing whether a committed product-safety recall notice applies to one exact product, model, batch, and market. It independently verifies the raw bytes of both the product record and recall notice, then uses validator consensus for the semantic scope judgment.

RecallScope is contract-only: no frontend, token, escrow, or off-chain decision service. v0.1.0 is deployed on Studionet at [0x58117a2D5a6332dDe2e303a5128D939c54270664](https://explorer-studio.genlayer.com/address/0x58117a2D5a6332dDe2e303a5128D939c54270664). The deployment transaction is [0x2db9b6d748c185bd7767ffaeade07235d114de86ec4745228b445a822100e32e](https://explorer-studio.genlayer.com/tx/0x2db9b6d748c185bd7767ffaeade07235d114de86ec4745228b445a822100e32e). Deployed source was retrieved with `genlayer-js` `getContractCode` and matched byte-for-byte to the repository contract (SHA-256 `b0bf0ed02d5e13aec238af3e88cfd5cc5e464ff7c4358d7d1c34e6a402465d31`). This is deployment evidence only: no live case submission, semantic review, or consumer acknowledgement is claimed yet.

## Why GenLayer?

SHA-256 can prove which bytes were reviewed, but it cannot determine whether a recall applies to a particular model, batch, and region. A single operator-controlled API or model could selectively answer that question. In RecallScope, validators independently fetch the same hash-committed documents and independently classify applicability and required action. The contract accepts only valid bounded output and a matching consensus outcome; unclear scope, low confidence, malformed output, or disagreement cannot create an actionable recall result.

This reduces reliance on one decision service, but it does not authenticate the document publisher, prove the recall is legally authoritative, or guarantee that every validator is correct.

## Lifecycle

```text
submit_case -> pending -> recall_applies -> acknowledged
                     -> not_applicable
                     -> inconclusive
                     -> cancelled (proposer only, while pending)
```

The submitter binds exact UTF-8 product-record and recall-notice bytes with SHA-256 hashes, plus exact product/model/batch/market identifiers and a designated consumer address. An optional JPEG/PNG label image may also be supplied by HTTPS URL and raw-byte SHA-256; when present, it is independently fetched and verified before being passed as image bytes to the vision-capable semantic review. Anyone may trigger review. Each validator checks all supplied artifact digests before semantic interpretation.

Decision behavior:

- `recall_applies` requires confidence >= 75, clear applicability, a concrete action, and validator agreement on the exact required action.
- `not_applicable` requires a confident explicit exclusion. Validators may differ on which exclusion supports the same non-applicable conclusion; the result never authorizes a recall action.
- `inconclusive` is non-authorizing and includes unclear or low-confidence analysis.
- Transient fetch/provider failures are retryable and leave state pending; malformed or integrity-failing inputs cannot approve.
- Only the designated consumer can acknowledge an applicable case, once.

The acknowledgment is an on-chain record, not proof that a physical recall, customer notification, refund, repair, or inventory action occurred. Downstream contracts must still apply their own authorization and operational controls.

## Data and security boundary

- SHA-256 is calculated on exact raw response bytes before UTF-8 decoding.
- Optional product-label images are hash-checked as raw bytes before being passed to GenLayer vision, are limited to one image and 1 MB, and must have PNG/JPEG framing. Unsupported, unavailable, or mismatched images fail closed.
- Both artifacts are bounded, non-empty UTF-8 text and are pinned to the proposal hashes.
- HTTPS URL admission rejects obvious local/internal host forms, IP literals, userinfo, ports, fragments, and malformed authorities. The contract cannot reliably prove DNS resolution, block DNS rebinding, or guarantee redirect behavior in GenVM.
- Artifact text and summaries are untrusted data; embedded instructions are not followed. Prompt-injection resistance is not absolute.
- Submitter, consumer, market, and product identifiers are caller-supplied protocol labels, not real-world identity proofs.
- The contract is an evidence-scoped signal, not medical, legal, regulatory, or manufacturer advice. For actual safety issues, follow competent authority/manufacturer guidance directly.
- Storage retains final and cancelled records. Each proposer has a 64-case lifetime limit; multiple addresses can create separate namespaces.
- Validator/provider disagreement and network outages can produce inconclusive/retryable outcomes. No honest design can guarantee zero `UNDETERMINED` results; safety comes from never treating uncertainty as authorization.
- Escrow is intentionally excluded. Recall warnings should not be delayed or conditioned on a deposit, and this primitive has no natural party entitled to receive funds. A downstream commercial workflow can implement its own independently audited payment contract if needed.

## Example downstream gate

```python
if not recallscope.is_action_required_for(
    case_id, submitter, product_name, model, batch, market
):
    raise gl.vm.UserError("No consensus-backed recall action exists for this exact scope")

# Apply the downstream system's own action and access controls here.
```

The named consumer can record acknowledgment:

```python
recallscope.acknowledge_action(case_id, submitter)
```

## Build and test

Requires Python 3.12+. Install pinned tools and run:

```powershell
python -m pip install -r requirements.txt
python scripts/preflight.py
python -m pytest tests/direct -q
genvm-lint check contracts/recallscope.py --json
genvm-lint schema contracts/recallscope.py --output artifacts/recallscope.abi.json
```

Tests are outside `contracts/`; `contracts/` must contain exactly one deployable source. A failed gate means do not freeze or deploy.

## Release status

**Studionet lifecycle demonstrated.** A synthetic, explicitly fictional demo case completed `pending -> recall_applies -> acknowledged`; this demonstrates contract flow only and is not a real recall or product-safety warning. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for finalized transaction receipts and artifact hashes.
