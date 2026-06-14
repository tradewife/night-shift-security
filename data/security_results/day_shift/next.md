# Session plan — next
Status: queued

## Objective

Close P1 gaps from `AUDIT.md`: hunt saturation fix, HIPIF fold alignment, KLend/Wormhole novel grade 3+.

## Blocks

- [x] P1-2 — Fork-ready hunt bypasses `saturated_slugs` (`ignore_saturation=True`, v3.2.0)
- [x] P1-1 — `CHAIN_SUBGOALS` extended; `hipif fold --subgoal` (v3.2.0)
- [ ] P0-3 — KLend probe beyond fee-only CPI (`live_executed` + measured delta)
- [ ] P2-1 — Wormhole triage-scoped CPCV on grade-1 fork survivors
- [ ] Optional — Agent cron E2E with OAuth (`nss-hipif-chain` + lab notebook)

## Night Shift handoff

- Primary: `nss-hipif-chain` 04:00 (agent) or `nss-hipif-chain-run.py --init` (deterministic)
- Env: `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0`
- Do not re-run completed bounty-depth assays unless hypothesis/refinement queue changes
- Intel: `data/security_results/intel/latest.md`
- Audit: `AUDIT.md`