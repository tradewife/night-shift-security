---
name: hypothesis-expansion
description: Use when expanding NSS attack hypotheses via Hermes delegate_task before a pipeline run. Writes hermes_proposals JSON for external provider ingestion.
---

# Hypothesis Expansion (Hermes Delegate)

Generate untrusted attack parameter proposals via `delegate_task` subagents (Grok OAuth). Output feeds the NSS pipeline as `llm_expansion.provider: external`.

## Prerequisites

- Read target config (`kamino_shoestring.json` or caller-specified)
- Read `sources/kamino/recon.json` when target is Kamino
- Read `data/security_results/semantic/<slug>/code_map.json` and `candidate_seeds.jsonl` when present
- Seeds: run hypothesis sampling or read latest `findings.json` / grid seeds from prior pipeline stage metadata

## Workflow

1. Determine `run_id` (e.g. `kamino-immunefi-2026-06-YYYYMMDD`)
2. For each template in config `templates` array, build delegate context:
   - Parameter space from NSS generators (read `parameter_spaces.py` or sample one seed via CLI)
   - Catalog analogue from target config
   - Recon notes when available
3. Fire parallel delegates (max 3 per batch):

```
delegate_task(
  goal="Propose 2 diverse attack parameter variants for template <TEMPLATE>. Output JSON array of parameter objects only.",
  context="Night Shift Security researcher. Template: <TEMPLATE>. Seed: <SEED_PARAMS>. Parameter space: <SPACE>. Catalog analogue: <ANALOGUE>. Recon: <RECON_SUMMARY>. Untrusted — must be valid JSON array.",
  model="grok-4.3",
  provider="xai-oauth"
)
```

4. Parse each subagent response (JSON array); merge into proposals list
5. Write `data/security_results/hermes_proposals/<run_id>.json`:

```json
{
  "run_id": "...",
  "campaign_id": "kamino-immunefi-2026-06",
  "target_slug": "kamino",
  "required_config": "src/night_shift_security/config/kamino_klend.json",
  "allowed_templates": ["flash_loan_oracle", "composability_risk"],
  "source_artifacts": ["data/security_results/semantic/kamino/code_map.json"],
  "force_target": true,
  "proposals": [
    {
      "template": "flash_loan_oracle",
      "seed_id": "<optional seed hypothesis_id>",
      "parameters": { "loan_fraction_of_ceiling": 0.3, "price_skew_severity": 0.6, "oracle_dependency_score": 0.8 },
      "lineage": ["<seed_id>"],
      "delegate_note": "composability angle vs mango analogue"
    }
  ]
}
```

6. Symlink: `ln -sf <run_id>.json data/security_results/hermes_proposals/latest.json`

7. Run with explicit target pin:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target <target_slug> --iterations 1
```

## Gotchas

- Parameter keys must match NSS `parameter_spaces.py` exactly — wrong keys fail `validate_hypothesis()` silently (dropped proposals).
- `seed_id` must match actual seed `hypothesis_id` from sampled vectors or delegate proposals won't attach to seeds.
- Subagent may wrap JSON in markdown fences — strip before parse.
- If all proposals rejected, pipeline parametric fallback still runs when `--proposals` is passed.
- Missing or mismatched `target_slug` / `required_config` now fails fast for forced proposals; that is intentional.
