# 2026-06-15 - Root doc alignment after v4 full run

## Context

The root markdown set drifted from the actual v4 operating state after the no-agent `nightsoul` cron conversion and successful full HIPIF run.

## Changes

- Updated current root docs to SPEC v4.0.0 and the `nightsoul` no-agent deterministic 04:00 runner.
- Replaced stale v3-oriented audit/runbook/architecture text with the current v4 baseline, current gaps, and current target slates.
- Removed stale root docs `METHODOLOGY.md` and `SUSTAINABILITY.md`; their useful content is now superseded by `SPEC.md`, `AUDIT.md`, `BOUNTY_RUN.md`, and the architecture doc.
- Reframed `SPEC.md` milestones into shipped v4 baseline plus forward backlog.

## Verification

- Root markdown stale-reference scan passed for deleted doc names and old v3 runbook markers.
- Root markdown set is now: `AGENTS.md`, `AUDIT.md`, `BOUNTY_RUN.md`, `CHANGELOG.md`, `README.md`, `SPEC.md`, `adversarial_research_architecture.md`.
