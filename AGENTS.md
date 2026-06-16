# Night Shift Security — Agent Onboarding & Workflow

**For coding agents working in this repository.**

## Core philosophy

- High-agency, rigorous research systems work.
- Start from existing code.
- Preserve statistical rigor, provenance, and reproducibility.
- Move fast but document decisions clearly.

## Solo developer workflow

- Push directly to `main` when work is ready (or at clear checkpoints).
- Short-lived branches are acceptable; quick merges to `main` are preferred.
- Use clear commit messages referencing `SPEC.md` sections.
- After significant work: update `SPEC.md` (version + status), `CHANGELOG.md`, and root docs if behavior changed.

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + [`hermes/DAY_SOUL.md`](hermes/DAY_SOUL.md) | Session-planned arcs: infra, validator replay, tests, drafts, intel → backlog. Skill: `day-shift-cycle`. |
| **Night Shift** | Hermes profile `nightsoul` cron + repo-managed `night-shift` assets | **HIPIF bounty-depth chain** (daily 04:00): no-agent full v4.2 runner: scan → Solodit corpus → semantic recon → concrete candidates → self-interrogation → Wormhole → bridge → KLend live → Cantina → fork-ready hunt → failure-trace RSI → refine → coordinator → gate. Optional 07:00 authenticated Solodit agent writes untrusted proposals for the next deterministic run. |

Session boundary = one plan in [`data/security_results/day_shift/current.md`](data/security_results/day_shift/current.md) until close; then [`next.md`](data/security_results/day_shift/next.md) queues the following session. Day Shift writes **Night Shift handoff** so cron does not repeat finished assays.

## Session start checklist

1. `git pull`
2. **Day Shift open:** `day_shift/current.md` → lab notebook (newest first) → `SPEC.md` → `AUDIT.md` (gaps) → cron output
3. Optional: `intel/latest.md`, `hipif/folded_context.json`, `loop/state.json`
4. Read `adversarial_research_architecture.md` for architectural baseline

Do not re-plan from scratch if the lab notebook already answers what changed last time.

## Current baseline (2026-06-16, SPEC v4.2.0)

| Item | Value |
|------|-------|
| Architecture | v4.2.0 (`adversarial_research_architecture.md`) |
| Tests | **391 passed**, 5 skipped, 3 deselected in sandbox-safe run; focused Solodit/self-interrogation/pipeline tests: **66 passed** |
| Platform intel | `platform sync` — 208 Immunefi + 52 Cantina; `platform solodit-sync` for Cyfrin Solodit findings corpus |
| Export tracks | `bounty/research/` vs `bounty/submittable/` (gated on `qualifies_for_submission()`) |
| Primary cron | `nightsoul` profile `nss-hipif-chain` 04:00 — **no-agent** deterministic full v4.2 runner through final HIPIF gate |
| Deterministic fallback | `NSS_HIPIF_MODE=deterministic hermes/scripts/nss-hipif-chain.sh` |
| Bounty-depth env | `NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0` (cron default) |
| Self-interrogation | Advisory conviction reports by default; bounty-depth rank pressure enabled |
| Solodit | Deterministic corpus sync + pattern JSONL; authenticated follow-up agent may write untrusted proposals only |
| `submit_ready` | **0** — gates correct; see `AUDIT.md` current gaps |
| Next focus | Bind top v4 Wormhole/KLend concrete candidates to real deployed state and measured value-moving repros |

### Bounty-depth chain (deterministic)

```bash
set -a && source .env && set +a
export NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_FIXTURE=0
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init --phase full
```

Expected runtime: **60–150+ min** with RPC + `solana-test-validator`. Latest verified full v4.1 run: 4805s, 13/13 folds, `gate_ok=true`, `submit_ready=false`.

| Knob | Default |
|------|---------|
| `NSS_HIPIF_TRIALS_WORMHOLE` | 12 |
| `NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` | 4 |
| `NSS_HIPIF_TRIALS_KAMINO` | 5 |
| `NSS_HIPIF_HUNT_SLUGS` | kamino,wormhole,morpho,euler,ethena,jito (fork-ready) |
| `NSS_HIPIF_CANTINA_SLATES` | uniswap,reserve-protocol,euler,polymarket,coinbase,morpho,pendle,okx,paxos |
| `NSS_SOLODIT_SCOPE` | target-plus-pattern |
| `NSS_SOLODIT_MAX_PAGES` | 2 |

### Target-specific notes

- **Wormhole:** clone `sources/wormhole/repo`, run `semantic map --slug wormhole --repo sources/wormhole/repo --kind bridge`, optional `tools opengrep`, then `nss-write-wormhole-triage-proposals.py` → `wormhole_shoestring.json`
- **KLend live:** `NSS_KLEND_FIXTURE=0` + RPC; `klend_live_preflight()` before Kamino depth; fee-only CPI ≠ `submit_ready`
- **Block C:** `novel score` → `data/security_results/novel/human_gate.json`

## Lab notebook — mandatory

Hermes is the lab notebook; the Python pipeline is the instrument.

**Read at session start:**
1. `data/security_results/lab_notebook/*.md` (newest first)
2. `~/.hermes/profiles/nightsoul/memories/MEMORY.md` and `~/.hermes/profiles/night-shift/memories/MEMORY.md` (if present)
3. `~/.hermes/profiles/nightsoul/cron/` and `~/.hermes/profiles/night-shift/cron/` (last `nss-hipif-chain`)

**Write after every scan/investigate:** skill `hermes/skills/lab-notebook/SKILL.md`. If cron ran but `lab_notebook/` is empty, flag it.

## Hermes orchestration

```bash
./hermes/install-profile.sh
./hermes/install-nightsoul-overlay.sh
hermes --profile nightsoul doctor
cd /home/kt/projects/rtp/night-shift-security && hermes --profile nightsoul
```

| Component | Path |
|-----------|------|
| SOUL + skills | `hermes/` → `~/.hermes/profiles/night-shift/`; NSS v4 overlay + linked skills → `~/.hermes/profiles/nightsoul/` |
| Cron recipes | `hermes/cron/jobs.example.yaml` |
| Proposals sidecar | `data/security_results/hermes_proposals/latest.json` |
| Folded context | `data/security_results/hipif/folded_context.json` |

### Workflows

| Workflow | Path |
|----------|------|
| HIPIF chain | `hipif` skill → subgoals → `hipif` CLI hooks → `bounty-loop` / `recursive-improvement` / `coordinator-cycle` / `lab-notebook` |
| RSI | `improve` CLI → `improvement_ledger.jsonl` + `refinement_hints.json` |
| Single expansion | `hypothesis-expansion` → `delegate_task` → `--proposals` → pipeline |

### Trust boundary

Hermes orchestrates CLI/MCP only. **Never bypass:**
- `validate_hypothesis()`
- Evidence grading, CPCV, task verifier, credible harness gate
- `submission_alert.json` human gate

LLM/subagent output: `metadata.trusted=false`. Checkpoint before rollover: skill `operator-checkpoint`.

**Full-auto git:** Hermes may commit + push to `main` only after `.venv/bin/python -m pytest` passes (`hermes/SOUL.md`).

**Hermes may mutate:** `sources/*/recon.json`, `data/security_results/**`, `hermes/skills/**` Gotchas. Core pipeline Python requires tests.

## NSS CLI — global flags

`--config` and `--proposals` are **global** — must appear **before** the subcommand:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --iterations 1
```

Scan uses `--min-bounty` (not `--min-max-bounty`).

## Communication

- Push to `main` with clear summary referencing SPEC section.
- Update `SPEC.md`, `CHANGELOG.md`, and `AUDIT.md` gaps when closing known issues.
