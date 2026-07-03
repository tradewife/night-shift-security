# Strategy S3 — Consortium Quorum Cross-Layer

**Targets:** PROP-CR-006 (valset update ordering), PROP-CR-007 (mid-session rotation replay), PROP-CONS-002 (quorum weight), PROP-CONS-007 (session payload isolation), PROP-SD-001 (storage layout desync).

## Soft trust boundary

- `consortium.Config.current_validators/[VECTOR]`, `current_weights/[VECTOR]`, `current_weight_threshold`, `current_height`, `current_epoch`.
- `consortium.Session.signed/[VECTOR]`, `weight` per `(epoch, payer, payload_hash)` PDA.
- `consortium.SessionPayload.payload/[VECTOR]` per `(payer, payload_hash)`.
- `consortium.ValidatedPayload.latest_epoch` per `(payload_hash)`.
- `consortium.utils.check_signature`: secp256k1_recover tryRecover (v=27, v=28).

## Attack-shape candidates

1. **Vec index out-of-bounds (DoS).** `post_session_signatures` indexes `current_validators[*index]` without bounds check. A `payer` with bad indices produces a panic. Sampled threat: bounded DoS — only DoS, no fund-loss. Adversarial input index=10, validators_len=3. **Actual code review proof:** `programs/consortium/src/instructions/post_session_signatures.rs:34`. Rust returns an IndexOutOfBounds panic, which Anchor surfaces as 1xxx-class error. DoS-only.
2. **Sesame weight underflow.** `session.weight += current_weights[*index]` is `u64`; if `*index` is 32 (post-rotation index, or wrong-sized), and `current_validators.len() == 32`, weight += weights[31]. Probe at `u64::MAX - small_weight` boundary.
3. **Cross-rotation signed[i] sticky flag.** `signed[i]` is a `Vec<bool>` allocated with size `current_validators.len()` at session creation. After `update_valset` to a *strictly-larger* validator set, an existing session PDA cannot have its `signed` vector re-allocated (Anchor Account). New validators appended at indexes >= OLD_size: signature posts contribute weight only at the *new* index — but if the rotation reorders validators, signed[i] could remain true for validator[i]_OLD that no longer is validator[i]_NEW — weight remains counted toward OLD validator's correctness.
4. **Sticky LegislativeReorder.** Same flag in **another validator at a non-equal index** doesn't apply because `post_session_signatures` fails on `signed[i] == true`. **Replay attack**: if a validator moved to a *new* index i+1, the *new* index can be addressed by a previously-counted signature's pubkey — but pubkey differs. Replay requires the same old pubkey being published at new index — not under attacker control.
5. **Epoch-bound `validated_payload`.** `validated_payload.latest_epoch = config.current_epoch` at finalize time. If finalize happens at epoch N, a rotation locks `validated_payload.epoch == N` but `config.current_epoch == N+1` after `update_valset` — `set_initial_valset_from_session` checks `validated_payload.latest_epoch == config.current_epoch`, so a finalize-session in OLD epoch N cannot be re-applied at NEW epoch N+1. **Cross-rotation finalize-attempt: revert.**
6. **`update_valset` nonces.** `update_valset_payload.epoch == config.current_epoch + 1` and `height > current_height`. Must be consecutive. Skip-epoch or roll-back rotators: revert. Probe.
7. **`set_initial_valset`** (no payload) — admin-only path with no quorum constraint. Probe admin-only behavior; ensure not bypassed.
8. **`consortium.Session.signed[i]` race.** Multiple sigs posting concurrently: Anchor accounts enforce sequence, but a sub-quorum payload could still come through multiple sigs at different *sessions*. Forced-stateful probe.
9. **`handle_message` ↔ consortium epoch alignment.** Mailbox.deliver_message requires `consortium_validated_payload[VALIDATED_PAYLOAD_SEED, payload_hash]` PDA to exist (Anchor `init_if_needed`-like check via `owner = config.consortium, seeds = …`). If a session is built and finalized but rotation happens before deliver_message, the validator set's signatures were already attached + signed with OLD weights. Finalize_session records `latest_epoch` against CURRENT epoch → at rotation moment, Config.current_epoch rolls forward, ValidatedPayload's old epoch doesn't match NEW epoch → could a stale session still be cited as a notarized payload? Probe.
10. **SessionPayerMismatch.** `delete_session_payload.close = payer` closes only the caller's session payload. Cross-payer is impossible due to PDA seeds.

## Tests / fuzzers

1. **Crucible for consortium**: stateful sequences:
  - `set_initial_valset` (admin-only path) — pre-rotation
  - `create_session`
  - `post_session_payload` (multiple chunks)
  - `post_session_signatures` (multiple signatures + indices)
  - `finalize_session`
  - `update_valset`
  - `delete_session_payload`
  - `close_session_for_epoch`
  - `accept_ownership`
  - `transfer_ownership`
  - `initialize`
  - `advance_slots`
2. **Python harness** — `tests/test_native_lombard.py` extension:
  - Vector-index bounds test: post 5 indices but validator set is 3 — asserts revert.
  - Quorum weight arithmetic test: post 8-of-9 sigs and finalize — confirms weight tracking.
  - Mid-session rotation: simulate `current_height += 1` — confirm session closes.
  - Mid-session epoch: confirm `validated_payload.latest_epoch` rejected after rotation.

## Pass@k acceptance criteria

- Vector-index DoS: pass if program panics on invalid index.
- Quorum: pass if sub-quorum finalize reverts.
- Rotation: pass if new-epoch finalize requires fresh `validated_payload`.

## v6.51 round-3 update: index-bounds DoS confirmed (DoS-only, not fund-loss)

Direct source review of `programs/consortium/src/instructions/post_session_signatures.rs:34`
("`if !ctx.accounts.session.signed[*index as usize]` and downstream `[validator]/[weight]` accesses) and a pure-Rust probe
(`programs/consortium/src/utils/post_session_signatures_probe.rs`) confirmed that:

1. Indexing `current_validators[index as usize]` and `current_weights[index as usize]`
   without bounds-check is a real source pattern.
2. With MAX_VALIDATOR_SET_SIZE = 102 as the constant, attacker-supplied `index >= 102`
   (or any value above `current_validators.len()` even if smaller than 102) panics
   in pure Rust; on Solana, the equivalent operation surfaces as a runtime panic and
   an unrecoverable transaction failure.
3. The reachable impact is **session DoS**: the bad-index caller's `Session` PDA is the
   only state mutated by the tx (the panic aborts before any state mutation that would
   have passed init). Any future signature submission for the same `(epoch, payer, payload_hash)`
   triple is still possible because the `Session` Account is provided through a PDA
   derived from those inputs — *but* the call must reach the same memory access, so the
   same panic happens again unless the operator pre-runs bounds-check.
4. No fund-loss path verified: the panic occurs *before* any CPI to `bridge.gmp_receive`
   / `mailbox.handle_message` / `bascule_gmp.validate_mint`, so any authorised validator
   adversary could grind such calls but never drain tokens.

The pure-Rust probe `tests/post_session_signatures_probe::*` was added and run via
`cargo test --no-default-features --features localnet -p consortium post_session_signatures_probe`:

```
running 3 tests
test utils::post_session_signatures_probe::post_session_signatures_oob_probe::probe_index_in_range_is_accessible ... ok
test utils::post_session_signatures_probe::post_session_signatures_oob_probe::probe_index_above_max_panics_without_guard ... ok
test utils::post_session_signatures_probe::post_session_signatures_oob_probe::probe_index_above_max_validator_set_constant ... ok
test result: ok. 3 passed; 0 failed; 0 ignored
```

**Adjudication:** honest-zero for fund-loss; informational DoS-only signal. Carry-forward
recommendation: add `require!(*index < current_validators.len() as u64, ConsortiumError::ValidatorIndexOutOfBounds)`
or equivalent at the top of `post_session_signatures`. The fix is one-liner; not submission-ready
on its own.

## Expected false positives

- Vec-index DoS: not a fund-loss issue. Track only as informational finding.
- Rotation: by design, sessions bound to era.
