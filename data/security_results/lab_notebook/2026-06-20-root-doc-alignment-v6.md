# 2026-06-20 — Root doc alignment after v6 Ready expansion

## Context

After orchestrator handoff (`482fd4f`, `69daa27`) and the cleanup
commit (`bf14075`), the root markdown set drifted from the new v6
operating state. The v4.2-era files (`AUDIT.md`, `BOUNTY_RUN.md`,
`SPEC_V5_COMPLETION.md`, `SYSTEM_AUDIT_2026-06-18.md`) were all pointing
at pre-v6 baselines even though `SPEC.md` and `CHANGELOG.md` were already
on v6.0.0-draft.

## Changes

- **UPDATED in place**:
  - `README.md` — status stamped `2026-06-20`, SPEC v6.0.0-draft, eight
    ready NativeHarness + ethena_native scaffolded, v6 strategy recap.
    Repository layout table rebuilt (drops `AUDIT.md` and `BOUNTY_RUN.md`
    rows; replaces with SPEC.md §3 + §13 pointers).
  - `AGENTS.md` — session-start checklist references SPEC.md §3 in place
    of `AUDIT.md`; `submit_ready=0` line and "Next focus" row updated to
    reference the v6 audit-saturation reasoning in
    `lab_notebook/2026-06-20-orchestrator-handoff-reflection.md`;
    the `v5 Phase 6` inline callout is replaced with a `v6 (2026-06-20)`
    callout that records the four retirements.
  - `SPEC.md` §13 References — replaces `AUDIT.md` / `SPEC_V5_COMPLETION.md`
    / `SYSTEM_AUDIT_2026-06-18.md` entries with the v6-actual lab notebook
    + falsification probe artifacts, plus a preservation note.
  - `day_shift/current.md` — supersession header added; reference list
    redirected to `SPEC.md` §3 + §14.
  - `hermes/SOUL.md` + `hermes/DAY_SOUL.md` + `hermes/skills/day-shift-cycle/SKILL.md`
    + `hermes/cron/jobs.example.yaml` + `hermes/scripts/nss-hipif-chain.sh`
    + `docs/agents/coding-agent-orchestrator-loop.md` — all references
    to the retired root docs rewritten to point at SPEC.md-equivalents.
  - `src/night_shift_security/native/{__init__,kamino,uniswap_v4}.py`
    + `src/night_shift_security/impact/{measured_oracle,solana_measured_oracle}.py`
    + `src/night_shift_security/hypothesis/concrete_sequences.py`
    + `foundry/test/UniswapV4PoolManagerHarness.t.sol`
    + `foundry/test/UniV4Measure.t.sol` — docstring / comment-level
    rewrites (only). Empty trailing fragments preserved.

- **DELETED** (per explicit user permission):
  - `AUDIT.md`
  - `BOUNTY_RUN.md`
  - `SPEC_V5_COMPLETION.md`
  - `SYSTEM_AUDIT_2026-06-18.md`

  Substantive content preserved in:
  - `SPEC.md` §3 (Strengths + Current Gaps) and §14 (Version History).
  - `CHANGELOG.md` per-version entries.
  - Historical `data/security_results/lab_notebook/` entries that
    already cite these files remain the immutable record of the
    pre-v6 reasoning.

- **NOT touched** (intended preservation):
  - `adversarial_research_architecture.md` — v4.2.0 architecture baseline;
    referenced from `AGENTS.md` as the architectural substrate.
  - `goal-reference.md` — strategic inspiration doc.
  - `solodit-api-ref.md` — self-contained Cyfrin Solodit API reference.

## Verification

- `git grep -nE "(AUDIT\.md|BOUNTY_RUN\.md|SPEC_V5_COMPLETION\.md|SYSTEM_AUDIT_2026-06-18\.md)" -- ':!*lab_notebook*' ':!*reflection*' ':!*self_criticism*' ':!CHANGELOG.md'`
  rejected any remaining live-link references; old links remain only
  inside the historical lab notebook / CHANGELOG.md / reflection self-doc
  files (immutable record).
- `.venv/bin/python -m pytest` still passes (87 passed across
  test_native_ethena + test_native_reserve + test_native_morpho_blue
  + test_native_aave_v3 + test_native_orca).

## Root markdown set is now

| File | Status |
|------|--------|
| `AGENTS.md` | v6-aligned |
| `CHANGELOG.md` | v6-current (already) |
| `README.md` | v6-aligned |
| `SPEC.md` | v6-current (already) |
| `adversarial_research_architecture.md` | v4.2.0 architectural baseline (preserved) |
| `goal-reference.md` | preserved |
| `solodit-api-ref.md` | preserved |
