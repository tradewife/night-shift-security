---
name: lab-notebook
description: Use after every NSS scan, investigation, or triage. Write lab notebook entry comparing this run to prior runs.
---

# Lab Notebook

Hermes is the **lab notebook**. The Python pipeline is the instrument; you record what was tried, what differed, and what it means.

## When to write

**Mandatory** after:
- `nss-investigate-queue` / any full pipeline run
- Immunefi scan (even if no investigate follows)
- Manual `investigate` or `run` sessions worth keeping

## Two locations (both)

### 1. Hermes memory (cross-session recall)

Use the `memory` tool to append to `MEMORY.md` in this profile. Update sections: Active campaigns, Lessons/Gotchas, Open questions.

### 2. Repo file (versioned, diffable)

Write a dated entry:

```
data/security_results/lab_notebook/YYYY-MM-DD-<slug-or-scan>.md
```

## Entry template

```markdown
# Lab entry — YYYY-MM-DD

## Trigger
cron: nss-investigate-queue | manual | ...

## Scan queue (dry-run top 3)
- slug: grade, submission_ready, analogue

## Investigated
- [slug]: config path, proposals file, campaign_id

## Delegate proposals vs last run
- New templates/params: ...
- Repeated (same as last): ...
- Rejected by validate_hypothesis: ...

## Engine outcome
- Findings: N | max grade: G | novel vs catalogue: ...
- findings_store campaign stats (if available): ...

## Same vs different
Explicit: did we probe differently, or rerun the same assay?

## Next action
One concrete step.

## Skill/recon updates
- Gotcha to add: ...
- recon.json change: ...
```

## Compare prior runs

Before writing, read when available:
- Previous `lab_notebook/*.md` for same slug
- `data/security_results/hermes_proposals/` (last 2 JSON files)
- `knowledge --campaign <id> --stats`
- `immunefi_scan/latest.json` (scan-only entries)

## Gotchas

- Do not skip the notebook because pytest passed with zero findings — "null result" is valuable.
- "Same vs different" must cite evidence (proposal diff or hypothesis_id), not vibes.
- Keep entries under ~80 lines; link to findings.json paths for detail.