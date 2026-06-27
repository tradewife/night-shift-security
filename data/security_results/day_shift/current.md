# Session plan — v6.30 Token-2022 fee invariant campaign

**Status: closed** (2026-06-28) — v6.30/session-34 Token-2022 transfer fee invariants.
**Verdict:** **1 confirmed (OnRe H1, submit_ready), 1 honest zero (Marginfi), 1 pending (Drift).**

## Summary

Built portable Token-2022 transfer fee Crucible invariant template (P-TF-001..007) and applied across OnRe, Marginfi, and Drift.

### Key findings

1. **OnRe H1 — CONFIRMED (submit_ready).** `create_redemption_request` records gross amount (100M) but vault receives net (95M after 5% Token-2022 transfer fee). Cancel/fulfill revert; boss top-up + cancel returns only 95M to user (second fee charge), creating 5M protocol treasury hole. PoC validated on mainnet binary dump (SHA256 `abcea77d935ca5eb...`). Already submit_ready from v6.13 investigation.

2. **Marginfi — HONEST ZERO.** Deep code review of `deposit.rs`, `withdraw.rs`, `repay.rs`, `liquidate.rs`. Marginfi correctly handles Token-2022 fees via `calculate_pre_fee_spl_deposit_amount` — pre-compensates for fee before SPL transfer. Vault receives exactly gross amount after fee. No bug in deposit/withdraw path.

3. **Drift — PENDING.** Token-2022 spot deposit/withdraw/borrow paths untested. Highest remaining yield target.

### Deliverables

- Portable Crucible harness template: `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/crucible/src/main.rs`
- Strategy files: `tf_deposit_fee_mismatch`, `tf_liquidation_fee_impact`, `tf_fee_on_fee_lending`
- Property fan-in: P-TF-001 through P-TF-007
- `summary.json` with 1 confirmed + 1 honest zero + 1 pending
- `concrete_candidates.jsonl` updated

### Test results

**51 passed**, 1 skipped (Marginfi 26 + OnRe 11 + Drift 14).

## Submission gate status

| Gate | Status |
|---|---|
| OnRe H1 | **submit_ready=1** (from v6.13) |
| Marginfi | **honest_zero** |
| Drift | **pending** |

## References

- `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/`
- `data/security_results/lab_notebook/2026-06-28/token2022-fee-invariants.md`
- `data/security_results/investigations/2026-06-22-v6-13-onre-deep-dive/summary.json` (OnRe H1)
