# Lab entry — 2026-06-11

## Trigger
Day Shift: bounty scoring layer + Cantina screen (SPEC v2.0.7)

## Shipped
- `bounty/scoring.py` — `compute_bounty_score`, grade-3 gate, reproduction tier multipliers
- `bounty/candidates.py` — `bounty_candidates.jsonl` + yield_signals
- `bounty/discovery_scan.py` — unified Immunefi + Cantina zero-RPC scan
- `data/cantina_registry.py` — 7 curated live bounties (Euler $7.5M, Uniswap $15.5M, …)
- CLI: `bounty score`, `bounty export`, `scan --platform all`, `knowledge --bounty-ready`
- Immunefi packs: `bounty/immunefi/<exploit-id>/` (no overwrite)
- `SUSTAINABILITY.md` — allocation TBD after first payout

## Demo (grant_demo validator anchors)
Run `bounty score --append` on mango/solend/cashio — ranked ledger at `bounty/bounty_candidates.jsonl`.

## Same vs different
**Different:** first economic ROI layer on top of evidence grades; Cantina extends screen beyond Immunefi-only.

## Night Shift handoff
- Cron OK: `scan --platform all` weekly; investigate top unified rank
- Use `knowledge --bounty-ready` before external submit decision
- Human gate: no autonomous platform submission

## Gotchas
- `bounty export` replaces old `bounty --input` CLI (subcommand required)
- Cantina `deposit_required` bounties penalized in readiness score
- Catalogue analogue penalty — validator replay still ranks high but `submit_now` needs grade 4 + validator tier