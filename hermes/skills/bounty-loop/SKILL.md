---
name: bounty-loop
description: Autonomous Immunefi + Cantina hunt loop until a novel finding hits submit_now. Human gate for external post.
---

# Bounty Loop

Sub-skill of **HIPIF** (`hipif` skill) — used in chain steps `depth_wormhole`, `depth_kamino`, and `hunt_rotation`. Daily cron runs the full HIPIF chain, not this skill alone.

Closed **outer loop**: unified scan → pick uninvestigated target → full pipeline → score → repeat until `submit_now` qualifies or queue exhausts.

Orchestrates NSS CLI only. Never bypass validation gates or post to Immunefi/Cantina without human approval.

## Qualification gate (`submit_now`)

All must be true (engine + `compute_bounty_score`):

- `submission_recommendation == submit_now`
- `evidence_grade >= 4`
- `reproduction_tier` in `fork_reproduced` | `solana_validator`
- `catalog_analogue == false`
- `deployed_viable == true`
- `fork_evidence.balance_verified == true` (novel findings; catalogue anchors exempt)
- v4 concrete candidate present: `candidate_schema_version >= 4`, `target_pinned`, `source_ref.commit`, entrypoint selector/discriminator, candidate-specific reproduction artifact, measured non-fee impact
- **KLend:** `solana_evidence.harness_mode == live_executed` with `probe_executed` + measured balance delta — fixture/deploy-only blocked (`klend_require_live` in `kamino_klend.json`). Validator clones mainnet lending market + USDC/SOL reserves/vaults (`sources/kamino/klend_accounts.json`; marker `CLONED_DATA_ACCOUNTS`). Fee-only CPI (`live_deploy_verified`, `MEASURED_DELTA_LAMPORTS:0`) is **not** submittable.
- **Wormhole:** loop uses `wormhole_triage.json` with live fork targets and semantic bridge candidates. Governance/pause smoke or `triage_surface_verified` without token/native delta, bridge accounting violation, or bounded TVS is **not** submittable.

On qualify: writes `data/security_results/loop/submission_alert.json` (schema v2), sets `human_gate_pending` in state, **stops** the loop. Export lands in `bounty/submittable/` only when `qualifies_for_submission()` passes. Alert Kate — follow skill `operator-submit`; do not post externally without approval.

## Step 1 — Environment

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull --ff-only
# .env: ALCHEMY_API_KEY, ETHEREUM_RPC_URL, SOLANA_MAINNET_RPC_URL (validator clone depth)
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
  bounty loop --target <slug> --iterations 1
```

## Step 3 — N-trial session (high-priority target)

```bash
hermes/scripts/nss-bounty-loop.sh --trials 30 --iterations 1 --refresh-scan
```

Runs 30 independent attempts on the same picked slug before advancing queue. Not for daily cron (cost).

## Step 3b — Multi-iteration session

```bash
hermes/scripts/nss-bounty-loop.sh --iterations 3 --min-bounty 250000
```

State: `data/security_results/loop/state.json` (saturated slugs, run history, submission queue).

## Step 4 — Check alert + export tracks

```bash
cat data/security_results/loop/submission_alert.json
ls data/security_results/bounty/submittable/
.venv/bin/python -m night_shift_security.cli.main platform diff
```

If `submit_ready`: **hard stop** — human gate for Immunefi/Cantina post (skill `operator-submit`). Research-only findings stay in `bounty/research/`.

## Step 5 — RSI (automatic)

Each tick runs deterministic recursive self-improvement inline:

- `knowledge/improvement_ledger.jsonl` — append-only action log
- `loop/refinement_hints.json` — top refinement target for parametric proposals
- State fields: `cooldown_overrides`, `scan_boost_slugs`, `refinement_queue`

Standalone analysis: skill `recursive-improvement` or `improve` CLI.

## Step 6 — Lab notebook

**Required** after every loop invocation. Follow `lab-notebook` skill:

- Which slug ran, same vs different vs prior loop tick
- `best_recommendation`, saturated slugs updated?
- RPC used (EVM fork / Solana validator / shoestring)
- **Kamino:** `CLONED_DATA_ACCOUNTS`, `PROBE_ACCOUNTS`, `HARNESS_MODE`, `MEASURED_DELTA_LAMPORTS`
- **Kamino v4:** KLend instruction map, account roles, account diff path, failure classifier
- **Wormhole:** semantic candidate count, which fork targets ran, message fixtures/economic deltas, `BRIDGE_PAUSE_AUTH` in forge logs

## Saturation

Programs where **all** findings are `catalog_analogue` with no submit candidates get added to `saturated_slugs` and skipped. Seed list includes kamino, raydium, orca, marinade, wormhole, euler.

## Gotchas

- Write `operator-checkpoint` before context rollover if mid-investigation.
- Novel PoCs must emit `DELTA_WEI` in forge output for task verifier (threshold 0.1 ETH default).
- `--refresh-scan` runs full `scan --platform all` (slow); cron uses it daily; ad-hoc can omit if `bounty_scan/latest.json` is fresh.
- EVM targets need `ETHEREUM_RPC_URL` (or `FOUNDRY_FORK_URL`) for fork configs; without RPC, loop falls back to shoestring base.
- `--proposals` is a **global** CLI flag (before `bounty loop`).
- Use `--target <slug>` with any forced proposal file; target/config mismatch fails before validation.
- Catalogue fork replay (Euler, Wormhole) scores `shoestring_only` / `polish_validator` — not `submit_now`. Loop keeps hunting novel surface.
- Wormhole live bridge may lack `pauser()` getter bubbling — pauser roles read from ERC-7201 storage in triage tests; mainnet roles may be unassigned (`0x0`).
- `investigate` subcommand remains Immunefi-only; **bounty loop** uses `program_registry` for Cantina + Immunefi.
- Cron: `nss-hipif-chain` daily 04:00 runs this skill inside the HIPIF subgoal chain (agent + OAuth). Emergency no-agent fallback: `nss-bounty-loop-cron.sh.legacy`.
