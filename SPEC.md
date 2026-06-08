# Night Shift Security — Technical Specification

**Version:** 1.9  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-08)

- Architecture baseline **v2.1** (`adversarial_research_architecture.md`).
- Hypothesis Generation Layer **v1.4** (all 7 templates, versioned mapping, lineage).
- **LLM provider integration shipped** (v1.5): `llm_provider.py`, `LLMExpansionOrchestrator`, LiteLLM optional dep, mandatory `validate_hypothesis()` gate, parametric fallback, `metadata.trusted=false`.
- **Validation Layer shipped** (v1.7): multi-axis scores (Likelihood, Impact, Stealth, Generality), evidence grading (Levels 0–4), scoring integration, persistence on candidates/findings/hypothesis metadata.
- **Early structural filters shipped** (v1.9): ranking signals, pre-simulation filtering, priority-sorted evaluation.
- **Lightweight findings store shipped** (v1.9): JSONL lineage store, survival analytics, CLI `knowledge` command.
- `METHODOLOGY.md` — adapted research/audit process.
- `AGENTS.md` — solo developer workflow (push to main when ready).
- **146 tests passing** (4 skipped).

---

## v1.9: Early Structural Filters + Findings Store (Shipped)

**Goal**: Reduce wasted computation on low-quality hypotheses and persist lineage-aware findings for campaign analytics.

### Part A: Ranking Signals

Each attack vector carries lightweight metadata at generation time:

| Signal | Purpose |
|--------|---------|
| `priority_score` | Pre-evaluation ranking (impact + novelty + testability blend) |
| `novelty_score` | Deviation from template centroid — favors less obvious vectors |
| `evidence_potential` | Heuristic likelihood of reaching higher evidence grades |
| `impact_proxy` | Template-specific economic/governance impact estimate |
| `testability_score` | Simulation interpretability |

Attached in: `ranking.py`, `hypothesis_to_attack_vector()`, `generate_attack_vectors()`, `BaseHypothesisGenerator._make_hypothesis()`.

### Part B: Early Structural Filters

Pre-simulation gate in Stage 1 (`structural_filters.py`):

| Filter | Action |
|--------|--------|
| Structural validity | `validate_hypothesis()` on hypothesis-layer vectors |
| Dedup fingerprint | Skip duplicate `(template_id, params)` within a run |
| Feasibility heuristics | Template-specific structural impossibilities |
| Priority floor | Skip below `min_priority_score` (default **0.05**) |

**Bypass**: catalog seeds and ground-truth vectors skip priority floor only.

Config (`hypothesis_generation.structural_filters` in `default.json`):

```json
{
  "structural_filters": {
    "enabled": true,
    "dedupe": true,
    "feasibility_checks": true,
    "min_priority_score": 0.05
  }
}
```

### Part C: Lineage on Findings

`Finding` schema extended with `hypothesis_id`, `parent_ids`, `lineage`, `generation_method`, `priority_score`, `novelty_score`. Propagated through `findings_from_candidates()`, run JSON, and public export payloads.

### Part D: Lightweight Findings Store

Append-only JSONL at `data/security_results/knowledge/findings_store.jsonl`.

- Records all evaluated candidates + promoted findings per run
- Captures lineage, gate outcomes, evidence grades
- Hook runs **after Stage 5d deduplication, before export**

Analytics: `lineage_survival_stats()`, `ancestors()`, `descendants()`, `best_evidence_per_lineage_root()`.

CLI: `night-shift knowledge --stats` or `--hypothesis-id <id>`.

Config:

```json
{
  "findings_store": {
    "enabled": true,
    "path": "data/security_results/knowledge/findings_store.jsonl"
  }
}
```

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

- Compositional and bounded iterative refinement in Hypothesis Generation.
- Lineage-informed campaign orchestration (bias generation toward high-survival lineages).
- Tune `min_priority_score` using findings store analytics from real runs.

---

## Previous Increments

- v1.9: Early structural filters + lightweight findings store.
- v1.8: Hypothesis generation improvements + validation layer completion scope.
- v1.7: Validation Layer strengthening (multi-axis + evidence grading).
- v1.5: Real LLM provider integration.
- v1.4: Hypothesis Generation Layer + mapping + lineage.

---

*End of v1.9 update.*