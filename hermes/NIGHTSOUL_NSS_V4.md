# NightSoul NSS v4.1 Overlay

This overlay keeps the general `nightsoul` profile aligned with the current
Night Shift Security v4 system without replacing the broader NightSoul mission.

## Night Shift Security Status

- Track repo: `/home/kt/projects/rtp/night-shift-security`
- Current system baseline: `SPEC.md` v4.1.0
- Repo-managed NSS profile/assets: `night-shift`
- Active authenticated cron owner on this machine: `nightsoul`
- Primary cron job: `nss-hipif-chain` daily 04:00 under the `nightsoul` profile, no-agent deterministic mode
- Deterministic fallback: `NSS_HIPIF_MODE=deterministic hermes/scripts/nss-hipif-chain.sh`

## v4 Operating Model

When working on Night Shift Security, treat the pipeline as:

`platform scan -> semantic recon -> concrete candidate store -> target-pinned proposals -> self-interrogation -> generated PoC -> verifier -> evidence grading -> human gate`

The bottleneck is no longer generic hypothesis generation. The bottleneck is
source-grounded, candidate-specific discovery that can survive the submission
gate.

## Current v4 Capabilities

- Semantic recon package: maps target repos into entrypoints, authority flows,
  value surfaces, bridge paths, and candidate seeds.
- Concrete candidate store:
  `data/security_results/knowledge/concrete_candidates.jsonl`.
- Target-pinned proposal envelope with `target_slug`, `required_config`,
  `allowed_templates`, `source_artifacts`, and `force_target: true`.
- `bounty loop --target <slug>` fail-fast binding for proposal-backed runs.
- Self-interrogation conviction reports before CPCV/MC/fork/Solana validation;
  bounty-depth mode applies small rank pressure toward higher-conviction candidates.
- Opengrep/SARIF ingestion via `tools opengrep`.
- Generated PoC artifacts and fail-closed verifier path via `poc generate` and
  `poc verify`.
- Failure-trace RSI via `traces summarize --slug <slug>`.
- KLend v2 artifacts: instruction discriminators, typed accounts, account diffs,
  live preflight classification, and deterministic failure classifiers.
- Wormhole economic gates: semantic bridge candidates plus impact fixtures.

## Required Commands

Run semantic recon before target depth when a repo clone exists:

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug wormhole --repo sources/wormhole/repo --kind bridge

.venv/bin/python -m night_shift_security.cli.main tools opengrep \
  --slug wormhole --repo sources/wormhole/repo

.venv/bin/python -m night_shift_security.cli.main poc generate --candidate-id <candidate_id>
.venv/bin/python -m night_shift_security.cli.main poc verify --candidate-id <candidate_id>
.venv/bin/python -m night_shift_security.cli.main traces summarize --slug <slug>
```

Target-pinned proposal runs must use global flags before the subcommand:

```bash
cd /home/kt/projects/rtp/night-shift-security
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target <slug> --iterations 1
```

## Submission Hard Gate

Do not call a result submit-ready unless the NSS engine, not the agent, confirms:

- `qualifies_for_submission() == true`
- concrete candidate binding exists
- source commit/provenance is recorded
- selector, discriminator, or instruction binding is recorded
- candidate-specific reproduction artifact exists
- impact oracle shows measured value movement or bounty-relevant state change
- evidence grading passes
- `submission_alert.json` is written and a human gate is pending

Catalogue replay, fee-only CPI, smoke triage, zero-delta generated PoC, and
semantic candidate presence alone are research outputs, not submissions.

## NightSoul Behavior

For NSS work, use the repo-managed `night-shift` assets and the authenticated
`nightsoul` cron on this machine. Use this broader `nightsoul` profile as
command infrastructure:

- inspect status and cron output
- update docs/specs
- run focused assays and tests
- create or refine NSS skills
- escalate OAuth/RPC/paid-infra blockers

Never bypass the NSS Python pipeline gates with agent judgment.
