---
name: novel-vector-digest
description: Use when summarizing NSS novel vector catalog exports from pipeline Stage 5f outputs.
---

# Novel Vector Digest

After a pipeline run, catalog lives under:

```
data/security_results/novel_vectors/
```

If missing, re-run pipeline (Stage 5f exports when candidates exist) or check latest `findings.json` for high `novelty_score` vectors.

## Weekly digest prompt

1. Read latest novel vector catalog JSON/MD if present
2. Summarize: template distribution, top novelty scores, overlap with Immunefi scan targets
3. Cross-reference `knowledge --campaign` survival stats
4. Write brief to `data/security_results/hermes_proposals/digests/novel-<date>.md` (optional)

## Gotchas

- Novel catalog only populates when pipeline produces qualifying candidates — empty is normal on shoestring runs.
- Do not conflate catalogue analogues with novel vectors — check `catalog_analogue` field in findings.