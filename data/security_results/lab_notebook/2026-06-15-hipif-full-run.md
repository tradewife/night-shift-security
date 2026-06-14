# Lab entry — 2026-06-15 full HIPIF run (agent + deterministic)

## Trigger
manual — `cron tick` after OAuth re-auth; agent stopped early; deterministic chain for full data

## Agent cron (fbe84e39c1b1)
- Session: `cron_fbe84e39c1b1_20260615_062356`
- Wall time: ~64s (11 API calls)
- Outcome: **bootstrap only** — folded scan_all never started pipeline
- Output: `~/.hermes/profiles/night-shift/cron/output/fbe84e39c1b1/2026-06-15_06-25-00.md`
- Root cause: agent emitted short text stop (`response_len=8`); Hermes marked job ok

## Deterministic bounty-depth chain
- Log: `data/security_results/hipif/chain_run_20260614_202533.log`
- Wall time: **5158s (~86 min)**
- Folds: 13/13 complete
- submit_ready: **false** (gates correct)

| Phase | Result |
|-------|--------|
| Scan | 29 programs, 6 scan_grade3_plus, 0 submittable_candidate |
| Wormhole | 12 trials → 69 fork repros |
| Bridge | 4 trials → 60 fork repros |
| KLend live | 5 trials → 108 solana_reproduced, 33 findings (fee-only CPI) |
| Cantina | reserve 75 fork, coinbase 57, morpho 97, euler 100 |
| Hunt | wormhole/morpho/euler/ethena × 3 trials |
| RSI | refinement_queue=11 |
| Refine | 3 passes |
| Coordinator | 2 cycles |

Folded: `data/security_results/hipif/folded_context.json`

## Same vs different
vs 2026-06-14 run (~93 min): KLend solana_reproduced 104→108; euler cantina fork 96→100; hunt morpho fork 99→100. No submit_ready delta. Agent path still untested for refine/delegate.

## Next action
Fix agent early-stop (cron must not mark ok until gate subgoal); hybrid: deterministic depth + agent refine/coordinator only.