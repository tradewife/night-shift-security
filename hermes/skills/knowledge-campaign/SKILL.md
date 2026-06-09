---
name: knowledge-campaign
description: Use when querying NSS findings store campaign stats and lineage survival analytics.
---

# Knowledge Campaign Analytics

```bash
cd /home/kt/projects/rtp/night-shift-security

.venv/bin/python -m night_shift_security.cli.main knowledge \
  --campaign kamino-immunefi-2026-06 \
  --stats

# Lineage drill-down
.venv/bin/python -m night_shift_security.cli.main knowledge \
  --hypothesis-id <id>
```

Store path: `data/security_results/knowledge/findings_store.jsonl`

## Gotchas

- Campaign id must match `campaign.id` in run config (`kamino_shoestring.json`).
- Empty stats means no runs recorded with that campaign id yet.