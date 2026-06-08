# Night Shift Security — Technical Specification

**Version:** 1.6  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State

- v1.4 (Hypothesis Generation Layer) merged.
- Architecture baseline updated to v2 (`adversarial_research_architecture.md`).
- 113 tests passing.

---

## Next Increment: Validation Layer Strengthening + Real LLM Provider (v1.6)

**Status**: Ready to start  
**Goal**: Deliver two tightly coordinated improvements:
1. Strengthen the Validation Layer with multi-axis evaluation and evidence grading.
2. Integrate a real LLM provider behind the `llm_expansion` hook with all existing safety guardrails.

### Why These Two Together

These changes are synergistic. The strengthened validation layer provides better guardrails for LLM-generated hypotheses, while the real LLM provider gives us richer candidates to validate. Doing them together produces a more coherent increment than splitting them.

### Scope

#### Part A: Validation Layer Strengthening

- Define and implement **Multi-Axis Validation** across four axes:
  - Likelihood (Monte Carlo + regime variation)
  - Impact (economic/governance damage)
  - Stealth / Realism
  - Generality
- Introduce **Evidence Grading** (Levels 1–4) with clear criteria for promotion:
  - Level 1: Basic structural + Monte Carlo survival
  - Level 2: Passes CPCV/PBO
  - Level 3: Achieves reproduction (`fork_reproduced` or `solana_reproduced`)
  - Level 4: Clear root cause + reproducible artifacts
- Update scoring to incorporate evidence grade + axis survival rates.
- Update `AttackHypothesis` and findings structures to carry evidence grade and axis scores.
- Add corresponding tests and update existing pipeline stages that consume validation results.

#### Part B: Real LLM Provider Integration

- Implement support for at least one production LLM provider (LiteLLM recommended for flexibility).
- Wire it behind `llm_expansion.enabled: true`.
- Preserve parametric fallback when LLM calls fail or the flag is disabled.
- **Mandatory**: Every LLM-proposed hypothesis must pass `validate_hypothesis()` (structural + lightweight semantic) before entering the main pipeline.
- Add basic observability (call logging, success/failure, rough cost/token estimates).
- Ensure the implementation remains swappable for additional providers.
- Update tests (mocked LLM path acceptable for CI).
- Document configuration and environment variables required to enable the feature.

### Constraints

- Do not weaken or bypass existing gates (Monte Carlo, CPCV/PBO, reproduction).
- LLM output remains untrusted for validation and scoring decisions.
- No changes to Stages 4–6 or the Solana/EVM reproduction harnesses.
- Backward compatibility with `hypothesis_generation.enabled: false` (pure grid mode) must be preserved.

### Success Criteria

- Multi-axis scores and evidence grades are computed and stored for hypotheses.
- `llm_expansion.enabled: true` successfully calls a real LLM provider and produces valid hypotheses.
- Failed LLM calls gracefully fall back to parametric generation.
- All LLM-generated hypotheses pass early validation before expensive simulation.
- 125+ tests passing.
- Both features are documented and configurable.

### Out of Scope

- Advanced prompt engineering or multi-turn agentic loops (keep bounded for v1.6).
- Full findings store / knowledge graph (deferred to later increment).
- Compositional generation improvements (deferred).
- Production-grade cost tracking or observability dashboards.

### Implementation Notes

- The Validation Layer changes should be designed so they can be used immediately by the new LLM path.
- Consider making evidence grading and multi-axis scoring available as a reusable component.
- Update `adversarial_research_architecture.md` (already at v2) only if major structural changes are required.

---

## Previous Work Reference

- v1.4: Full Hypothesis Generation Layer + versioned mapping + lineage.
- Architecture v2: Multi-axis validation, evidence grading, and refined layers.

---

*End of v1.6 task definition. Implement Validation Layer strengthening + real LLM provider integration as described.*