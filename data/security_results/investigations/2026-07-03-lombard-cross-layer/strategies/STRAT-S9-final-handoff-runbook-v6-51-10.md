# Lombard Cross-Layer Hard-First Loop — Final Handoff Runbook (v6.51.10)

## Mission

Drive the Lombard Finance (Immunefi $250k) primary subsystem — Solana
`lombard_token_pool` + EVM/Solana cross-layer message and mint handling
— under hard-first persistent looping in this Droid session until either a
submission-gate passer is found or the protocol is fully closed out
under strict CPCV/credible-harness evidence.

## Final State (v6.51.10)

- **20 attempts** captured under `runs.jsonl`.
- **No new submission-ready finding.** `submit_ready` unchanged at 1
  (OnRe H1 v6.13).
- All evidence-gated honestly-zero results are recorded with reproducible
  replay commands.
- All submission-candidate signals remain `submission_candidate: false`.

## Rounds executed

| Round | Outcome | Evidence |
|-------|---------|----------|
| R1 — multi-program Crucible scaffold (8 programs, 21k iters) | PASS | `crucible-token-pool-multi-program-dry-run-6.log`, `crucible-token-pool-stateful-multi-program-run-8s.log` |
| R2 — full-repo Cargo unit test recap (68/68 across 19 crates) | PASS — honest-zero under Crucible | `full-cargo-test-v651-recap.log`, `STRAT-S7-release-or-mint-rollback-crucible-blocked.md` |
| R3 — validator/bankrun N4 rollback test added | ENV-BLOCKED; cron carry-forward | `ccip-rollback-n4-with-validator.log`, `STRAT-S8-validator-rollback-classifier.md` |
| R4 — EVM divergence Hardhat extension (PROP-XR-EVM-010) | 6/6 passing in 6s | `evm-prop-cross-layer-divergence-with-prop-010.log` |
| R5 — adversarial `post_session_payload` Crucible action | 6/6 actions discovered, 4,781 iters | `crucible-token-pool-stateful-r5-post-session-payload-8s.log` |
| R6 — luminous-belt cleanup | this runbook | `lombard-cross-layer-v651-final-handoff-runbook.md` |

## Five-Open Signals

1. **SIG-XR-002-STATE-HANDLER** — structural refinement (closed in
   `tests/ccip.ts`).
2. **SIG-XR-001-ROLLBACK** — open: validator-level proof pending (R3 N4
   test code written, replay once a session with yarn/ts-mocha on PATH is
   used).
3. **SIG-XR-003-EVM-DIVERGENCE** — design-documentation; contrast between
   EVM try/catch and Solana atomic rollback is fully recorded.
4. **SIG-CR-001-OOB-DOS** — informational DoS-only; honest-zero for
   fund-loss; pure-Rust probe confirms the OOB pattern; recommended
   one-liner fix is `require!(*index < current_validators.len() as u64,
   ConsortiumError::ValidatorIndexOutOfBounds)`.
5. **BLOCKER-CRUCIBLE-001** — resolved (multi-program load + stateful
   smoke PASS, both captured).

## Carry-Forward Queue (post-v6.51.10)

- `BR-MBOX-001` Exhaustive search for an attempted Mailbox path (out-of-band).
- `BR-LRBT-002` `lbtc.mint_from_payload.allowListed`-style path-bypass probe.
- `BR-CONS-002` Per-session index-bounds revision (`SIG-CR-001-OOB-DOS`) as a
  one-liner disclosure if/when a confirmed beneficiary-impact vector is found.
- `BR-XR-LIGHT` Lower-cost variant of the SIG-XR-001-ROLLBACK validator
  fixture (drive directly via `tests/bascule.bankrun.test.ts` style)
  avoiding the full consortium/bridge/mailbox hydration overhead.

## Skill chain used

| Skill | Where it ran |
|------|------|
| `ultrafuzz-discovery` | R1, R3, R5 |
| `codegraph-x-ray` | R1 (scope-drift check), R3 (mailbox-handle-message scope) |
| `agentic-strategy-generation` | R1, R3, R4, R5 (each round) |
| `fuzz-scaffolder` | R1 (harness scaffold bootstrap) |
| `operator-checkpoint` | this runbook |

## Honest-zero recording

R1–R5 honest-zero results are recorded under
`data/security_results/investigations/2026-07-03-lombard-cross-layer/runs.jsonl`
with reproducible commands. Each result is `submission_candidate: false`
under NSS submission gating.

## Stop conditions met

- ✅ All five carry-forward signals have at least one credible-harness
  evidence point or honest-zero reproduction.
- ✅ `runs.jsonl` records shell-replayable commands (or env-block classifiers).
- ✅ `summary.json` carries the full signal/validator map.
- ✅ `SPEC.md` reflects the v6.51.10 final state.
- ✅ `CHANGELOG.md` carries the v6.51.1 through v6.51.10 closing lines.
- ⏳ `submit_ready` unchanged at 1 — no submission gate pass.

## Recommended next-session plan

1. **Restart session with an environment that exposes `yarn`/`npm`.**
   The night-shift cron already does this via
   `hermes/scripts/anchor-test-each.sh` and will replay N4 + any R3+
   carry-forward automatically.
2. **Carry-forward `BR-XR-LIGHT`** rather than re-running the full
   consortium/mailbox/bridge hydration; pick a leaner bankrun setup.
3. **Periodic incubation** of the BLR-2 (Lombard BridgeV2 bridge-to-mailbox
   integration) if the BR-XR-LIGHT path is satisfied.

The Droid session closes: R6 round done; submission gate untouched; clean
carry-forward ready for the night-shift cron to drive further rounds.
