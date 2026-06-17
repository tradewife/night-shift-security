# Session plan — P0 novel surface + platform ops
Status: **open** (2026-06-18)

## v5 pivot just landed

The 2026-06-18 directed audit (`SYSTEM_AUDIT_2026-06-18.md`) closed the v4.2 path
because eight structural defects upstream of the gates prevented novel bug
discovery. v5 pivots to a NativeHarness substrate: per-target ABI/IDL-bound
harnesses + measured-impact oracle + Foundry tests against live deployed state.

The v4.2 cron is **paused by default** (`NSS_HIPIF_PAUSE_FOR_NATIVE=1`). Resume
only after at least one target reaches `status=ready` in
`data/security_results/loop/native_harness_status.json`.

## Objective

Build the first NativeHarness — Uniswap v4 ($15.5M Cantina pot) — and prove
one real measured delta against a deployed PoolManager. Then scale the same
shape to Morpho Blue, Aave v3, Compound v3, Pendle, Euler v2 over 2–3 weeks.

## Blocks

- [x] v3.3.0 — platform sync/diff, split export tracks, Cantina harness (reserve/coinbase/polymarket)
- [x] Hermes profile — `operator-submit` skill; HIPIF v3.3.0 bootstrap
- [x] Full v4.2 bounty-depth run (2026-06-17) — 3564s, 13 folds, `submit_ready: false` (gates correct)
- [x] Audit + pivot to v5 — `SYSTEM_AUDIT_2026-06-18.md`; cron paused by default
- [x] Native module + CLI + 6 tests passing
- [ ] P0-1 Uniswap v4 NativeHarness — clone repo, ABI, deployed address, top-3 selectors, Foundry test, measured delta
- [ ] P0-2 MeasuredImpactOracle integration in `submission_gates`
- [ ] P1-1 Saturating `pick_next_target` with `concrete_candidates.jsonl` precondition
- [ ] P1-2 Splitting `fork_reproduced` aggregator into `{catalog_anchor, live_program, value_moving, novel}`

## Latest verified v4.2 run (2026-06-17, frozen)

| Phase | Result |
|-------|--------|
| Scan | 31 programs, 6 `scan_grade3_plus`, 0 `submittable_candidate` |
| Wormhole | 12 trials → 69 fork repros; bridge → 60 |
| KLend live | 5 trials → 104 `solana_reproduced`, fee-only CPI |
| Cantina v4.2 | reserve (76 fork), coinbase (57), morpho (97), euler (96) |
| Gate | `submit_ready: false` — now historically closed; pivot follows |

Log: `data/security_results/hipif/chain_run_20260617_*.log`
Folded: `data/security_results/hipif/folded_context.json`

## Night Shift handoff

- **Primary cron:** paused. `hermes/scripts/nss-hipif-chain.sh` exits 0 when `NSS_HIPIF_PAUSE_FOR_NATIVE=1` and no harness is `ready`.
- **Resume after harness ready:** the cron will run automatically once any target's `status` flips to `ready`.
- **Deterministic fallback (legacy v4.2):** `NSS_HIPIF_PAUSE_FOR_NATIVE=0 .venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init`
- **Env:** `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0`, `NSS_HIPIF_PAUSE_FOR_NATIVE=1`
- **First target:** uniswap_v4 (Cantina $15.5M) — mapped, ABI/IDL/source pending
- **Platform intel:** unchanged; `platform sync --all` weekly, `platform diff` before external submit
- **Export:** `bounty/research/` internal; `bounty/submittable/` only after `qualifies_for_submission()` + Kate gate
- **Human gate:** `submission_alert.json` schema v2 — skill `operator-submit`

## References

- `SYSTEM_AUDIT_2026-06-18.md` — eight structural defects + the pivot
- `AUDIT.md` — v4.2 closure + v5 Pivot section
- `SPEC.md` v5.0.0-draft
- `tests/test_native_harness.py` — 6 tests
- `data/security_results/lab_notebook/2026-06-18-v5-pivot-acceptance.md`