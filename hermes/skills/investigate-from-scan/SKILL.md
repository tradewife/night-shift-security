---
name: investigate-from-scan
description: Use after Immunefi scan to deep-dive top-ranked programs. Reads latest.json and runs full NSS pipeline per target.
---

# Investigate From Scan

Manual/ad-hoc path: **scan ranks programs → top N get full investigation** via Immunefi-only `investigate` CLI. Autonomous cross-platform hunt: use `bounty-loop` skill instead.

## Step 1 — Scan (if stale)

```bash
.venv/bin/python -m night_shift_security.cli.main scan --platform all --min-bounty 250000
```

Output: `data/security_results/bounty_scan/latest.json` (preferred) or legacy `immunefi_scan/latest.json`

## Step 2 — Preview queue

```bash
.venv/bin/python -m night_shift_security.cli.main investigate \
  --scan data/security_results/bounty_scan/latest.json \
  --dry-run --top 3 --ecosystem all

# Cross-target (skip Kamino if already deep-dived):
.venv/bin/python -m night_shift_security.cli.main investigate --dry-run --top 2 --exclude kamino --ecosystem solana
```

Selects by: `scan_grade3_plus` (legacy: `submission_ready`) → `best_evidence_grade` → `solana_reproduced` → `max_bounty_usd`.

## Step 3 — Delegate expansion for top target(s)

For each selected slug, run `hypothesis-expansion` skill OR parametric cross-target writer:

```bash
.venv/bin/python hermes/scripts/nss-write-scan-proposals.py --slug raydium
```

## Step 4 — Deep investigation

```bash
# --proposals is a GLOBAL flag (before the subcommand)
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  investigate --scan data/security_results/bounty_scan/latest.json \
  --top 2 --exclude kamino --ecosystem all
```

Runs full pipeline per program (dynamic config from `kamino_shoestring.json` base). Use `--exclude kamino` after Kamino coordinator campaign. Kamino only runs if scan ranks it in top N and not excluded.

## Step 5 — Triage + export

Per run output under `data/security_results/`: triage grade ≥3, export shoestring pack for grade ≥4.

## Step 6 — Lab notebook

**Required.** Follow `lab-notebook` skill — MEMORY.md + `data/security_results/lab_notebook/YYYY-MM-DD-<slug>.md`.

## Gotchas

- `--proposals` must come **before** `investigate` on the CLI (`main.py --proposals PATH investigate …`). Placing it after the subcommand fails with "unrecognized arguments".
- Scan is lightweight (4 samples/template); investigate is full pipeline (darwinian, CPCV, etc.) — don't `--top` more than 2-3 per cron tick.
- Programs without `targets/<slug>.json` use catalogue analogue states only — Kamino has richer recon in `sources/kamino/recon.json`.
- EVM programs need `--ecosystem evm` or `all`; Solana cron should keep `ecosystem solana`.