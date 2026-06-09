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
- When implementing, respect the constraints listed in SPEC (especially around validation gates and LLM trust boundaries).
- After completing work, update `SPEC.md` to reflect new status and version.
- Push to `main` (preferred) or merge your branch quickly.

## Current Baseline (as of 2026-06-09)
- Architecture is at **v2.1** (`adversarial_research_architecture.md`).
- SPEC **v2.0.2**: Immunefi path, shoestring/Kamino, reality-check fields, dual grading tracks, recon slice, novel vector catalog, campaigns, LLM eval harness.
- **179 tests** passing (4 skipped).
- Next focus: first real Immunefi submission with grant-funded validator replay; deeper on-chain recon.

## Communication
- When work is complete, open a PR or push to main with a clear summary.
- Reference the relevant SPEC section in commits and PR descriptions.
