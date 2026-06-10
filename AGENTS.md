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

## General Instructions
- Always `git pull` at the start of a session.
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
3. **Recent cron output** — `~/.hermes/profiles/night-shift/cron/output/` (last investigate-queue run)

Look for: which targets were queued, **same vs different** vs prior runs, open questions, and Gotchas. Do not re-plan from scratch if the notebook already answers what changed last time.

After you run or triage a scan/investigate session, ensure a notebook entry exists (skill `hermes/skills/lab-notebook/SKILL.md`). If cron ran but `lab_notebook/` is empty, flag it — SOUL requires journaling.

## Current Baseline (as of 2026-06-10)
- Architecture is at **v2.1** (`adversarial_research_architecture.md`).
- SPEC **v2.0.4**: Hermes outer loop + deterministic Coordinator (Layer 6 mission lifecycle).
- **197 tests** passing (4 skipped).
- Next focus: first real Immunefi submission with grant-funded validator replay; deeper on-chain recon.

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

**Workflow (multi-run):** `coordinator-cycle` skill → `coordinator plan` → scoped `hypothesis-expansion` → `coordinator cycle` → `lab-notebook`.

**Workflow (single run):** `hypothesis-expansion` skill → `delegate_task` (Grok) → `--proposals` → NSS pipeline → triage.

**Trust boundary:** Hermes orchestrates CLI only. Never bypass `validate_hypothesis()`, evidence grading, or gates. LLM/subagent output is `metadata.trusted=false`.

**Full-auto git:** Hermes may commit + push to `main` only after `.venv/bin/python -m pytest` passes (see `hermes/SOUL.md`).

**Lab notebook:** Hermes appends `MEMORY.md` (profile) + `data/security_results/lab_notebook/*.md` (repo) after every scan/investigate — mandatory per `hermes/SOUL.md`.

**Hermes may mutate:** `sources/*/recon.json`, `data/security_results/**`, `hermes/skills/**` Gotchas. Core pipeline Python requires tests.

## Communication
- When work is complete, open a PR or push to main with a clear summary.
- Reference the relevant SPEC section in commits and PR descriptions.
