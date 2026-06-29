# Session plan — next

**Status: queued**

## Objective

v6.34 closed: Coinbase Onchain Bug Bounty (Cantina $5M Tier 0) sidecar — 4
carry-forward hypotheses adjudicated honest-zero; cross-chain replay
primitive captured as documented intent. `submit_ready` unchanged
(still 1, OnRe H1 v6.13).

v6.33 closed: Veda boring-vault deep-dive STRAT-01 Token-2022 deposit
fee bug class confirmed executable; production blast currently zero
(session-38).

v6.32 closed: Silo Finance reentrancy in defaulting liquidation —
10 tests passing, mainnet fork confirmed, submission packaged.
`submit_ready` unchanged (still 1, OnRe H1 v6.13). Silo finding
submission-ready pending human gate.

v6.31 closed: Raydium CP-Swap + CLMM additive forensic depth
(`hermes/scripts/clmm_limit_order_fuzz.py`, 100k-iteration settlement
fuzz, full Token-2022 trace, cross-CPI audit, reward-precision
simulation, oracle bounds). 0 anomalies.

**Next priority — from corpus gap analysis + completed templates:**
1. **Drift Token-2022 spot path testing** — Deploy Drift .so to local validator, create Token-2022 mint with 5% fee, exercise deposit/withdraw/borrow paths, measure collateral_recorded vs vault_balance_delta. **Highest remaining yield.**
2. **Extend Lombard Crucible harness** beyond consortium to mailbox + bridge instructions (corpus shows 91 bridge patterns, strong indicator for novel finding potential).
3. **Complete Midas Stream B** — validator reproduction of `mint_request → reject_mint_request` with payment-token-side lamport measurement.

**Completed (v6.35):**
- Monad UI Bounty (Cantina) deep-dive: 3 loops, 16 findings, 0 submission-ready. Privy reflective CORS (F-011, High) documented. Surface exhausted without authenticated access. Investigation closed.

**Monad carry-forward (potential re-open):**
- If claim.monad.xyz reopens for a future airdrop/distribution, re-test with authenticated session.
- If telegram.molandak.org becomes accessible (Vercel auth lifted), analyze Telegram auth flow.
- Privy reflective CORS (F-011) would be elevated to submission-ready if combined with an XSS vector on claim.monad.xyz.

**Carry-forward from prior sessions:**
1. Resolve the OnRe human-gate decision.
2. Build a production-bootstrap PositionManager scaffold for H1-prime falsifier on 3F Grunt substrate.
3. Stateful-fuzz campaign on H4/H9/H11/H17 surface using forge-std's orchestrator on 3F Grunt.
4. Continue Midas sidecar: extend Crucible harness beyond reject handlers (Stream B).
5. Continue Lombard second-ring surfaces (mailbox + bridge).
6. Continue Origin ARM after fresh `nss_origin_jit_monitor.py` run finds non-zero signals.
7. Maintain Sidecar posture until a reproduction-tier path survives submission gates.
8. **Phase-4 Coinbase carry-forward (optional)**: PROP-SPM-013 full reentrancy fixture if Drift/Lombard/Midas yield empty.

**Raydium carry-forward (conditionally triggered):**
- Re-run `hermes/scripts/clmm_limit_order_fuzz.py` against any future CLMM upgrade that touches `settle_filled_order`, `match_limit_order`, `get_limit_order_output/_input`, or the `-1` dust deduction in the part-filled branch.
- Monitor the `create_support_mint_associated` admin key (`GThUX1Atko4tqhN2NaiTazWSeFWMuiUvfFnyJyUghFMJ`) for any unexpected activity — if compromised, the only known path to a malicious-mint Raydium pool is open. Alert: track via AuditVault/Solodit corpus for any Raydium `InitializePool` with Token-2022 mints not in the hardcoded whitelist.

**Coinbase carry-forward (optional):**
- PROP-SPM-013: build a controlled-reentrancy MockCoinbaseSmartWallet that re-fires `receive()` during the first `spendWithWithdraw`.
- PROP-RT-007: audit-equivalent patch review of SpendRouter.constructor EIP-7702 indicator check.
- PROP-CCH-006: multi-chain fork exercise if RPC becomes available.
- All 4 carry-forward hypotheses can be picked back up in a future session if (a) Coinbase issues new relevant code, or (b) the chain-id-stripping behavior changes in a Coinbase deployment / deprecation announcement.

## Blocks

- [x] ~~Human-review H1 pack~~ — **DONE.** Variational: downgraded to Medium.
- [x] ~~v6.34 Coinbase deep-dive cycles 1–3~~ — **DONE.** 40/40 harness tests, 4 hypotheses adjudicated honest-zero.
- [ ] Human-review OnRe NSS-ONRE-1.json.
- [ ] Human-review Origin WEB-003.
- [ ] Human-review Silo Reentrancy v6.32 submission.
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

## v6.34 key references

- `data/security_results/lab_notebook/2026-06-29-v6-34-coinbase-cantina.md`
- `data/security_results/lab_notebook/2026-06-29-v6-34-coinbase-cantina-phase3.md`
- `data/security_results/investigations/2026-06-29-v6-34-coinbase-cantina/{setup.md,property_fanin.md,strategies/,adjudication/,summary.json}`
- `sources/spend-permissions/repo/test/coinbase_propfuzz/*` (8 suites, 40 tests)
- `src/night_shift_security/native/coinbase_smart_wallet.py` + `tests/test_native_coinbase_smart_wallet.py`

## v6.30 key references

- `data/security_results/lab_notebook/2026-06-28/token2022-fee-invariants.md`
- `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/summary.json`
- `data/security_results/investigations/2026-06-28-v6-29-token2022-fee-invariants/crucible/src/main.rs`
- `data/security_results/investigations/2026-06-22-v6-13-onre-deep-dive/summary.json` (OnRe H1)
- `sources/crucible/repo/` (Crucible framework)

