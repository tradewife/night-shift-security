# Session plan — next

**Status: queued**

## Objective

v6.32 closed: Silo Finance reentrancy in defaulting liquidation — 10 tests passing, mainnet fork confirmed, submission packaged. `submit_ready` unchanged (still 1, OnRe H1 v6.13). Silo finding submission-ready pending human gate.

v6.31 closed: Raydium CP-Swap + CLMM additive forensic depth (`hermes/scripts/clmm_limit_order_fuzz.py`, 100k-iteration settlement fuzz, full Token-2022 trace, cross-CPI audit, reward-precision simulation, oracle bounds). 0 anomalies.

**Next priority — from corpus gap analysis + completed template:**
1. **Drift Token-2022 spot path testing** — Deploy Drift .so to local validator, create Token-2022 mint with 5% fee, exercise deposit/withdraw/borrow paths, measure collateral_recorded vs vault_balance_delta. Highest remaining yield.
2. **Extend Lombard Crucible harness** beyond consortium to mailbox + bridge instructions (corpus shows 91 bridge patterns, strong indicator for novel finding potential).
3. **Complete Midas Stream B** — validator reproduction of `mint_request → reject_mint_request` with payment-token-side lamport measurement.

**Carry-forward from prior sessions:**
1. Resolve the OnRe human-gate decision.
2. Build a production-bootstrap PositionManager scaffold for H1-prime falsifier on 3F Grunt substrate.
3. Stateful-fuzz campaign on H4/H9/H11/H17 surface using forge-std's orchestrator on 3F Grunt.
4. Continue Midas sidecar: extend Crucible harness beyond reject handlers (Stream B).
5. Continue Lombard second-ring surfaces (mailbox + bridge).
6. Continue Origin ARM after fresh `nss_origin_jit_monitor.py` run finds non-zero signals.
7. Maintain Sidecar posture until a reproduction-tier path survives submission gates.

**Raydium carry-forward (conditionally triggered):**
- Re-run `hermes/scripts/clmm_limit_order_fuzz.py` against any future CLMM upgrade that touches `settle_filled_order`, `match_limit_order`, `get_limit_order_output/_input`, or the `-1` dust deduction in the part-filled branch.
- Monitor the `create_support_mint_associated` admin key (`GThUX1Atko4tqhN2NaiTazWSeFWMuiUvfFnyJyUghFMJ`) for any unexpected activity — if compromised, the only known path to a malicious-mint Raydium pool is open. Alert: track via AuditVault/Solodit corpus for any Raydium `InitializePool` with Token-2022 mints not in the hardcoded whitelist.

## Blocks

- [x] ~~Human-review H1 pack~~ — **DONE.** Variational: downgraded to Medium.
- [ ] Human-review OnRe NSS-ONRE-1.json.
- [ ] Human-review Origin WEB-003.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen ORIGIN-ARM-JIT-1 only if material discount release.
- [ ] Build PM scaffold for H1-prime on 3F Grunt substrate.
- [ ] Extend Lombard Crucible: mailbox + bridge actions.
- [ ] Complete Midas Stream B validator reproduction.
- [ ] **Deploy Drift .so to local validator and test Token-2022 spot paths.**
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote any candidate without human gate.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Token-2022 invariant template is now portable — reuse `crucible/src/main.rs` for any new Solana target.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`

## v6.30 key references

- `data/security_results/lab_notebook/2026-06-28/token2022-fee-invariants.md`
- `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/summary.json`
- `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/crucible/src/main.rs`
- `data/security_results/investigations/2026-06-22-v6-13-onre-deep-dive/summary.json` (OnRe H1)
- `sources/crucible/repo/` (Crucible framework)
