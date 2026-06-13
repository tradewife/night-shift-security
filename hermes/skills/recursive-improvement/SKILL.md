---
name: recursive-improvement
description: Deterministic RSI pass — findings store signals → loop state mutations, refinement hints, improvement ledger.
---

# Recursive Self-Improvement (deterministic)

No LLM in this layer. Reads findings store + loop outcomes; writes bounded state updates and `improvement_ledger.jsonl`.

Runs automatically at end of each `bounty loop` tick. Use this skill for standalone analysis or post-cron triage.

## Patterns (all deterministic)

| Action | Trigger | Effect |
|--------|---------|--------|
| `repeat_fingerprint` | Same top-findings hash as prior run on slug | Log + extend cooldown |
| `extend_cooldown` | Repeat fingerprint | +12h per repeat (max 72h) |
| `queue_refinement` | Grade 1–2 survivors, survival ≥ 0.4 | `refinement_queue` + `refinement_hints.json` |
| `plateau_template` | Catalogue analogue grade ≥ 4 | `template_plateaus[slug]` |
| `boost_scan_priority` | Refinement candidates in store | `scan_boost_slugs` |
| `config_fallback` | Fork catalogue-only | `config_hints[slug]` → novel/shoestring |

## Step 1 — Analyze (no pipeline)

```bash
.venv/bin/python -m night_shift_security.cli.main improve
```

## Step 2 — Inspect outputs

```bash
cat data/security_results/loop/refinement_hints.json
tail -5 data/security_results/knowledge/improvement_ledger.jsonl
jq '.refinement_queue, .cooldown_overrides' data/security_results/loop/state.json
```

## Step 3 — Act on refinement hints

If `refinement_hints.json` has a top entry:

```bash
# Kamino campaign path (coordinator state):
.venv/bin/python hermes/scripts/nss-write-proposals.py

# Or scoped cross-target:
.venv/bin/python hermes/scripts/nss-write-scan-proposals.py --slug <slug>
```

Then re-run bounty loop with `--proposals data/security_results/hermes_proposals/latest.json`.

## Step 4 — Lab notebook

Log: which RSI actions fired, cooldown deltas, refinement queue changes. **Same vs different** vs prior tick.

## Gotchas

- RSI never bypasses `validate_hypothesis()` or evidence grading.
- `config_hints` are advisory — Day Shift or next loop tick decides config swap.
- Coordinator and bounty loop share `refinement_seeds_from_store()` — same grade 1–2 band.