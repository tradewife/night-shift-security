---
name: hipif
description: Hierarchical Planning and Information Folding — one consecutive Night Shift v4.1 chain (scan, semantic recon, self-interrogation, Wormhole depth, KLend depth, hunt, RSI, refine, journal). Use for nss-hipif-chain cron, manual night runs, or when the user asks for HIPIF / all-in-one loop.
---

# HIPIF — Hierarchical Planning and Information Folding

Organize long-horizon Night Shift execution around explicit **subgoals**. **Fold** completed subgoal history into compact records so context stays bounded across 50+ turns.

Orchestrate NSS CLI only. Never bypass validation gates. LLM output is untrusted until the pipeline grades it.

## Folded context C_k,j

Persisted at `data/security_results/hipif/folded_context.json`:

| Field | Symbol | Meaning |
|-------|--------|---------|
| `task` | c | High-level chain objective |
| `folded_history` | H_<k | Compact completed subgoal records |
| `current_subgoal` | g_k | Active local objective |
| `local_history` | T_k,j | Raw action-observation steps for g_k only |

Bootstrap each chain:

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main hipif init \
  --task "Bounty-depth chain SPEC v4.1.0 (2026-06)"
.venv/bin/python -m night_shift_security.cli.main hipif read
```

## Mandatory output format (every turn)

Before acting, emit:

```xml
<reflection>Evidence and failure diagnosis for current subgoal.</reflection>
<completion>yes|no</completion>
<subgoal>current_subgoal_id</subgoal>
<action>Next CLI command (required when completion=no)</action>
```

Validate your own turn:

```bash
.venv/bin/python -m night_shift_security.cli.main hipif parse --text "$(cat <<'EOF'
<reflection>...</reflection>
<completion>no</completion>
<action>...</action>
EOF
)"
```

## Reflection workflow

### Step 1 — Reflection (every turn)

Assess: is g_k complete given the latest observation? State evidence in `<reflection>`. Set `<completion>yes|no</completion>`.

### Step 2 — Branch

**Mode A (completion=yes):**

1. Fold via CLI:

```bash
.venv/bin/python -m night_shift_security.cli.main hipif fold \
  --outcome "one-line outcome" \
  --metrics '{"fork_reproduced":47,"findings":13,"status":"continue"}'
```

2. Read next subgoal: `hipif next`
3. Plan first action for g_{k+1}

**Mode B (completion=no):**

1. Ground the action:

```bash
.venv/bin/python -m night_shift_security.cli.main hipif ground \
  --subgoal depth_wormhole \
  --action-cmd "NSS_LOOP_DEPTH_SLUG=wormhole hermes/scripts/nss-bounty-loop.sh --iterations 1"
```

2. Record observation (blocked if repetition ≥3):

```bash
.venv/bin/python -m night_shift_security.cli.main hipif record \
  --action-cmd "..." \
  --observation "stdout summary"
```

3. Execute the action in the shell

## Subgoal chain (fixed order — every night, no week spread)

| # | ID | Action | Complete when |
|---|-----|--------|---------------|
| 1 | `bootstrap` | `git pull --ff-only`; read latest `lab_notebook/*.md` + `day_shift/current.md`; `hipif read` | Context + handoff reviewed |
| 2 | `scan_all` | `scan --platform all` (or bounty loop with `--refresh-scan` once) | `bounty_scan/latest.json` fresh |
| 3 | `depth_wormhole` | Wormhole `semantic map --kind bridge`, candidate store, self-interrogation, then `NSS_LOOP_DEPTH_SLUG=wormhole` bounty loop (bounty-depth: `--trials 12`) | Semantic artifacts + pipeline done; note conviction stats and `fork_reproduced` |
| 4 | `depth_wormhole_bridge` | **Bounty-depth:** semantic candidates + triage proposals + target-pinned `wormhole_shoestring.json` loop | Core/token_bridge fork repros and candidate seeds |
| 5 | `kamino_preflight` | **Bounty-depth:** `klend_live_preflight`; `NSS_KLEND_FIXTURE=0` | Validator + RPC ready |
| 6 | `depth_kamino` | `NSS_LOOP_DEPTH_SLUG=kamino` bounty loop (bounty-depth: `--trials 5`) | Harness markers / `solana_reproduced` |
| 7 | `cantina_slates` | **Bounty-depth:** current high-value Cantina slates from `NSS_HIPIF_CANTINA_SLATES` | One fold after all slates |
| 8 | `hunt_rotation` | Fork-ready slugs with depth pin (`ignore_saturation`) | Each slug hunted with `NSS_LOOP_DEPTH_SLUG` |
| 9 | `rsi_fold` | `improve`; summarize failure traces when present; read `improvement_ledger.jsonl`, `failure_signatures.jsonl`, `refinement_hints.json` | RSI actions folded into H |
| 10 | `refine_conditional` | If hints: proposals → loop with `--proposals` | Hints empty → fold as skipped |
| 11 | `coordinator_conditional` | If Kamino hints: `coordinator plan` + `cycle` | No mission → fold as skipped |
| 12 | `journal_fold` | `lab-notebook` skill: HIPIF fold summary + same-vs-different | Notebook entry written |
| 13 | `gate` | `operator-submit` skill if alert present; check `submission_alert.json` | `submit_ready` → **hard stop** |

Agent runs without bounty-depth may fold steps 4–5–7 as skipped in one turn. Deterministic runner: `nss-hipif-chain-run.py` folds each subgoal explicitly (`hipif fold --subgoal <id>`).

RSI runs inline after each bounty loop tick (steps 3–5). Step 6 aggregates ledger + hints.

## Process self-checks (penalties)

Before emitting tags, verify:

| Penalty | Rule |
|---------|------|
| Groundedness | Subgoal ∈ chain table; slugs exist in program registry |
| Termination | Do not mark complete if last observation was empty error / "nothing happens" |
| Execution loop | Never repeat identical failed action ≥3 times (`hipif record` blocks) |
| Format | All required tags present; `hipif parse` returns `format_ok: true` |

## Trust boundary + gates

- `submit_ready` requires `qualifies_for_submission()` — grade ≥4, credible reproduction, balance verified, v4 concrete candidate binding, source commit, selector/discriminator, reproduction artifact, measured impact, `export_track: submittable` (not `research_surface`)
- Scan queue uses `scan_grade3_plus` (not legacy `submission_ready` label)
- KLend: `klend_require_live`, `CLONED_DATA_ACCOUNTS`, measured delta — not fee-only CPI
- Wormhole: `wormhole_triage.json`, semantic bridge candidates, pauser-auth fork targets, economic-impact gate; triage-only remains research
- Proposals from `delegate_task` are `metadata.trusted=false`
- Target-pinned proposals must carry `target_slug`, `campaign_id`, `required_config`, and `force_target:true`; run loops with `--target <slug>`.

## Sub-skills

- Pipeline depth: `bounty-loop` (steps 3–5)
- RSI analysis: `recursive-improvement` (step 6)
- Kamino missions: `coordinator-cycle` (step 8)
- Expansion: `hypothesis-expansion` (step 7, OAuth)
- Journal: `lab-notebook` (step 9)

## Hybrid mode (default cron — SPEC v4.1.0)

`NSS_HIPIF_MODE=hybrid` (bootstrap default):

| Phase | Runner | Subgoals |
|-------|--------|----------|
| **Deterministic** | `nss-hipif-chain-run.py --phase deterministic` | bootstrap → scan → semantic recon → depth_wormhole → kamino → cantina → hunt → rsi_fold |
| **Agent** | Hermes cron + this skill | depth_wormhole_bridge → refine → coordinator → journal → gate |

After deterministic phase: `chain_status=awaiting_agent`. Agent **must** run `hipif gate` last (exits 1 if fewer than 13 folds).

```bash
.venv/bin/python -m night_shift_security.cli.main hipif status
.venv/bin/python -m night_shift_security.cli.main hipif gate   # mandatory cron finale
hermes/scripts/nss-hipif-verify-chain.sh
```

Full deterministic (no agent): `NSS_HIPIF_MODE=deterministic`

## Cron

Job `nss-hipif-chain` daily 04:00 — **hybrid agent mode** (requires xAI OAuth: `hermes --profile night-shift model`).

Bootstrap script: `hermes/scripts/nss-hipif-chain.sh` (init + deterministic bulk, then agent).

Emergency no-agent fallback: `NSS_HIPIF_MODE=deterministic hermes/scripts/nss-hipif-chain.sh`

## Bounty-depth profile (default for chain runner)

`nss-hipif-chain-run.py` sets `NSS_HIPIF_BOUNTY_DEPTH=1` and `NSS_KLEND_FIXTURE=0` to force live KLend + heavy forks:

| Knob | Default | Effect |
|------|---------|--------|
| `NSS_HIPIF_TRIALS_WORMHOLE` | 12 | 12 full pipeline attempts on Wormhole (fork top_n≥10) |
| `NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` | 4 | core/token_bridge triage proposals + shoestring |
| `NSS_HIPIF_TRIALS_KAMINO` | 5 | 5 KLend live-validator passes (preflight + `KLEND_PROBE`) |
| `NSS_HIPIF_HUNT_SLUGS` | kamino,wormhole,morpho,euler,ethena,jito | fork-ready hunt; **ignores saturated_slugs** |
| `NSS_HIPIF_CANTINA_SLATES` | uniswap,reserve-protocol,euler,polymarket,coinbase,morpho,pendle,okx,paxos | Current high-value Cantina depth slates × trials; dYdX tracked but excluded until Cosmos harness |
| `NSS_HIPIF_CANTINA_TRIALS` | 3 | trials per Cantina slate |
| `NSS_HIPIF_HUNT_TARGETS` | 4 | top scan picks, each hunted |
| `NSS_HIPIF_HUNT_TRIALS` | 3 | trials per hunt target |
| `NSS_HIPIF_REFINE_TOP` | 3 | refinement queue passes |
| `NSS_HIPIF_COORD_CYCLES` | 2 | coordinator cycles |

```bash
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init
```

## Expected runtime (RPC + validator, bounty-depth)

**60–150+ minutes** — intentional. Wormhole 12×~4m + bridge refinement + KLend live 5×~10–20m + Cantina slates + fork-ready hunt + refine + coordinator.

## NSS CLI global flags (critical)

`--config` and `--proposals` are **global** — they must appear **before** the subcommand:

```bash
# Correct
.venv/bin/python -m night_shift_security.cli.main --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target wormhole --iterations 1

.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/kamino_shoestring.json \
  coordinator plan --top 1

.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  coordinator cycle

# Wrong (will error)
.venv/bin/python -m night_shift_security.cli.main bounty loop --proposals ...
.venv/bin/python -m night_shift_security.cli.main coordinator plan --config ...
```

Scan uses `--min-bounty` (not `--min-max-bounty`).

## Deterministic fallback (no OAuth)

When xAI OAuth is missing or agent context is tight, run the full chain without an LLM:

```bash
hermes/scripts/nss-hipif-chain.sh          # init folded context
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init
```

Or set `NSS_HIPIF_MODE=deterministic` before cron bootstrap to auto-run the Python chain.

## Gotchas

- **Bulk vs agent fold boundary:** kamino/cantina/hunt/RSI folds require `NSS_HIPIF_RUNNER=deterministic` (set by `nss-hipif-chain-run.py`). Agent must wait for `agent_phase_ready: true` in `hipif status` before folding bridge/refine/coordinator.
- Hermes cron script timeout must be ≥10800s (`HERMES_CRON_SCRIPT_TIMEOUT` or `cron.script_timeout_seconds`) — default 120s kills bulk depth early.
- Write `operator-checkpoint` before context rollover mid-chain
- `hipif fold` advances `current_subgoal` automatically — do not skip fold on complete subgoals
- `hipif fold --metrics` must be valid JSON (use Python subprocess or single-quoted JSON; bash functions often break parsing)
- Cantina targets use catalogue fork anchors until live harness exists (`targets/<slug>.json`)
- Full-auto git only after `pytest` passes (SOUL policy)
- Generated PoCs are fail-closed by design. A failed generated verifier with `MEASURED_DELTA_LAMPORTS:0` or `TOKEN_DELTA:0` is a refinement seed, not a finding.
