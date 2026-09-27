# RecallScope protocol design

## Purpose and compatibility

RecallScope produces an exact-scope, consensus-backed record of whether a committed recall notice applies to one product, model, batch, and market. It preserves the v0.1 open-evidence workflow and adds an opt-in signed-authority workflow. Both remain fail-closed and both use the same semantic review and consumer acknowledgement state machine.

### Evidence modes

| Mode | Publisher-authority guarantee | Submission entry point |
| --- | --- | --- |
| `OPEN_EVIDENCE` | None. The notice and product record are exact-byte committed and reviewed, but their publisher is not cryptographically authenticated. | `submit_case(...)` |
| `AUTHORITY_BOUND` | A bounded on-chain registry key signed the canonical case-scoped manifest; its exact notice hash, scope, and URL hostname passed deterministic checks. | `submit_authority_bound_case(...)` |

Mode is stored once on submission and cannot be changed. An open-evidence result never satisfies `is_authoritative_action_required_for`.

## Trust chain

```text
registry administrator (root of trust)
          │ registers signer public key + exact domains/products/markets
          ▼
RecallAuthorityRegistry ── synchronous read-only IC view ──► RecallScope
          │                                                  │
          │ RSA-2048 public key                              │ deterministic scope/key/signature/time check
          │                                                  ▼
          └──── signer signs canonical manifest ◄──── proposer submits signed recall scope
                                                             │
                                    validators independently fetch/hash product + notice (+ image)
                                                             │
                                                             ▼
                                       semantic scope and action consensus
                                                             │
                                                             ▼
                                deterministic result + mode-aware downstream helper
```

GenLayer documents synchronous `view()` calls between Intelligent Contracts; the authority registry is read before entering the nondeterministic callback. Registry access is deterministic and never performed from inside `run_nondet_unsafe`. See [GenLayer's IC interaction reference](https://docs.genlayer.com/developers/intelligent-contracts/features/interacting-with-intelligent-contracts).

## Registry model

`RecallAuthorityRegistry` captures its deployer as a permanent administrator. At most 32 distinct authority IDs may ever be added. Registration is admin-only and each authority is immutable after creation except for one irreversible transition from active to revoked. To rotate a key or alter scope, register a new ID; no update, reactivation, or deletion path exists. Each record has one 2048-bit RSA modulus, an exact list of up to eight lowercase notice hostnames, up to eight exact markets, and up to eight exact product names. There are no wildcards.

The registry is a trust root, not a proof of real-world identity. It asserts that its administrator recognizes a particular key and scope. Reviewers and downstream applications must independently decide whether the registry administrator is an appropriate root of trust. The signer key is a cryptographic public key, not an asserted EOA address.

## Canonical signed manifest

Authority-bound submissions include `authority_id`, a recall reference, issue and optional expiry timestamps, and a signature. The contract reads the authority record and builds the following fixed-order fields:

1. `RECALLSCOPE_AUTHORITY_MANIFEST_V1`
2. GenLayer chain ID in canonical decimal
3. RecallScope contract address as lowercase `0x` + 40 hex digits
4. Authority-registry address in the same form
5. case ID
6. authority ID
7. registry record revision in canonical decimal
8. lowercase `0x`-prefixed notice SHA-256
9. normalized product name
10. normalized model
11. normalized batch
12. normalized market
13. issue time in canonical decimal
14. expiry time in canonical decimal (`0` means no expiry)
15. recall reference

For each value, UTF-8 encode it, append its UTF-8 byte length as ASCII decimal followed by `:`, then append the bytes. Concatenate the 15 length-prefixed fields without extra separators. SHA-256 of this byte sequence is the manifest commitment. The signer produces a standard RSA-2048 PKCS#1 v1.5 SHA-256 signature over those canonical bytes; verification uses the registered modulus and fixed exponent 65537 with exact EMSA-PKCS1-v1_5 padding validation. Signature and modulus encodings are exactly 256 bytes. No model or web observation participates in signature verification.

Issue time may not be in the future or older than one year at submission. Nonzero expiry must be after issue and current time and no more than one year after issue. A case reviewed after its expiry becomes terminal `authority_expired`. Domain allowlisting is exact hostname equality against the signed authority scope; it does not assert that a hostname is controlled by the signer.

The manifest binds chain, both contract addresses, case namespace, authority ID/revision, exact notice hash, product/model/batch/market, and timing. Changing any field invalidates the signature and prevents replay across a second case, chain, contract, or registry. Exact URLs are not signed; instead, the notice digest is signed and the submitted hostname must be in the frozen authority allowlist.

## Deterministic and nondeterministic responsibilities

Deterministic logic validates case IDs, bounded fields, URL syntax, SHA-256 syntax, consumer and proposer identities, capacities, lifecycle state, registry state, exact authority scopes, issue/expiry times, canonical manifest, RSA signature, confidence threshold, output shape, and state writes.

Inside `run_nondet_unsafe`, each observer re-fetches the committed product record and recall notice, hashes exact raw bytes, verifies each SHA-256, validates UTF-8, then semantically assesses the exact product/model/batch/market and operative action. Optional label images are independently fetched, raw-byte hashed, size/framing checked, then passed to the configured vision model. Storage fields used in callbacks are copied to local values before entering the nondeterministic boundary. Any artifact failure prevents model interpretation.

For `AUTHORITY_BOUND`, deterministic signature and registry checks finish before the semantic review is invoked. The LLM is not asked whether the key is trusted, the signature is valid, or the notice is authoritative; it only assesses semantic applicability to the exact committed product scope.

## Decision and equivalence

Model output contains exactly `applicability`, `required_action`, `confidence`, and `rationale`. Enums are closed, confidence is a non-boolean integer from 0 to 100, and rationale is normalized and bounded. A confident applicable result requires a concrete action. Validators must agree on the derived outcome, and for `recall_applies` on the exact required action. For safe non-authorizing `not_applicable` or `inconclusive` results, rationale and diagnostic variation are not compared. Malformed output or disagreement cannot authorize.

| Condition | Stored result |
| --- | --- |
| Confidence below 75 or applicability unclear | `inconclusive` |
| Confident explicit exclusion | `not_applicable` |
| Confident exact applicability and concrete agreed action | `recall_applies` |
| Registry revoked/changed before review | `authority_revoked` |
| Signed manifest expires before review | `authority_expired` |
| Transient HTTP/network/model failure | Retryable transaction failure; existing state remains unchanged |
| Integrity failure or malformed result | No authorization; committed state remains unchanged |

## Revocation and case snapshots

Authority-bound cases snapshot the authority ID, display name, signer modulus fingerprint, full registered modulus, exact domains, markets, products, registry revision, notice hash, manifest commitment/signature, scope fields, reference, and time bounds. Registry updates are not permitted. A record can only be irreversibly revoked. Revocation before semantic review makes a pending case terminal `authority_revoked`; expiry before review makes it terminal `authority_expired`. If revoked after a positive review, the stored semantic result remains auditable, but both action helpers return false and a not-yet-recorded consumer acknowledgement is rejected. A previously recorded acknowledgement remains historical state and cannot be erased by registry revocation.

## State transitions

```text
OPEN_EVIDENCE:
pending -> recall_applies -> acknowledged
pending -> not_applicable | inconclusive | cancelled

AUTHORITY_BOUND:
pending -> recall_applies -> acknowledged
pending -> not_applicable | inconclusive | cancelled
pending -> authority_revoked | authority_expired
```

Only the proposer may cancel while pending; reviews only operate on pending cases; only the stored consumer can acknowledge an applicable result, once. An authority-bound review requires active matching registry state at review time. Acknowledgment repeats that active-state check. Each proposer has a 64-case lifetime capacity; the registry has a 32-record lifetime capacity.

## Downstream helpers

- `is_action_required_for(...)` is the compatibility helper for a consensus-backed exact-scope semantic result. For open evidence it makes no authority claim. For authority-bound cases it also returns false after registry revocation or snapshot mismatch.
- `is_authoritative_action_required_for(...)` is the stronger gate. It returns true only for an active, matching, non-revoked authority snapshot with verified manifest/signature, matching notice hash and exact product/model/batch/market, positive semantic result, confidence >=75, and a concrete action.

Integrators requiring source authority must call the second helper and separately enforce any application-level identity, authorization, and physical-action policy.

## Limitations

- The administrator can register a false authority or key; on-chain registration cannot prove real-world authority identity.
- DNS resolution, DNS rebinding, network redirects, and continued artifact availability cannot be proven by syntactic HTTPS/domain admission.
- A valid signature proves key possession for canonical bytes, not the truth or legality of the notice.
- Semantic models and vision providers can disagree or be unavailable. Honest protocol behavior may remain inconclusive; no zero-`UNDETERMINED` guarantee is made.
- Caller-supplied product/batch/market identifiers are not external identity proofs. A consumer acknowledgement is not a physical recall-action receipt.
- No funds, escrow, or automated recall execution exist in RecallScope.
