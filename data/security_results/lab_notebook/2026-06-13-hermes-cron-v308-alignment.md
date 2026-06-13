# Lab notebook — Hermes cron aligned to SPEC v3.0.8

**Date:** 2026-06-13  
**SPEC:** v3.0.8  
**Trigger:** Day Shift — bounty-loop skill + live cron prompt stale vs pipeline

## Changes

- `./hermes/install-profile.sh` — symlinks restored for `bounty-loop`, `coordinator-cycle`, `recursive-improvement`, operator skills
- `hermes/skills/bounty-loop/SKILL.md` — v3.0.8 gates: KLend `CLONED_DATA_ACCOUNTS`, Wormhole governance + pauser-auth forks
- `nss-bounty-loop.sh` — `git pull --ff-only` before loop tick
- Live cron `fbe84e39c1b1` prompt updated via `hermes cron edit`

## Gates (unchanged)

- Still **0 submit_ready** — cron now documents that fee-only KLend CPI and pause-auth smoke are not submittable

## Next

- First v3.0.8 cron tick: 2026-06-14 04:00 — verify lab notebook + `loop/state.json` after run