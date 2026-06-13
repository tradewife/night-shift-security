# Night Shift Security — Technical Specification

**Version:** 3.0.0  
**Date:** 2026-06-13
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-13)

- Architecture baseline **v3.0** (`adversarial_research_architecture.md`).
- **Operator Layer Phase A shipped** (v3.0.0): task verifier, operator checkpoint, `bounty loop --trials`.
- Hypothesis Generation Layer **v1.4** (all 7 templates, versioned mapping, lineage).
- **LLM provider integration shipped** (v1.5): `llm_provider.py`, `LLMExpansionOrchestrator`, LiteLLM optional dep, mandatory `validate_hypothesis()` gate, parametric fallback, `metadata.trusted=false`.
- **Validation Layer shipped** (v1.7): multi-axis scores, evidence grading (Levels 0–4), scoring integration.
- **Early structural filters + findings store shipped** (v1.9).
- **Immunefi-ready bounty path shipped** (v2.0): zero-cost LLM configs, Immunefi submission packs, live-target harness.
- **Shoestring + Kamino target shipped** (v2.0.1): zero-RPC packs, Immunefi scan CLI, `targets/kamino.json`.
- **Architecture gap closure shipped** (v2.0.2): reality-check fields, dual grading tracks, recon slice, novel vector catalog, campaigns, LLM eval harness, Mango validator profile.
- **Hermes integration shipped** (v2.0.3): `night-shift` profile bundle, external proposals bridge, `delegate_task` expansion path, cron recipes.
- **Coordinator shipped** (v2.0.4): deterministic Layer 6 mission lifecycle, global attack-surface state, debrief → prioritize loop.
- **QuickNode x402 RPC bridge shipped** (v2.0.5): `solana/x402-proxy/` local JSON-RPC sidecar for wallet-auth mainnet RPC (1M free credits/mo).
- **Day Shift ops + Mango validator shipped** (v2.0.6): session plans (`day_shift/`), intel watchlist, strict replay for all three validator anchors.
- **Bounty scoring + Cantina screen shipped** (v2.0.7): `compute_bounty_score`, `bounty_candidates.jsonl`, unified `scan --platform all` (Immunefi + Cantina), `bounty score` / `knowledge --bounty-ready` CLI.
- **Novel-surface campaigns shipped** (v2.0.8): `kamino_klend.json` (no catalogue anchor), `wormhole_shoestring.json`, fixed `access_control_escalation` scan proposals; coordinator cycles through Wormhole + KLend with zero `deployed_viable`.
- **Autonomous bounty loop shipped** (v2.0.9): `bounty loop` CLI, `program_registry`, `orchestration/bounty_loop.py`, loop state + `submission_alert.json` human gate, Hermes `bounty-loop` skill + `nss-bounty-loop.sh` cron.
- **Deterministic RSI shipped** (v2.0.10): `recursive_improvement.py`, `improve` CLI, improvement ledger, refinement hints, shared refinement seeds with Coordinator.
- `BOUNTY_RUN.md` + `SUSTAINABILITY.md` — zero-budget bounty workflows and self-sustaining allocation model (split TBD).
- **241 tests** passing (5 skipped without live validator).

---

## v3.0: Operator Layer (Phase A Shipped)

**Goal**: Closed-loop operator scaffolding atop v2 gates — balance-delta ground truth, context persistence, N-trial scaling. Phases B–D (triage, MCP, impact) specified; not yet implemented.

**Trust boundary unchanged**: Hermes orchestrates CLI/MCP only; `validate_hypothesis()` + evidence grading remain authoritative; `submission_alert.json` human gate.

### Phase A — Ground truth + persistence (Shipped)

| Artifact | Purpose |
|----------|---------|
| `validation/task_verifier.py` | Parse forge output for `DELTA_WEI` / balance logs; catalogue anchors exempt |
| `orchestration/operator_checkpoint.py` | `operator/checkpoint.json` schema for context rollover |
| `bounty loop --trials N` | N independent attempts on same target before queue advance |
| `config/operator.json` | Reference overlay for fork-enabled operator runs |

**Task verifier gate** (novel findings only when `required_for_novel: true`):

- Fork phase attaches `balance_verified`, `balance_delta_wei` to `fork_evidence`
- Evidence grade capped at 2 without passing verifier on non–`catalog_analogue` candidates
- `qualifies_for_submission()` requires `finding_balance_verified()`

**Config** (`operator` in `default.json`):

```json
"operator": {
  "task_verifier": {
    "enabled": true,
    "threshold_wei": "100000000000000000",
    "required_for_novel": true
  },
  "checkpoint": { "path": "data/security_results/operator/checkpoint.json" },
  "trials": { "default_n": 1, "high_priority_n": 30 }
}
```

**CLI**:

```bash
.venv/bin/python -m night_shift_security.cli.main bounty loop --trials 30 --iterations 1
.venv/bin/python -m night_shift_security.cli.main operator checkpoint write \
  --target-slug kamino --hypothesis "..." --reason rollover
```

Hermes skill: `operator-checkpoint`.

### Phase B — Discovery alpha (Planned)

- `triage/file_ranker.py` — per-file score 1–5; analyze ≥4 only
- `triage/git_patches.py` — security-patch shape miner
- `invariants/pbt.py` — Hypothesis counterexamples from recon invariants
- KLend validator harness + Solana lamport verifier

### Phase C — Execution scaffolding (Planned)

- `mcp/foundry-server/` — `forge_test`, `cast_call`, `anvil_fork`
- `docker/anvil-sandbox/` — pinned block, funded attacker
- `mcp/slither-server/` — logic-bug detectors on ranked files

### Phase D — Impact + scale (Planned)

- `impact/oracle_arbitrage.py` — internal vs DEX price on fork
- `impact/tvs_maximization.py` — sibling pool / clone sweep post-PoC
- Hermes personas: `operator-recon`, `operator-exploit`, `operator-triage`

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

## v2.0.4: Deterministic Coordinator (Shipped)

**Goal**: Close Layer 6 orchestration gap — global attack-surface state, short-lived one-template missions, deterministic debrief and next-mission prioritization. Reuses existing pipeline, findings store, and evidence grading without gate changes.

| Artifact | Purpose |
|----------|---------|
| `orchestration/coordinator.py` | `Mission`, `CoordinatorState`, `AttackSurfaceCoverage`, `MissionDebrief`; `init_state`, `plan_missions`, `debrief_mission`, `run_mission_cycle` |
| `data/security_results/knowledge/coordinator_state.json` | Persistent coordinator state |
| `data/security_results/knowledge/debriefs/<mission_id>.json` | Machine-readable post-run debrief |
| CLI `coordinator` | `init`, `status`, `plan`, `cycle` subcommands |
| `hermes/skills/coordinator-cycle/` | Hermes workflow: plan → scoped expansion → cycle → lab notebook |

### Prioritization (deterministic)

Missions ranked by: uncovered `(target, template)` from recon → refinement seeds (grade 1–2, survival ≥ 0.4) → novelty gap → deprioritize plateaued catalogue analogues (grade ≥ 4).

### Trust boundary

Coordinator logic is **deterministic only**. Hermes `delegate_task` proposals remain `metadata.trusted=false`. No bypass of `validate_hypothesis()`, evidence grading, or CPCV gates.

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  coordinator init

.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  coordinator plan --top 1

.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  coordinator cycle
```

---

## v2.0.5: QuickNode x402 RPC Bridge (Shipped)

**Goal:** Unblock `SOLANA_USE_VALIDATOR=1` strict reproduction without API-key RPC accounts.

- `solana/x402-proxy/` — Node sidecar (`@quicknode/x402`) exposing `http://127.0.0.1:18989` → `x402.quicknode.com/solana-mainnet`
- Default: Solana devnet USDC payment + mainnet RPC query; `credit-drawdown` for validator clone bursts
- Documented in `solana/README.md`, `BOUNTY_RUN.md` §8, Hermes `night-shift-run` Gotcha
- **Human gate:** Hermes SOUL requires chat approval before autonomous wallet RPC usage

## v2.0.6: Day Shift + Mango Validator (Shipped)

- Day Shift operating model: [`hermes/DAY_SOUL.md`](hermes/DAY_SOUL.md), skill `day-shift-cycle`, `data/security_results/day_shift/`, `intel/watchlist.yaml`
- Mango Slice 3: correct program `4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg`; `validator_backed=True` in `solana_targets.py`
- Strict validator replay green: Solend, Cashio, Mango via x402 proxy

## v2.0.10: Deterministic Recursive Self-Improvement (Shipped)

- `orchestration/recursive_improvement.py` — store signals → loop state (cooldown, refinement queue, scan boost, plateaus)
- `improve` CLI; `improvement_ledger.jsonl`; `loop/refinement_hints.json`
- Wired into bounty loop end-of-tick; Coordinator shares `refinement_seeds_from_store()`
- Hermes skills `recursive-improvement`, `bounty-loop`; cron: bounty-loop primary, investigate-queue weekly Kamino depth
- Live cron IDs: `nss-bounty-loop` fbe84e39c1b1, `nss-investigate-queue` d5f0875fe76c

## v2.0.9: Autonomous Bounty Loop (Shipped)

- `bounty loop` CLI: unified Immunefi + Cantina scan → pick target → pipeline → `submit_now` gate
- `orchestration/bounty_loop.py` + `data/program_registry.py`; state at `data/security_results/loop/state.json`
- Human gate: `submission_alert.json` on qualify — no external post without operator
- Hermes: skill `bounty-loop`, script `nss-bounty-loop.sh`, cron `nss-bounty-loop`

## Next Focus (Post v3.0.0 Phase A)

1. **Phase B triage** — file ranker + git patch miner for KLend/Wormhole (Day Shift blocks A–B).
2. **Novel surface hits** — `nss-bounty-loop` + optional `--trials 30` on high-priority slugs.
3. **Phase C MCP** — Foundry/Slither MCP + Docker Anvil sandbox.
4. **Cross-template compose** — multi-stage chained attacks (architecture L59).

See `BOUNTY_RUN.md` for exact commands.

---

## Previous Increments

- v3.0.0: Operator Layer Phase A — task verifier, checkpoint, `--trials`.
- v2.0.10: Deterministic RSI, `improve` CLI, improvement ledger, shared refinement seeds.
- v2.0.9: Autonomous bounty loop CLI, program_registry, Hermes `nss-bounty-loop` cron.
- v2.0.8: Novel-surface campaigns (KLend, Wormhole), coordinator cycles.
- v2.0.7: Bounty scoring, Cantina screen, unified `scan --platform all`.
- v2.0.6: Day Shift session ops, Mango validator Slice 3, three-anchor strict replay.
- v2.0.5: QuickNode x402 local RPC proxy for Solana validator replay.
- v2.0.4: Deterministic Coordinator, mission lifecycle, debrief JSON, `coordinator` CLI.
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

*End of v3.0.0 update.*