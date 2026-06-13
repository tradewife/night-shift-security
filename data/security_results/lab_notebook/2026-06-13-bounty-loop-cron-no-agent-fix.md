# Lab notebook — bounty-loop cron no-agent fix

**Date:** 2026-06-13  
**Trigger:** Manual cron smoke before overnight run

## Issue

`nss-bounty-loop` agent cron failed: `xAI OAuth state is missing access_token` (Hermes LLM path).

## Fix

- Added `hermes/scripts/nss-bounty-loop-cron.sh` — no-agent: `nss-bounty-loop.sh` + auto lab notebook from `loop/state.json`
- Live job `fbe84e39c1b1` switched to `--no-agent --script nss-bounty-loop-cron.sh`
- Profile `.env` symlinked; `hooks_auto_accept: true`; gateway restarted

## Verify

- Manual script: polymarket tick, `LAB_NOTEBOOK:.../2026-06-13-bounty-loop-polymarket.md`
- Cron tick: `last_status: ok`, next run **2026-06-14 04:00 AEST**

## Note

Weekly `nss-investigate-queue` still uses agent skills — needs `hermes model` re-auth before Sun 05:00.