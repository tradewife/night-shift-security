# Session plan — next

**Status: queued**

## Objective

v6.43 closed: Superform v2 Cantina bounty deep-dive produced a Critical self-deposit via Merkle-valid hook execution finding. Upstream-integrated PoC passes against real `SuperVault` / `SuperVaultStrategy` / `SuperVaultAggregator` / Merkle / redeem path. **Submitted to Cantina on 2026-07-01**; now awaiting triage. `submit_ready` queue returned to 1 (OnRe H1 v6.13 remains outstanding).

v6.38 closed: Sablier Cantina Bounty corpus-exhaustive — AuditVault #42010 overflow adjudicated not exploitable (empirical H-017 proof). 33/33 Flow tests pass. Lockup/Airdrops CEI verified. No submission-ready finding. `submit_ready` unchanged (still 1, OnRe H1 v6.13).

v6.37 closed: Sablier Cantina Bounty deep-dive — 29/29 tests, core Flow math provably sound, protocol fee precision documented.

v6.36 closed: Pendle Finance corpus x-ray — callback + router angles honest-zero pending residual-balance materiality.

v6.35 closed: Monad UI Bounty — 16 findings, 0 submission-ready. Surface exhausted.

v6.34 closed: Coinbase Onchain Bug Bounty (Cantina $5M Tier 0) sidecar — 4 carry-forward hypotheses adjudicated honest-zero.

v6.33 closed: Veda boring-vault deep-dive STRAT-01 Token-2022 deposit fee bug class confirmed executable; production blast currently zero.

v6.32 closed: Silo Finance reentrancy in defaulting liquidation — 10 tests passing, mainnet fork confirmed, submission packaged. `submit_ready` unchanged (still 1, OnRe H1 v6.13).

**Next priority — from corpus gap analysis + completed templates:**
1. **Drift Token-2022 spot path testing** — Deploy Drift .so to local validator, create Token-2022 mint with 5% fee, exercise deposit/withdraw/borrow paths, measure collateral_recorded vs vault_balance_delta. **Highest remaining yield.**
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

## Blocks

- [ ] Human-review OnRe NSS-ONRE-1.json.
- [ ] Human-review Origin WEB-003.
- [ ] Human-review Silo Reentrancy v6.32 submission.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen ORIGIN-ARM-JIT-1 only if material discount release.
- [ ] Build PM scaffold for H1-prime on 3F Grunt substrate.
- [ ] Extend Lombard Crucible: mailbox + bridge actions.
- [ ] Complete Midas Stream B validator reproduction.
- [ ] **Deploy Drift .so to local validator and test Token-2022 spot paths.**
- [ ] Keep `submit_ready=1` unchanged unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote any candidate without human gate.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`

## v6.38 key references

- `data/security_results/investigations/2026-06-29-v6-37-sablier-deep-dive/{setup.md,property_fanin.md,strategies/STRAT-002-flow-core-validated.md}`
- `sources/sablier/flow/repo/tests/v6-37-SablierFlowDeathProbe.t.sol`
- `data/security_results/lab_notebook/2026-06-30-v6-37-sablier-cantina-deep-dive.md`

