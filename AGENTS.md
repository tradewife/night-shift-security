# Night Shift Security — Agent Onboarding & Workflow

**For coding agents working in this repository.**

## Core Philosophy
- High-agency, rigorous research systems work.
- Start from existing code.
- Preserve statistical rigor, provenance, and reproducibility.
- Move fast but document decisions clearly.

## Solo Developer Workflow Preference

The maintainer of this repository is a solo operator and prefers a simple, low-friction workflow:

- Push directly to `main` when work is ready (or at clear checkpoints).
- Short-lived branches are acceptable for organization during active development, but quick merges to `main` are preferred.
- No mandatory long-lived feature branches or PR blocking for routine work.
- Use clear commit messages that reference relevant sections in `SPEC.md`.
- After merging significant work, update `SPEC.md` (version + status) and clean up the branch if one was used.

This keeps velocity high while maintaining traceability through SPEC.md and commit history.

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + [`hermes/DAY_SOUL.md`](hermes/DAY_SOUL.md) | Session-planned arcs: infra, validator replay, tests, drafts, intel → backlog. Skill: `day-shift-cycle`. |
| **Night Shift** | Hermes profile `night-shift` + cron | **bounty loop** (daily), coordinator (weekly Kamino), immunefi digest. Skills: `bounty-loop`, `recursive-improvement`, `coordinator-cycle`. |

Session boundary = one plan in [`data/security_results/day_shift/current.md`](data/security_results/day_shift/current.md) until close; then [`next.md`](data/security_results/day_shift/next.md) queues the following session. Day Shift writes **Night Shift handoff** so cron does not repeat finished assays.

## General Instructions
- Always `git pull` at the start of a session.
- **Day Shift open:** read `day_shift/current.md` → lab notebook → SPEC → cron output → optional `intel/latest.md`.
- Read the latest `SPEC.md` to understand the current task and baseline.
- Read `adversarial_research_architecture.md` for the architectural baseline.
- **Check the lab notebook** before Hermes, autonomous-run, or bounty work (see below).
- When implementing, respect the constraints listed in SPEC (especially around validation gates and LLM trust boundaries).
- After completing work, update `SPEC.md` to reflect new status and version.
- Push to `main` (preferred) or merge your branch quickly.

## Lab notebook — agents must read this

Hermes is the lab notebook; the Python pipeline is the instrument. **At session start** (or before changing cron, skills, or investigation workflow), read:

1. **Latest repo entries** — `data/security_results/lab_notebook/*.md` (newest first)
2. **Profile memory** — `~/.hermes/profiles/night-shift/memories/MEMORY.md` (if present)
3. **Recent cron output** — `~/.hermes/profiles/night-shift/cron/output/` (last `nss-bounty-loop` or investigate-queue run)

Look for: which targets were queued, **same vs different** vs prior runs, open questions, and Gotchas. Do not re-plan from scratch if the notebook already answers what changed last time.

After you run or triage a scan/investigate session, ensure a notebook entry exists (skill `hermes/skills/lab-notebook/SKILL.md`). If cron ran but `lab_notebook/` is empty, flag it — SOUL requires journaling.

## Current Baseline (as of 2026-06-13)
- Architecture is at **v3.0** (`adversarial_research_architecture.md`).
- SPEC **v3.0.0**: Operator Layer Phase A — task verifier, checkpoint, `bounty loop --trials`.
- **241 tests** passing (5 skipped without live validator).
- Cron: `nss-bounty-loop` daily 04:00 (primary); `nss-investigate-queue` → weekly Kamino depth only.
- Next focus: novel non–catalogue-analogue `submit_now`; KLend / Wormhole program-specific surface.

## Hermes Orchestration

Autonomous runs use **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** profile `night-shift` (NSS-only; separate from `nightsoul` cross-track profile).

```bash
./hermes/install-profile.sh
hermes --profile night-shift doctor
cd /home/kt/projects/rtp/night-shift-security && hermes --profile night-shift
```

| Component | Path |
|-----------|------|
| SOUL + skills | `hermes/` (symlinked into `~/.hermes/profiles/night-shift/`) |
| Cron recipes | `hermes/cron/jobs.example.yaml` |
| Proposals sidecar | `data/security_results/hermes_proposals/latest.json` |

**Workflow (bounty loop):** `bounty-loop` → `bounty loop` CLI → inline RSI → `lab-notebook` → stop on `submit_ready` + human gate.

**Workflow (RSI):** `recursive-improvement` skill or `improve` CLI → check `improvement_ledger.jsonl` + `refinement_hints.json`.

**Workflow (Kamino depth):** `coordinator-cycle` (weekly cron) → `coordinator plan` → scoped `hypothesis-expansion` → `coordinator cycle` → `lab-notebook`.

**Workflow (single run):** `hypothesis-expansion` skill → `delegate_task` (Grok) → `--proposals` → NSS pipeline → triage.

**Trust boundary:** Hermes orchestrates CLI/MCP only. Never bypass `validate_hypothesis()`, evidence grading, task verifier, or gates. LLM/subagent output is `metadata.trusted=false`. Write `operator/checkpoint.json` before context rollover (skill `operator-checkpoint`).

**Full-auto git:** Hermes may commit + push to `main` only after `.venv/bin/python -m pytest` passes (see `hermes/SOUL.md`).

**Lab notebook:** Hermes appends `MEMORY.md` (profile) + `data/security_results/lab_notebook/*.md` (repo) after every scan/investigate — mandatory per `hermes/SOUL.md`.

**Hermes may mutate:** `sources/*/recon.json`, `data/security_results/**`, `hermes/skills/**` Gotchas. Core pipeline Python requires tests.

## Communication
- When work is complete, open a PR or push to main with a clear summary.
- Reference the relevant SPEC section in commits and PR descriptions.
