# Session plan — P0 novel surface + platform ops + v6.8 engine expansion

Status: **open** (2026-06-21) — v6.7 closed; v6.8+ queue re-opened

## v6.7 close context

v6.7.0-proposal-session11 (2026-06-21) closed the engine-vs-wrapper gap that
sessions 5–10 carried silently. Re-reading `https://blog.monad.xyz/blog/ultrafuzz`
named the gap: sessions 5–10 ran the multi-attempt wrapper without the
executable fuzz engine. v6.7 wired the engine on Marginfi v2 (the most-tested
substrate), produced 846,081,229 cumulative libfuzzer iterations in 90s+90s
instrumented-release mode, surfaces 0 panics and 0 crashes. Engine-level
honest-zero recorded.

Audit-saturation framing is now bounded at TWO layers:

| Level | N | Outcome |
|-------|---|---------|
| Substrate-level (source review, sessions 5-10) | 5 | All honest-zero |
| **Engine-level (executable fuzz, v6.7 this session)** | **1** | **Honest-zero** |

`submit_ready` remains 0. Gates intact. `native_harness_status.json` unchanged.
No fixture-only claim. No auto-submit. The 846M-iteration result is a
crash-freeness signal, not a submission.

## Blocks (carryover + v6.8+ queue)

- [x] v3.3.0 — platform sync/diff, split export tracks, Cantina harness (reserve/coinbase/polymarket)
- [x] Hermes profile — `operator-submit` skill; HIPIF v3.3.0 bootstrap
- [x] Full v4.2 bounty-depth run (2026-06-17) — 3564s, 13 folds, `submit_ready: false`
- [x] Audit + pivot to v5 — retired; folded into SPEC.md §3 + §14
- [x] Native module + CLI + 6 tests passing
- [x] v6.x substrate sweep — Ethena V1 / Marginfi v2 / Kamino / Drift / Meteora DLMM all source-review honest-zero
- [x] **v6.7 engine operationalization** — Marginfi v2 fuzz crate + 7 pass@k attempts + ~846M cumulative iterations; engine-level honest-zero
- [ ] Path B — Plumb `ixs_sysvar` into `MarginfiFuzzContext::setup` so flash-loan composition engine can exercise `validate_ixes_exclusive`
- [ ] Engine calculus on a second substrate (build a Marginfi-shaped fuzz crate for Kamino OR Drift)
- [ ] Executable `socialize_loss` property test (currently source-review falsification only)
- [ ] First-measured-delta actionable finding (gate the next candidate through `qualifies_for_submission()`)

## Latest verified v6.7 run (2026-06-21, closed)

| Phase | Result |
|-------|--------|
| Engine orchestrator | 7 pass@k attempts × 20 corpus seeds = 140 inputs replayed; all exit_code=0 |
| Long fuzz `lend` (90s, instrumented-release) | 423,658,407 iterations, exit_code=0 |
| Long fuzz `lend_extended` (90s, instrumented-release) | 422,422,822 iterations, exit_code=0 |
| Cumulative engine load | **846,081,229 iterations / 182 seconds wall** |
| Gate | `submit_ready: 0` — engine-level honest-zero, gates correct |

Log: `data/security_results/investigations/2026-06-21-v6-7-engine/`
Folded: `data/security_results/investigations/2026-06-21-v6-7-engine/{runs.jsonl, summary.json, fuzz_long_run.json}`

## Night Shift handoff

- **Primary cron:** paused. `NSS_HIPIF_PAUSE_FOR_NATIVE=1` retained (no schema change).
- **v6.8+ target:** Path B (flash-loan engine on Marginfi v2). Plumb `ixs_sysvar` into `MarginfiFuzzContext::setup`; extend `lend_extended.rs` `Action` enum with `StartFlashloan{idx, end_idx}` + `EndFlashloan{idx}` variants; cross-check `validate_ixes_exclusive` behavior under random action timing; re-run long fuzz.
- **Env:** `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0`, `NSS_HIPIF_PAUSE_FOR_NATIVE=1` (retained)
- **Platform intel:** unchanged; `platform sync --all` weekly, `platform diff` before external submit
- **Export:** `bounty/research/` internal; `bounty/submittable/` only after `qualifies_for_submission()` + Kate gate
- **Human gate:** `submission_alert.json` schema v2 — skill `operator-submit`

## References

- `SPEC.md` v6.7.0-proposal-session11 (§0.1 v6.7 this session; §0.2-§0.8 preserved)
- `CHANGELOG.md` — v6.7.0-proposal-session11 entry
- `data/security_results/lab_notebook/2026-06-21-session-11-ultrafuzz-engine-on-marginfi.md`
- `https://blog.monad.xyz/blog/ultrafuzz` — re-derived engine-vs-wrapper separation
- `data/security_results/reflection/2026-06-20-orchestrator-handoff-reflection.md` — substrate-level audit-saturation reasoning (carryover)
