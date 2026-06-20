# 2026-06-20 — False positive measurement fix: slot_delta no longer counts as "measured impact"

**Author:** Orchestrator (self-evolving audit loop)
**Session:** Second orchestrator session (continuation from duplicate-key-bug fix)
**Finding:** NSS-0013 (Kamino, grade 4, qualifies=true) was a FALSE POSITIVE
**Severity:** GATE BUG — weak measurement criterion allowed slot-only delta to pass submission gates
**Status:** FIXED + tests passing (791 passed, 11 skipped, 0 failed)

---

## What happened

The submission gate in `_v4_candidate_submission_ok()` accepted
`reserve_last_update_slot_delta > 0` as evidence of "measured impact".
This criterion is too weak: advancing the reserve's `last_update_slot`
is routine behavior on every `refresh_reserve` call and produces NO
balance changes, NO token deltas, and NO value extraction.

The `kamino_measured_delta.json` for NSS-0013 showed:
- `supply_vault_amount_delta: 0` -- no tokens moved
- `borrowed_amount_sf_delta: 0` -- no borrow changes
- `lamport_delta: 56` -- only rent-exempt lamports (slot advancement)
- `measured_impact: true` because `reserve_last_update_slot_advanced`

The `solana_measured_oracle.delta()` function also had the same weak
criterion: it set `measured=True` whenever `post_slot > pre_slot`,
regardless of whether any actual state change occurred.

## Root cause

Both the submission gate and the measured oracle treated slot advancement
as a meaningful signal. In reality, slot advancement is an artifact of
any on-chain interaction (even a no-op CPI) and does not indicate value
extraction or invariant violation.

## Fix applied

### 1. submission_gates.py
Removed `reserve_last_update_slot_delta` as a measured-impact trigger.
Added a comment explaining why: slot-only deltas are routine behavior
that do not constitute exploit impact.

### 2. solana_measured_oracle.py (delta function)
Changed the classification logic:
- SPL delta above threshold -> measured (unchanged)
- Borrowed amount changed -> measured (unchanged)
- Cumulative borrow rate changed AND slot advanced -> measured (new: more conservative)
- Slot advanced without state change -> NOT measured (was: measured)

Added descriptive reason `"slot_advanced_without_state_change"` for the
now-non-measured case.

### 3. Test updates
- `test_delta_slot_advance_measured` -> renamed to
  `test_delta_slot_advance_without_state_change_not_measured` and now
  asserts `measured_impact is False`
- `test_build_evidence_envelope_shape` -> uses pre/post with no state
  change; asserts `measured_impact is False`
- `test_capture_cross_slot_mocked` -> uses pre/post with borrow delta
  so measured_impact remains True
- `test_delta_cumulative_rate_change` -> split into two tests:
  - With slot advance: measured=True
  - Without slot advance: measured=False

### 4. state.json
Cleared NSS-0013 from `submission_queue` and set `human_gate_pending=false`.

## Verification
- `python3 -m pytest tests/ -q` — **791 passed, 11 skipped, 0 failed**
- NSS-0013 no longer qualifies for submission

## Impact on pipeline
- This fix prevents any future slot-only-delta findings from passing the
  submission gate, forcing the pipeline to require actual balance/token
  deltas for measured impact
- The `invariant_detection.py` code already requires `impact_usd > 0` for
  the `oracle_deviation_bound` invariant when using slot_delta, so that
  path was already partially protected

## Files modified

| File | Change |
|------|--------|
| `src/night_shift_security/validation/submission_gates.py` | Removed slot_delta as sole measured trigger |
| `src/night_shift_security/impact/solana_measured_oracle.py` | delta() requires actual state changes, not just slot advancement |
| `tests/test_solana_measured_oracle.py` | Updated 4 tests for new classification logic |
| `data/security_results/loop/state.json` | Cleared NSS-0013 from submission_queue |
| `data/security_results/lab_notebook/2026-06-20-false-positive-measurement-fix.md` | This file |
