# Night Shift Security — Adversarial Research Architecture

**Big Picture Planning Document**  
**Status**: Draft for review (2026-06-08)  
**Owner**: Kate Cooper + research systems collaborator  
**Purpose**: Define the long-term engine architecture so subsequent SPEC.md updates and implementation can be tightly scoped and modular.

---

## 1. Vision

Night Shift Security is a **programmatic adversarial research engine** that compounds public-good knowledge about protocol fragility across EVM and Solana ecosystems.

It is not another autonomous pentest agent or black-box exploit generator. It is the rigorous counterpart: an engine capable of generating large volumes of attack hypotheses, exploring their parameter spaces at massive scale, subjecting every candidate to multi-gate statistical and reproduction validation, and only promoting findings that survive brutal, reproducible scrutiny with clear evidence.

**Success criteria**:
- Periodic research campaigns that expand a living, versioned knowledge base of breaking conditions and attack surfaces.
- High-confidence, scored outputs (playbooks, datasets, monitoring signals, bug-bounty packs) that outlive individual protocols.
- Clear dual relationship with the Night Shift Tokenomics track: Security maps where and how designs are fragile; Tokenomics quantifies resilience and value accrual.
- All outputs are auditable, reproducible, and directly useful to builders, auditors, grant programs, and security researchers.

This extends the original Night Shift philosophy (massive parallel exploration + Darwinian selection + "only survivors reach production") into the adversarial security domain.

## 2. Current Foundation (What We Build On)

The repository already contains strong, production-minded components:

- **Pipeline** (SPEC.md Stages 0–6b): ground-truth sanity → attack vector grid search (140 vectors across 7 templates) → Darwinian evolution → CPCV/PBO overfitting detection → Monte Carlo stress testing → EVM/Solana reproduction lanes → scoring with reproduction confidence bonuses → deduplication → export/monitoring/bounty packs.
- **7 attack templates** + seeded 19-exploit catalog with ground-truth anchors.
- **Strict validation signals**: `fork_reproduced` (EVM archive forks) and `solana_reproduced` (fixture mode + high-fidelity `solana-test-validator` replay at documented historical slots).
- **Solana harness** (Phase 5c-Slice 2 shipped): `validator_profiles.py`, `run_validator_replay.py`, `run_validator_test.sh`. Supports Solend whale (slot ~139,896,000) and Cashio (slot ~128,587,000) with strict evidence emission. Risks around historical clone state vs target slot are explicitly documented.
- **Simulation & optimization** layers already implement Monte Carlo and evolutionary search.
- **Extension points** exist via `attack_templates/` and catalog seeding in `data/`.

**Identified gap**: Hypothesis generation is currently static (grid search over fixed templates). There is no dedicated layer for rich, parameterized, composed, or novel attack hypothesis generation at scale. This is the primary modular addition required to realize the full vision.

## 3. Layered Architecture (Big Picture)

We organize the system into clear, swappable layers. The new work focuses on strengthening Layer 1 while preserving and evolving Layers 2–6.

| Layer | Name                        | Responsibility                                              | Current Maturity      | Priority (Now) |
|-------|-----------------------------|-------------------------------------------------------------|-----------------------|----------------|
| 1     | Hypothesis Generation       | Produce rich, parameterized, composable, and novel attack hypotheses | Static templates     | **High**       |
| 2     | Search & Optimization       | Explore parameter spaces at scale (grid + Darwinian evolution)     | Strong (Stages 1+3)  | Maintain + wire|
| 3     | Simulation                  | Execute candidates under controlled stochastic conditions          | Strong               | Maintain       |
| 4     | Validation & Gates          | Brutal multi-gate filtering (Monte Carlo, CPCV/PBO, reproduction)  | Strong + Solana      | Maintain + extend |
| 5     | Scoring & Promotion         | Severity, reproducibility, economic impact + confidence multipliers| Strong (repro bonuses)| Maintain     |
| 6     | Orchestration & Export      | Campaign running, result handling, playbook/dataset generation     | Partial (CLI+pipeline)| Future       |

**Guiding principle**: Creativity and breadth live in Layer 1. Brutality, statistical rigor, and auditability live in Layers 4–5. Most hypotheses must die.

## 4. Hypothesis Generation Layer (The New Modular Core)

This layer draws direct inspiration from patterns observed in the bug-bounty stars list while enforcing Night Shift discipline.

**Design goals**:
- Support **parameterized** attack spaces (continuous/discrete parameters, distributions, constraints).
- Support **composition** across templates for realistic multi-step attacks.
- Support **creative expansion** (LLM-assisted variant generation) with strict guardrails.
- Produce structured, serializable `AttackHypothesis` objects that flow cleanly into the existing pipeline.
- Remain swappable (pure parametric, evolutionary, or hybrid agentic generators).

**Explicit mapping from bug-bounty list patterns**:

- **Autonomous / multi-agent red teaming** (`pentagi`, `Decepticon`, `shannon`, `strix`, `pentest-ai` MCP server with 200+ tools + 17 specialist agents): Inspiration for a thin orchestrator that can dispatch specialist generators per attack class or attack phase (recon → hypothesis construction → parameter sampling). We keep the implementation thinner and more deterministic than the source projects.
- **Automatic exploit generation with LLMs** (`anamnesis`): Direct pattern for a bounded `llm_expansion.py` component that proposes parameterized variants from seed hypotheses or existing high-scoring survivors. All outputs are untrusted proposals and are immediately subjected to the existing brutal gates.
- **AI-driven vuln discovery + live validation** (`redai`): Reinforces the critical separation of concerns — generation can be creative/agentic; validation and evidence must remain strict, deterministic, and reproducible (`solana_reproduced`, `fork_reproduced`).
- **Deep automated analysis pipelines** (`DeepZero`): Future model for deeper static/dynamic analysis hooks inside specialized generators (e.g., for composability_risk or upgradeability_risk templates).
- **Recon / OSINT / payload orchestration** (various tools): Future extension points for protocol state gathering to inform realistic hypothesis parameterization (current governance params, liquidity distributions, etc.). Not included in first increment.

**Core abstractions** (to be defined precisely in the next SPEC update):
- `AttackHypothesis` — structured, versioned dataclass containing template type, parameter dictionary, metadata, provenance, and optional parent references (for evolution/composition).
- `HypothesisGenerator` — interface with methods `sample(n: int)`, `mutate(existing)`, `compose(h1, h2)`.
- `ParameterSpace` — declarative definition of ranges, distributions, constraints, and sampling strategies per template.
- `LLMExpansionOrchestrator` (shipped v1.5) — proposes variants using a swappable `LLMProvider` (LiteLLM-backed in production, mock in tests). Every proposal passes `validate_hypothesis()` before pipeline handoff; parametric fallback on failure. Never participates in validation or scoring decisions.

## 5. Integration with Existing Pipeline

Hypotheses produced by Layer 1 flow directly into:
- Stage 1 (attack vector grid search / expansion)
- Stage 3 (Darwinian evolution — mutation and selection now operate over a richer parameterized space)
- Future: Lightweight structural sanity checks can be added to Stage 0

The EVM and Solana reproduction lanes (including the Phase 5c validator harness) and the scoring bonuses for `fork_reproduced` / `solana_reproduced` remain unchanged. They become more powerful because they now validate a broader, searched candidate set rather than only the static catalog.

## 6. Risks, Assumptions & Scope Guardrails

**Key assumptions**:
- The existing CPCV/PBO overfitting detection and Monte Carlo stress gates are already aggressive enough to absorb significantly higher candidate volume. We will monitor and may tighten thresholds; we will not relax them.
- LLM components (if used) are strictly creative proposal engines. Validation, evidence emission (`SOLANA_VALIDATOR_PASS`, `SLOT_TARGET` matching, impact evidence), and final scoring remain fully deterministic and auditable.
- RPC rate limits on high-fidelity validator/fork paths will persist in the near term; the new layer enables the bulk of research to run in cheaper mock/fixture modes.

**Risks & mitigations**:
- Candidate volume explosion without gate strength → Mitigated by preserving aggressive existing gates and adding early lightweight structural filters in Layer 1.
- Over-engineering the generator layer before proving value → Mitigated by a thin, scoped first increment focused on two high-leverage templates + clear interfaces.
- Divergence from Tokenomics track → Mitigated by designing `AttackHypothesis` and scoring concepts to be potentially consumable or dual-use with Resilience Score generation in future shared components.

**Scope guardrails for first increments**:
- Prioritize depth on two high-leverage templates (`governance_capture` and `treasury_drain`) before adding breadth.
- Keep any LLM usage minimal, clearly bounded, and "proposal-only" in v1.
- Every new component must define clean handoff contracts into the existing pipeline stages.
- All new code and tests must run in fixture/mock mode (no new hard dependencies on live RPC).

## 7. Proposed First Modular Increment (Post-Architecture Approval)

1. Create `adversarial_research_architecture.md` at repo root (this document).
2. Add `src/night_shift_security/attack_hypotheses/` package skeleton:
   - `base.py` (core interfaces + `AttackHypothesis` model + `ParameterSpace`)
   - `parameter_spaces.py` (declarative definitions for `governance_capture` + `treasury_drain`)
   - One concrete generator implementation (e.g., `governance.py`)
   - Minimal integration test demonstrating hypotheses flowing into a mocked pipeline stage
3. Perform a scoped update to `SPEC.md` documenting the new layer, interfaces, integration points, and test strategy.
4. Optional: thin `llm_expansion.py` stub with strict "proposal-only" contract and no validation role.

This increment is intentionally small, reviewable, and unblocks richer research campaigns without modifying the Solana harness, existing validation logic, or scoring.

## 8. How This Informs the Next SPEC.md Update

The next SPEC.md update (to be scoped immediately after this architecture is reviewed) will focus narrowly on:
- Exact `AttackHypothesis` schema and serialization format
- `HypothesisGenerator` abstract base class and concrete interface
- `ParameterSpace` definition language + initial spaces for the two priority templates
- Precise wiring points into existing pipeline Stages 1 and 3
- Test strategy and evidence requirements for the new layer
- Any minimal changes needed to `data/` catalog seeding or CLI for discoverability

No changes to Stages 4–6, Solana/EVM harnesses, or core scoring logic are required in the first SPEC update.

---

*This document lives at repo root to serve as the stable big-picture reference while implementation proceeds modularly.*