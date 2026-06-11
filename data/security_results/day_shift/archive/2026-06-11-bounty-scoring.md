# Session plan — 2026-06-11-bounty-scoring
Status: done

## Objective

Ship bounty scoring layer + Cantina unified screen for self-sustaining bounty prioritization.

## Blocks

- [x] scoring-module — `bounty/scoring.py`
- [x] candidates-ledger — `bounty_candidates.jsonl`
- [x] cantina-registry — `scan --platform all`
- [x] wire-export-cli — `bounty score`, `knowledge --bounty-ready`
- [x] fix-pack-overwrite — per-exploit Immunefi dirs
- [x] tests — 213 passed
- [x] docs — SUSTAINABILITY.md, SPEC v2.0.7, BOUNTY_RUN §8b

## Night Shift handoff

- Cron OK: `scan --platform all` weekly; `knowledge --bounty-ready` before submit
- Open for Kate: pick external anchor from ranked `bounty_candidates.jsonl`

## Audit

Audit: pass