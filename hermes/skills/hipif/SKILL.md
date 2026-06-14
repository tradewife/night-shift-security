---
name: hipif
description: Hierarchical Planning and Information Folding — one consecutive Night Shift chain (scan, Wormhole depth, KLend depth, hunt, RSI, refine, journal). Use for nss-hipif-chain cron, manual night runs, or when the user asks for HIPIF / all-in-one loop.
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
  --task "Night chain SPEC v3.1.0"
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
| 3 | `depth_wormhole` | `NSS_LOOP_DEPTH_SLUG=wormhole` bounty loop (bounty-depth: `--trials 12`) | Pipeline done; note `fork_reproduced` |
| 4 | `depth_wormhole_bridge` | **Bounty-depth:** triage proposals + `wormhole_shoestring.json` loop | Core/token_bridge fork repros |
| 5 | `kamino_preflight` | **Bounty-depth:** `klend_live_preflight`; `NSS_KLEND_FIXTURE=0` | Validator + RPC ready |
| 6 | `depth_kamino` | `NSS_LOOP_DEPTH_SLUG=kamino` bounty loop (bounty-depth: `--trials 5`) | Harness markers / `solana_reproduced` |
| 7 | `cantina_slates` | **Bounty-depth:** reserve-protocol,coinbase,morpho,euler depth passes | One fold after all slates |
| 8 | `hunt_rotation` | Fork-ready slugs with depth pin (`ignore_saturation`) | Each slug hunted with `NSS_LOOP_DEPTH_SLUG` |
| 9 | `rsi_fold` | `improve`; read `improvement_ledger.jsonl` tail + `refinement_hints.json` | RSI actions folded into H |
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

- `submit_ready` requires grade ≥4, credible reproduction, balance verified — unchanged from `bounty-loop` skill
- KLend: `klend_require_live`, `CLONED_DATA_ACCOUNTS`, measured delta — not fee-only CPI
- Wormhole: `wormhole_triage.json`, pauser-auth fork targets
- Proposals from `delegate_task` are `metadata.trusted=false`

## Sub-skills

- Pipeline depth: `bounty-loop` (steps 3–5)
- RSI analysis: `recursive-improvement` (step 6)
- Kamino missions: `coordinator-cycle` (step 8)
- Expansion: `hypothesis-expansion` (step 7, OAuth)
- Journal: `lab-notebook` (step 9)

## Cron

Job `nss-hipif-chain` daily 04:00 — **agent mode** (requires xAI OAuth: `hermes --profile night-shift model`).

Bootstrap script: `hermes/scripts/nss-hipif-chain.sh` (init context + env).

Replaces week-spread `nss-bounty-loop` Mon/Thu depth rotation and absorbs `nss-investigate-queue` / `nss-coordinator-kamino` into steps 7–8.

Emergency no-agent fallback: `hermes/scripts/nss-bounty-loop-cron.sh.legacy`

## Bounty-depth profile (default for chain runner)

`nss-hipif-chain-run.py` sets `NSS_HIPIF_BOUNTY_DEPTH=1` and `NSS_KLEND_FIXTURE=0` to force live KLend + heavy forks:

| Knob | Default | Effect |
|------|---------|--------|
| `NSS_HIPIF_TRIALS_WORMHOLE` | 12 | 12 full pipeline attempts on Wormhole (fork top_n≥10) |
| `NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` | 4 | core/token_bridge triage proposals + shoestring |
| `NSS_HIPIF_TRIALS_KAMINO` | 5 | 5 KLend live-validator passes (preflight + `KLEND_PROBE`) |
| `NSS_HIPIF_HUNT_SLUGS` | wormhole,morpho,euler,ethena | fork-ready hunt; **ignores saturated_slugs** |
| `NSS_HIPIF_CANTINA_SLATES` | pendle,morpho,euler | 3 Cantina depth slates × trials |
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
  bounty loop --iterations 1

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

- Write `operator-checkpoint` before context rollover mid-chain
- `hipif fold` advances `current_subgoal` automatically — do not skip fold on complete subgoals
- `hipif fold --metrics` must be valid JSON (use Python subprocess or single-quoted JSON; bash functions often break parsing)
- Cantina targets use catalogue fork anchors until live harness exists (`targets/<slug>.json`)
- Full-auto git only after `pytest` passes (SOUL policy)