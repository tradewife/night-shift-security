---
name: bounty-loop
description: Autonomous Immunefi + Cantina hunt loop until a novel finding hits submit_now. Human gate for external post.
---

# Bounty Loop

Closed **outer loop**: unified scan → pick uninvestigated target → full pipeline → score → repeat until `submit_now` qualifies or queue exhausts.

Orchestrates NSS CLI only. Never bypass validation gates or post to Immunefi/Cantina without human approval.

## Qualification gate (`submit_now`)

All must be true (engine + `compute_bounty_score`):

- `submission_recommendation == submit_now`
- `evidence_grade >= 4`
- `reproduction_tier` in `fork_reproduced` | `solana_validator`
- `catalog_analogue == false`
- `deployed_viable == true`

On qualify: writes `data/security_results/loop/submission_alert.json`, sets `human_gate_pending` in state, **stops** the loop. Alert Kate — do not post externally.

## Step 1 — Environment

```bash
cd /home/kt/projects/rtp/night-shift-security
# .env: ALCHEMY_API_KEY, ETHEREUM_RPC_URL, SOLANA_MAINNET_RPC_URL (optional)
```

## Step 2 — One iteration (cron default)

```bash
hermes/scripts/nss-bounty-loop.sh --iterations 1 --refresh-scan
```

Or with Hermes proposals for the picked target:

```bash
# After hypothesis-expansion for loop target slug:
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --iterations 1
```

## Step 3 — Multi-iteration session

```bash
hermes/scripts/nss-bounty-loop.sh --iterations 3 --min-bounty 250000
```

State: `data/security_results/loop/state.json` (saturated slugs, run history, submission queue).

## Step 4 — Check alert

```bash
cat data/security_results/loop/submission_alert.json
```

If `submit_ready`: **hard stop** — human gate for Immunefi/Cantina post.

## Step 5 — Lab notebook

**Required** after every loop invocation. Follow `lab-notebook` skill:

- Which slug ran, same vs different vs prior loop tick
- `best_recommendation`, saturated slugs updated?
- RPC used (EVM fork / Solana validator / shoestring)

## Saturation

Programs where **all** findings are `catalog_analogue` with no submit candidates get added to `saturated_slugs` and skipped. Seed list includes kamino, raydium, orca, marinade, wormhole, euler.

## Gotchas

- `--refresh-scan` runs full `scan --platform all` (slow); cron uses it daily; ad-hoc can omit if `bounty_scan/latest.json` is fresh.
- EVM targets need `ETHEREUM_RPC_URL` (or `FOUNDRY_FORK_URL`) for fork configs; without RPC, loop falls back to shoestring base.
- `--proposals` is a **global** CLI flag (before `bounty loop`).
- Catalogue fork replay (Euler, Wormhole) scores `shoestring_only` / `polish_validator` — not `submit_now`. Loop keeps hunting novel surface.
- `investigate` subcommand remains Immunefi-only; **bounty loop** uses `program_registry` for Cantina + Immunefi.