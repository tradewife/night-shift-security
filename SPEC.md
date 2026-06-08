# Night Shift Security — Technical Specification

**Version:** 2.0  
**Date:** 2026-06-09  
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-09)

- Architecture baseline **v2.1** (`adversarial_research_architecture.md`).
- Hypothesis Generation Layer **v1.4** (all 7 templates, versioned mapping, lineage).
- **LLM provider integration shipped** (v1.5): `llm_provider.py`, `LLMExpansionOrchestrator`, LiteLLM optional dep, mandatory `validate_hypothesis()` gate, parametric fallback, `metadata.trusted=false`.
- **Validation Layer shipped** (v1.7): multi-axis scores, evidence grading (Levels 0–4), scoring integration.
- **Early structural filters + findings store shipped** (v1.9).
- **Immunefi-ready bounty path shipped** (v2.0): zero-cost LLM configs, Immunefi submission packs, live-target harness.
- `BOUNTY_RUN.md` — zero-budget command sequences for grant/bounty workflows.
- **158 tests passing** (4 skipped).

---

## v2.0: Immunefi-Ready Bounty Path (Shipped)

**Goal**: End-to-end zero-budget execution producing Level 3–4 catalog findings and submission-ready bounty artifacts.

### Phase 1 — Zero-Cost LLM Baseline

| Config | Purpose |
|--------|---------|
| `config/default.json` | CI default — `llm_expansion.enabled: false`, parametric fallback |
| `config/grok.json` | Grok/Hermes OAuth via `resolve_litellm_credentials()` (`~/.grok/auth.json`, `XAI_API_KEY`) |
| `config/ollama.json` | Local Ollama via LiteLLM `api_base: http://localhost:11434` |

Credential order: `config.api_key` → `api_key_env` → Grok OAuth → Hermes OAuth.

### Phase 2 — Immunefi Submission Packs

- `export/immunefi_submission.py` — markdown report, severity justification, repro script (Solidity or Solana shell), JSON metadata.
- `bounty/pipeline.py` — `export_bounty_artifacts()` wires standard pack + Immunefi manifest.
- Pipeline Stage 6b auto-exports when `bounty.immunefi_packs: true` (default).
- CLI: `bounty --immunefi`, `immunefi` subcommand.
- Verified: full catalog run produces Level 4 `solana_reproduced` findings; target run emits Immunefi packs.

### Phase 3 — Live-Target Harness

- `data/target_config.py` — `LiveTarget` loader from inline config or `config/targets/*.json`.
- `core/target_harness.py` — scoped vector generation + evaluation against target states.
- Bundled targets: `solend-whale-2022`, `cashio-2022`, `euler-finance-2023`.
- `config/target_run.json` — example scoped Solend run.

```json
"target": {
  "enabled": true,
  "config_path": "targets/solend-whale-2022.json"
}
```

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

# Zero-cost options (see BOUNTY_RUN.md):
.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/grok.json run
.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/ollama.json run
```

**Safety invariants**: LLM output untrusted; every proposal passes `validate_hypothesis()`; parametric fallback on failure; LLM never participates in gates or scoring.

---

## v2.0.1: Shoestring Submission (Shipped)

**Goal**: Zero-RPC bounty pack polish while grant budget is pending.

- `config/shoestring.json` — fixture-only Solana validation, fork off, Crema anchor target.
- `export/shoestring_submission.py` — selects best Level 4+ finding, exports single pack under `bounty/shoestring/<exploit-id>/`.
- Catalog-grounded Immunefi markdown + runnable fixture repro script (no RPC).
- CLI: `submission` subcommand.
- `resolve_exploit_id()` prefers strict `solana_evidence` over fuzzy rediscovery.

See `BOUNTY_RUN.md` §6.

---

## Next Focus (Post v2.0.1)

1. **First real Immunefi submission** — upgrade shoestring pack to validator replay (Solend/Cashio) once grant-funded RPC is available.
2. **Solana Slice 3** — validator clone replay for Mango Markets.
3. **Novel vector campaigns** — use live-target harness against active Immunefi programs (not just catalog anchors).
4. **LLM expansion quality eval** — compare Grok vs Ollama variant acceptance rates under `validate_hypothesis()` gate.

See `BOUNTY_RUN.md` for exact commands.

---

## Previous Increments

- v2.0: Zero-cost LLM configs, Immunefi submission packs, live-target harness, `BOUNTY_RUN.md`.
- v1.9: Early structural filters + lightweight findings store.
- v1.8: Hypothesis generation improvements + validation layer completion scope.
- v1.7: Validation Layer strengthening (multi-axis + evidence grading).
- v1.5: Real LLM provider integration.
- v1.4: Hypothesis Generation Layer + mapping + lineage.

---

*End of v2.0 update.*