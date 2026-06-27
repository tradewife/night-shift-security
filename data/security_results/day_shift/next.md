# Session plan — next
Status: queued

## Objective

v6.27 (KAST sidecar) completed honest-zero across the full m_ext + ext_swap instruction surface including cross-instance swap. H5 retracted as false positive. v6.26 Lombard Phase 4-5 corridor endgame — all 5 crucible harnesses honest-zero. 

**Recommend pivot to a fresh target with less audit saturation.** Carry-forward from all sessions:

1. Resolve the OnRe human-gate decision first (unchanged from previous handoff).
2. Build a production-bootstrap PositionManager scaffold (multi-position seeded state) for an H1-prime falsifier on the 3F Grunt substrate; record results as v6.20+ evidence.
3. Stateful-fuzz campaign on the H4/H9/H11/H17 surface using forge-std's orchestrator on 3F Grunt.
4. Continue Midas sidecar from v6.25 (engine_partial_directional_H2, need deeper instruction coverage via Crucible pre-written-state PDAs).
5. Continue Lombard second-ring surfaces: lombard_token_pool as NativeHarness target, RatioOracle consortium-rotation sequences, corpus refinement for corridor + lbtc.
6. Only continue Origin ARM after a fresh `nss_origin_jit_monitor.py` run finds non-zero `pendingRedeemAssets` AND material cross-discount release.

## Blocks

- [ ] Human-review `data/security_results/bounty/submittable/onre/NSS-ONRE-1.json` and decide whether to submit externally, including the configuration-dependent exposure caveat.
- [ ] Human-review WEB-003 (`findings/WEB-003-blind-trust-external-aggregator-tx.md`) once Origin reviewers are available.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen `ORIGIN-ARM-JIT-1` only if Ethena ARM is unpaused with non-zero `pendingRedeemAssets` and material discount release.
- [ ] Build a production-bootstrap PM scaffold for H1-prime on the 3F Grunt substrate, capture static + dynamic evidence into investigation folder.
- [ ] Stateful-fuzz campaign on the H4/H9/H11/H17 surface using forge-std's orchestrator on 3F Grunt.
- [ ] Non-role liquidator nested-callback harness for H8-prime (3F Grunt).
- [ ] Midas sidecar deep instruction coverage: extend Crucible harness beyond reject_mint_request/reject_redeem_request.
- [ ] Lombard Token Pool as NativeHarness target — Python/NativeHarness approach for CCIP-based pool. Promote `lombard_token_pool.py` from `tests/test_native_lombard.py`.
- [ ] RatioOracle consortium-rotation sequences: dedicated test for stale-ratio rejection after consortium upgrade.
- [ ] Corpus refinement for corridor + lbtc: merge corpus from standalone consortium/mailbox/bridge runs into 9-program corridor.
- [ ] `secp256k1_recover` syscall in litesvm — blocks BasculeGMP CPI. Until resolved, `bascule_gmp=None` on AssetRouter remains required in harness.
- [ ] Re-run `hermes/scripts/v6_16_grunt_static_probe.py` after every in-scope source change and diff against the baseline envelope.
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## H13 quantitative datum (carries forward)

- `testFinding_externalRepay_constantOracle_perfFeeAccruesOnDonation` in
  `sources/3f-grunt/repo/test/manager/GruntH13ExternalDebtFeeInflation.t.sol`
- documents donation 500e18 → feeRecipient shares ~92.59e18 with
  management=0.
- Cantina 3.3.21 records this dynamic at ME-info / acknowledged level.
- Does not escape the gate; reusable as a measurement baseline if a stronger
  finding emerges.

## Night Shift handoff

- Do **not** promote `ORIGIN-ARM-JIT-1` from research on local PoC alone; live materiality is currently zero.
- Do **not** autonomously submit OnRe `NSS-ONRE-1` or Origin `WEB-003`; both are still human-gated.
- Do **not** promote a 3F Grunt candidate solely on the v6.19 H13-H19 falsifier green: that is a falsifier-pass datum, not an absence-of-bug proof.
- Do **not** count fixed-input replay, dry-run, or replay-only runs as fuzzing.
- Use `ultrafuzz-discovery` before any engine-level honest-zero or candidate claim.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Do **not** run the full bounty-depth chain unless engine substrate counts/iterations change materially.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`

## KAST v6.27 key references (carry-forward for audit context)

- `data/security_results/lab_notebook/2026-06-27-v6-27-kast-sidecar.md`
- `sources/crucible/fuzz/kast/src/main.rs` — 23-action harness, cross-instance swap, value conservation invariant
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/property_fanin.md` — H5 retraction with full proof, 23-action execution status
- `src/night_shift_security/native/kast_state_model.py` — Python state machine model
- Program sustained 4 audit firms: Asymmetric Research, Adevar Labs, OtterSec, Halborn. Crucible coverage is exhaustive.

## Lombard v6.26 key references (carry-forward)

- `data/security_results/lab_notebook/2026-06-27-v6-26-lombard-corridor-endgame.md`
- `sources/crucible/fuzz/lbtc/src/main.rs` — secp256k1-signed mint lifecycle harness
- `sources/crucible/corridor/src/main.rs` — 9-program cross-program orchestrator
- `src/night_shift_security/native/lombard.py` — Lombard Token Pool NativeHarness target
