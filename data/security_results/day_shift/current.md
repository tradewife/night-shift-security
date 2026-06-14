# Session plan — P0 novel surface + platform ops
Status: **open** (2026-06-14)

## Objective

Close P0 gaps: KLend `live_executed` with measured delta; novel Wormhole path beyond triage surface. Keep platform intel and export gates current.

## Blocks

- [x] v3.3.0 — platform sync/diff, split export tracks, Cantina harness (reserve/coinbase/polymarket)
- [x] Hermes profile — `operator-submit` skill; HIPIF v3.3.0 bootstrap
- [x] Full bounty-depth run — 93 min, 13 folds, `submit_ready: false` (gates correct)
- [ ] P0-3 — KLend real instruction discriminators → `live_executed` + protocol/vault delta
- [ ] P0-1 — Novel Wormhole fork with economic delta (not `triage_surface_verified` only)
- [ ] Optional — Agent cron E2E with OAuth (`nss-hipif-chain` + lab notebook)

## Latest verified run (2026-06-14)

| Phase | Result |
|-------|--------|
| Scan | 29 programs, 6 `scan_grade3_plus`, 0 `submittable_candidate` |
| Wormhole | 12 trials → 69 fork repros; bridge → 60 |
| KLend live | 5 trials → 104 `solana_reproduced`, fee-only CPI |
| Cantina v3.3.0 | reserve (76 fork), coinbase (57), morpho (97), euler (96) |
| Gate | `submit_ready: false` |

Log: `data/security_results/hipif/chain_run_20260614_101352.log`  
Folded: `data/security_results/hipif/folded_context.json`

## Night Shift handoff

- **Primary cron:** `nss-hipif-chain` daily 04:00 — agent + `hipif` skill (OAuth required)
- **Deterministic:** `.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init`
- **Env:** `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0`
- **Cantina slates:** `reserve-protocol,coinbase,morpho,euler`
- **Platform intel:** `platform sync --all` weekly; `platform diff` before external submit
- **Export:** `bounty/research/` internal; `bounty/submittable/` only after `qualifies_for_submission()` + Kate gate
- **Human gate:** `submission_alert.json` schema v2 — skill `operator-submit`

## References

- `AUDIT.md` — P0–P3 gaps
- `BOUNTY_RUN.md` §12 — bounty-depth env knobs
- `SPEC.md` v3.3.0 — platform intel + export