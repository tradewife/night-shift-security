# Night Shift Security — Technical Specification

**Version:** 2.0.3  
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
- **Shoestring + Kamino target shipped** (v2.0.1): zero-RPC packs, Immunefi scan CLI, `targets/kamino.json`.
- **Architecture gap closure shipped** (v2.0.2): reality-check fields, dual grading tracks, recon slice, novel vector catalog, campaigns, LLM eval harness, Mango validator profile.
- **Hermes integration shipped** (v2.0.3): `night-shift` profile bundle, external proposals bridge, `delegate_task` expansion path, cron recipes.
- `BOUNTY_RUN.md` — zero-budget command sequences for grant/bounty workflows.
- **185 tests passing** (4 skipped).

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
- Bundled targets: `solend-whale-2022`, `cashio-2022`, `euler-finance-2023`, `crema-finance-2022`, `kamino`.
- Immunefi scan: `immunefi/scan.py` + 12-program registry (`data/immunefi_registry.py`).
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

### Grading Tracks (v2.0.2)

Two explicit tracks — do not conflate them:

| Track | Module | Use |
|-------|--------|-----|
| **pipeline** (strict) | `validation/evidence_grading.py` `compute_evidence_grade()` | Full runs; CPCV required for Level 3+ |
| **shoestring** / **scan** | `shoestring_evidence_grade_*()` in same module | Zero-RPC fixture packs; Immunefi scan reports |

Export uses `effective_evidence_grade(finding, track=...)` — shoestring bounty runs pass `shoestring_mode: true` so Immunefi bulk export and shoestring pack share the shoestring track.

**Policy**: shoestring Level 4 on catalogue analogue = **draft / engine-validation**, not a claim of a new live-protocol bug.

### Reality Check Fields (v2.0.2)

Structured lab vs deployed signals on `Finding` / `AttackCandidateResult`:

| Field | Values | Meaning |
|-------|--------|---------|
| `reproduction_tier` | `simulation`, `solana_fixture`, `solana_validator`, `fork_reproduced` | How reproduction was achieved |
| `deployed_viable` | bool | True for validator clone or fork replay |
| `catalog_analogue` | bool | True when repro anchor ≠ live target (e.g. Kamino → Mango) |
| `submission_readiness` | `draft`, `shoestring`, `strict` | External reporting tier |

Computed in `validation/reality_check.py`; persisted in findings store and public dataset.

---

## Enabling LLM Expansion

### Hermes path (autonomous — preferred)

1. Hermes `night-shift` profile runs `delegate_task` subagents (Grok OAuth) per `hermes/skills/hypothesis-expansion/`.
2. Proposals written to `data/security_results/hermes_proposals/<run_id>.json`.
3. Pipeline ingests via `llm_expansion.provider: external` or CLI `--proposals PATH`.

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  run
```

Module: `domain/attack_hypotheses/external_proposals.py`. Proposals carry `generation_method: hermes_delegate`, `metadata.trusted=false`.

### LiteLLM path (manual / ad-hoc)

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

See `BOUNTY_RUN.md` §6–7. Pack slug uses `immunefi_program` (e.g. `bounty/shoestring/kamino/`).

---

## v2.0.2: Architecture Gap Closure (Shipped)

**Goal**: Align implementation with `adversarial_research_architecture.md` v2.1 and `METHODOLOGY.md` gaps identified 2026-06-09.

### Recon Slice (minimal)

- `sources/<target_id>/recon.json` — protocol invariants, threat model, state hints.
- `data/recon.py` — merges recon into live-target config at load time.
- Shipped: `sources/kamino/recon.json` (KLend/KVault/oracle invariants).

### Novel Vector Catalog

- `export/novel_vectors.py` — Stage 5f exports `knowledge/novel_vectors.jsonl` + `novel_vectors_top.json`.
- Includes rejected candidates; ranked by `novelty_score`, `priority_score`.

### Campaign Primitive

- Config: `"campaign": {"id": "...", "name": "..."}` on run configs (e.g. `kamino_shoestring.json`).
- `campaign_id` persisted in findings store; CLI: `knowledge --campaign <id>`.

### LLM Quality Eval

- `eval/llm_quality.py` — zero-cost mock Grok vs Ollama acceptance under `validate_hypothesis()`.
- CLI: `night-shift-security eval`; optional pipeline hook via `llm_quality_eval.enabled`.

### Solana Slice 3

- `mango-markets-2022` validator profile in `solana/validator_profiles.py` (slot 152M, Mango program clone).

---

## v2.0.3: Hermes Agent Integration (Shipped)

**Goal**: Outer-loop autonomy via Hermes `night-shift` profile; Grok OAuth for orchestration and `delegate_task` hypothesis expansion.

| Artifact | Purpose |
|----------|---------|
| `hermes/` | SOUL, skills, scripts, `install-profile.sh`, cron recipes |
| `external_proposals.py` | Load Hermes JSON → `AttackHypothesis` → `validate_hypothesis()` |
| `llm_expansion.provider: external` | Pipeline branch; parametric fallback unchanged |
| CLI `--proposals` | Override proposals path; enables external expansion |
| `~/.hermes/profiles/night-shift/` | Isolated HERMES_HOME (symlinked from repo) |

Trust boundary: Hermes orchestrates CLI; subagent proposals never bypass gates or scoring.

See `BOUNTY_RUN.md` §9 and `AGENTS.md` §Hermes Orchestration.

---

## Next Focus (Post v2.0.3)

1. **First real Immunefi submission** — validator replay on Solend/Cashio/Mango with grant-funded RPC.
2. **Deeper recon** — on-chain account layout ingestion beyond static `sources/` JSON.
3. **Cross-template compose** — multi-stage chained attacks (architecture L59).
4. **Live LLM eval** — extend `eval/llm_quality.py` with real Grok/Ollama providers when keys exist.
5. **Hermes cron activation** — register jobs from `hermes/cron/jobs.example.yaml` after gateway install.

See `BOUNTY_RUN.md` for exact commands.

---

## Previous Increments

- v2.0.3: Hermes `night-shift` profile, external proposals bridge, delegate expansion path.
- v2.0.2: Reality-check fields, grading tracks, recon slice, novel vector catalog, campaigns, LLM eval, Mango validator.
- v2.0.1: Shoestring submission export, Kamino target, Immunefi scan.
- v2.0: Zero-cost LLM configs, Immunefi submission packs, live-target harness, `BOUNTY_RUN.md`.
- v1.9: Early structural filters + lightweight findings store.
- v1.8: Hypothesis generation improvements + validation layer completion scope.
- v1.7: Validation Layer strengthening (multi-axis + evidence grading).
- v1.5: Real LLM provider integration.
- v1.4: Hypothesis Generation Layer + mapping + lineage.

---

*End of v2.0.3 update.*