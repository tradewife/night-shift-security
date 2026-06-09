---
name: night-shift-run
description: Use when running the full NSS security pipeline with Hermes expansion, triage, and optional git push after pytest.
---

# Night Shift Run (Orchestration)

End-to-end scoped run: expand → pipeline → triage → optional commit.

## Standard Kamino shoestring

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull --ff-only

# 1. External expansion (delegate_task)
# Follow hypothesis-expansion skill → hermes_proposals/latest.json

# 2. Pipeline
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  run

# 3. Triage latest findings.json under data/security_results/
# Summarize: evidence grade >= 3, reproduction_tier, catalog_analogue, submission_readiness

# 4. Optional shoestring export if grade >= 4
RUN_JSON=$(ls -t data/security_results/*/findings.json 2>/dev/null | head -1)
.venv/bin/python -m night_shift_security.cli.main submission --input "$RUN_JSON"
```

## Full-auto git (SOUL policy)

Only after `.venv/bin/python -m pytest` passes:

```bash
git add -A && git commit -m "nss: <summary> (SPEC v2.0.3 Hermes run)" && git push origin main
```

## Gotchas

- Without `latest.json`, omit `--proposals` for parametric-only run.
- Kamino uses live target harness — catalog path is `targets/kamino.json`.
- Campaign id in config: `kamino-immunefi-2026-06` — pass to `knowledge --campaign`.