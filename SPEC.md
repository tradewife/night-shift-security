# Night Shift Security — Technical Specification

**Version:** 1.8  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-08)

- Architecture baseline **v2** (`adversarial_research_architecture.md`).
- Hypothesis Generation Layer **v1.4** (all 7 templates, versioned mapping, lineage).
- **LLM provider integration shipped** (v1.5): `llm_provider.py`, `LLMExpansionOrchestrator`, LiteLLM optional dep, mandatory `validate_hypothesis()` gate, parametric fallback, `metadata.trusted=false`.
- **Validation Layer strengthening shipped** (v1.7): multi-axis scores (Likelihood, Impact, Stealth, Generality), evidence grading (Levels 0–4), scoring integration, persistence on candidates/findings/hypothesis metadata.
- `AGENTS.md` — solo developer workflow (push to main when ready).
- **133 tests passing** (4 skipped).

---

## Validation Layer (v1.7 — Shipped)

### Multi-Axis Scores

Each candidate carries four axis scores (0.0–1.0) in `axis_scores`:

| Axis | Source |
|------|--------|
| Likelihood | `mc_reproducibility` when MC run, else `success_rate` |
| Impact | Normalized `mean_economic_impact_usd` / `mc_impact_p50_usd` |
| Stealth | `realism_score` |
| Generality | `generality` |

`axis_survival_rate` = geometric mean across axes.

### Evidence Grading

| Level | Label | Criteria |
|-------|-------|----------|
| 0 | none | Rejected or failed MC |
| 1 | monte_carlo_survivor | Passed gates (+ MC when run) |
| 2 | cpcv_survivor | CPCV/PBO survived (`SAFE`/`ELEVATED`, pbo ≤ max) |
| 3 | reproduced | `fork_reproduced` or `solana_reproduced` |
| 4 | root_cause_artifacts | Level 3 + invariant violations + reproduction steps + impact evidence |

Severity scoring incorporates evidence grade multiplier and axis survival blend. Fork/solana bonuses stack on top.

Config (`validation_layer` in `default.json`):

```json
{
  "validation_layer": {
    "impact_ceiling_usd": 100000000,
    "level_1_mc_min": 0.70,
    "max_pbo": 0.30
  }
}
```

---

## Enabling LLM Expansion

```bash
pip install -e ".[llm]"
export OPENAI_API_KEY="sk-..."
# Set llm_expansion.enabled: true in config
```

**Safety invariants**: LLM output untrusted; every proposal passes `validate_hypothesis()`; parametric fallback on failure; LLM never participates in gates or scoring.

---

## Next Focus

- Findings store with lineage support (architecture v2 Layer 6).
- Lineage survival analytics.
- Early structural filters in Hypothesis Generation.

---

## Previous Increments

- v1.7: Validation Layer strengthening (multi-axis + evidence grading).
- v1.5: Real LLM provider integration.
- v1.4: Hypothesis Generation Layer + mapping + lineage.

---

*End of v1.8 update.*