# RecallScope protocol design

## Purpose

RecallScope registers an immutable evidence pair and evaluates whether a recall notice covers a specified product name, model, batch, and market. It provides a consensus-backed, exact-scope signal for downstream systems. It does not execute or prove off-chain safety operations.

## Deterministic and nondeterministic responsibilities

Deterministic code validates IDs, field bounds, URL forms, canonical SHA-256 syntax, proposer namespaces, consumer authorization, capacity, lifecycle transitions, timestamps, output shape, confidence thresholds, and state writes.

Inside `run_nondet_unsafe`, each observer fetches the committed product record and recall notice, hashes the exact response bytes, verifies the commitments, decodes valid UTF-8, and independently classifies exact scope and required action. An optional label image is separately fetched, raw-byte hashed, size/framing checked, and sent as one `images=[bytes]` input to `exec_prompt`; text artifacts are never decoded/re-encoded before hashing. No model call occurs before all supplied integrity checks pass. Persistent values needed by the callbacks are copied to local values before nondeterministic execution.

## Decision and equivalence rule

The model output has exactly four fields: `applicability`, `required_action`, `confidence`, and `rationale`. Enum values are closed and validated; confidence is an integer 0-100 (booleans excluded); rationale is normalized and bounded. Contradictory combinations such as applies+none, not_applicable+stop_use, or unclear+repair are malformed.

The deterministic outcome is:

| Conditions | Outcome |
|---|---|
| Confidence below 75 | `inconclusive` |
| Applicability unclear | `inconclusive` |
| Confident explicit exclusion | `not_applicable` |
| Confident applicability with a concrete action | `recall_applies` |

Validators must agree on the derived outcome. For `recall_applies`, they must also agree exactly on the required action because `stop_use`, `stop_sale`, repair, inspection, support contact, and monitoring are materially different downstream consequences. For `not_applicable`, different explicit exclusion rationales are equivalent because they result in the same non-authorizing answer. For `inconclusive`, rationale and sub-threshold diagnostic variation cannot authorize action. Rationale is never compared. A disagreement between applicable/not-applicable/inconclusive, a threshold crossing, or different applicable actions fails equivalence.

The contract stores the leader's bounded diagnostic result only after the GenLayer nondeterministic boundary accepts consensus. Validators independently execute the observer, but the standard transaction receipt may expose only the leader equivalence output and validator vote/execution metadata; do not claim to recover every raw validator model response unless the platform actually exposes it.

## State transitions

```text
pending -> recall_applies -> acknowledged
pending -> not_applicable
pending -> inconclusive
pending -> cancelled
```

Only the proposer may cancel a pending case. Reviews apply only to pending cases. Only the stored consumer may acknowledge `recall_applies`; acknowledgement is one-time. No path changes a negative or inconclusive result into an action authorization. A new review requires a new case after a finalized outcome.

## External assumptions and limitations

- HTTPS hostname checks are syntactic; they do not prove DNS, redirect safety, source authority, or continuous availability.
- Hashes bind bytes, not the truth or authorship of documents.
- Optional image interpretation relies on validators' configured vision-capable models; model/provider variability can therefore lead to disagreement. Image parsing only checks size and JPEG/PNG framing, not image authenticity or OCR correctness.
- Caller-supplied product and market identifiers and consumer addresses are not verified identities.
- Semantic review can be uncertain; disagreement is expected and remains non-authorizing.
- `acknowledged` records only an on-chain consumer acknowledgement, not an off-chain recall action.
- There is no escrow. Financial custody and payout are outside this primitive.
- Escrow is intentionally omitted because safety notices must not depend on payment and there is no principled recall-verdict-based payee in this protocol.
- The toolchain pins Python packages and GenVM lint artifact; CI runs Direct Mode, lint, and ABI generation.
