# Lab notebook — RSI + cron strategy
**Date:** 2026-06-13  
**Trigger:** Day Shift — implement deterministic recursive self-improvement + cron tuning

## Recommendation implemented

**Primary:** `nss-bounty-loop` daily 04:00 — cross-platform Immunefi + Cantina + inline RSI.

**Demoted:** `nss-investigate-queue` from every 2d → **weekly Sun 05:00**, Kamino coordinator depth only. Avoids duplicate scan/investigate vs bounty loop.

**Kept:** `nss-coordinator-kamino` Wed 03:00 for campaign-scoped refinement.

## RSI patterns shipped (v2.0.10)

| Action | Deterministic trigger |
|--------|----------------------|
| `repeat_fingerprint` | Same top-findings hash on slug |
| `extend_cooldown` | +12h per repeat (max 72h) |
| `queue_refinement` | Grade 1–2, survival ≥ 0.4, lineage cap < 3 |
| `plateau_template` | Catalogue analogue grade ≥ 4 |
| `boost_scan_priority` | Refinement candidates in store |
| `config_fallback` | Fork catalogue-only → hint novel/shoestring |

Shared `refinement_seeds_from_store()` with Coordinator.

## Live cron (aligned 2026-06-13)

| Job | ID | Schedule |
|-----|-----|----------|
| nss-bounty-loop | fbe84e39c1b1 | daily 04:00 (+ recursive-improvement skill) |
| nss-investigate-queue | d5f0875fe76c | Sun 05:00 weekly (Kamino coordinator + RSI) |

## Next action

First bounty-loop + RSI cron run 2026-06-14 04:00 — check `improvement_ledger.jsonl` and `refinement_hints.json`.