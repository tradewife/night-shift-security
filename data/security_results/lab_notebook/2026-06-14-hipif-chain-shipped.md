# Lab entry — HIPIF all-in-one night chain (SPEC v3.1.0)

## Trigger
Day Shift: implement HIPIF skill + consecutive night chain (replaces week-spread cron).

## Shipped
- `hermes/skills/hipif/SKILL.md` — 10 subgoal chain, reflection tags, RSI fold rules
- `src/night_shift_security/orchestration/hipif.py` — parse, fold, ground, repetition hooks
- `hipif` CLI: init, read, parse, ground, record, fold, next
- `hermes/scripts/nss-hipif-chain.sh` — bootstrap + folded context init
- `nss-bounty-loop-cron.sh.legacy` — emergency no-agent fallback
- Cron: `nss-hipif-chain` replaces `nss-bounty-loop`; investigate-queue + coordinator-kamino disabled

## Chain (every night)
bootstrap → scan_all → depth_wormhole → depth_kamino → hunt_rotation → rsi_fold → refine_conditional → coordinator_conditional → journal_fold → gate

## Prerequisites
- xAI OAuth: `hermes --profile night-shift model`
- RPC in `.env` for fork/validator depth

## Notes
Folded context: `data/security_results/hipif/folded_context.json`. Expected ~15–25 min full chain with RPC.