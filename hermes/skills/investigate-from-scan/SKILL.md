---
name: investigate-from-scan
description: Use after Immunefi scan to deep-dive top-ranked programs. Reads latest.json and runs full NSS pipeline per target.
---

# Investigate From Scan

Closes the loop: **scan ranks all curated programs → top N get full investigation** (not Kamino-only).

## Step 1 — Scan (if stale)

```bash
.venv/bin/python -m night_shift_security.cli.main scan --ecosystem solana --min-bounty 250000
```

Output: `data/security_results/immunefi_scan/latest.json`

## Step 2 — Preview queue

```bash
.venv/bin/python -m night_shift_security.cli.main investigate --dry-run --top 3 --ecosystem solana
```

Selects by: `submission_ready` → `best_evidence_grade` → `solana_reproduced` → `max_bounty_usd`.

## Step 3 — Delegate expansion for top target(s)

For each selected slug, run `hypothesis-expansion` skill with that program's templates and catalogue analogue (from scan row). Write proposals JSON per slug or one merged file with `seed_id` bindings.

## Step 4 — Deep investigation

```bash
.venv/bin/python -m night_shift_security.cli.main investigate \
  --top 2 \
  --ecosystem solana \
  --proposals data/security_results/hermes_proposals/latest.json
```

Runs full pipeline per program (dynamic config from `kamino_shoestring.json` base). Kamino only runs if scan ranks it in top N.

## Step 5 — Triage + export

Per run output under `data/security_results/`: triage grade ≥3, export shoestring pack for grade ≥4.

## Step 6 — Lab notebook

**Required.** Follow `lab-notebook` skill — MEMORY.md + `data/security_results/lab_notebook/YYYY-MM-DD-<slug>.md`.

## Gotchas

- Scan is lightweight (4 samples/template); investigate is full pipeline (darwinian, CPCV, etc.) — don't `--top` more than 2-3 per cron tick.
- Programs without `targets/<slug>.json` use catalogue analogue states only — Kamino has richer recon in `sources/kamino/recon.json`.
- EVM programs need `--ecosystem evm` or `all`; Solana cron should keep `ecosystem solana`.