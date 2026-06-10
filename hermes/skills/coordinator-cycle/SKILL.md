---
name: coordinator-cycle
description: Use when running multi-mission Kamino (or campaign) research via the deterministic coordinator — plan, delegate, cycle, journal.
---

# Coordinator Cycle (Layer 6)

Deterministic mission orchestration: one narrow template per cycle. Creative work stays in `delegate_task`; prioritization and debrief are Python coordinator only.

## Prerequisites

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull --ff-only
```

Initialize once per campaign:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  coordinator init
```

## Standard cycle

```bash
# 1. Plan next mission (machine-readable)
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  coordinator plan --top 1

# 2. Scoped proposals — either:
#    a) hypothesis-expansion skill (delegate_task) for mission.template_id only, OR
#    b) parametric refinement: .venv/bin/python hermes/scripts/nss-write-proposals.py

# 3. Execute one cycle (pipeline + debrief + state update)
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  coordinator cycle

# 4. Status + lab notebook
.venv/bin/python -m night_shift_security.cli.main coordinator status
# Follow lab-notebook skill — cite debrief JSON under knowledge/debriefs/
```

## Trust boundary

- Coordinator is **deterministic** — never override gates, scoring, or evidence grades in agent logic.
- `delegate_task` proposals remain `metadata.trusted=false`.
- One mission = one template. Retire after `coordinator cycle`; do not reuse mission_id.

## Gotchas

- Run `coordinator init` before first `plan`/`cycle` — state lives at `data/security_results/knowledge/coordinator_state.json`.
- `coordinator plan` after a cycle should surface a **different** template unless refinement (`lineage_expansion`) fired.
- Debrief JSON: `data/security_results/knowledge/debriefs/<mission_id>.json` — use for Same vs different notebook entries.
- Full pipeline in `cycle` can take minutes; cron should use `plan` + expansion + `cycle` as separate steps if needed.