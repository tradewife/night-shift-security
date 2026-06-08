# Night Shift Security — Technical Specification

**Version:** 1.7  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-08)

- Architecture baseline updated to **v2** (`adversarial_research_architecture.md`).
- Hypothesis Generation Layer (v1.4) + LLM expansion scaffolding merged.
- Real LLM provider integration largely implemented (swappable `llm_provider.py`, `llm_expansion.py` with LiteLLM support, mandatory `validate_hypothesis()` gate, parametric fallback, and tests).
- 121 tests passing.
- `AGENTS.md` added with solo developer workflow guidance.

---

## v1.7 Focus: Validation Layer Strengthening

**Status**: Primary remaining work from the v1.6 scope.

The LLM provider integration is substantially complete. The main remaining piece is strengthening the Validation Layer as defined in the v2 architecture.

### Scope

- Implement **Multi-Axis Validation** across four axes:
  - Likelihood
  - Impact
  - Stealth / Realism
  - Generality
- Introduce **Evidence Grading** (Levels 1–4) with clear promotion criteria.
- Update `AttackHypothesis` and findings structures to carry axis scores and evidence grade.
- Adjust scoring logic to incorporate evidence grade and multi-axis survival rates.
- Add corresponding tests.
- Ensure the new validation capabilities are usable by both parametric and LLM-generated hypotheses.

### Constraints
- Do not weaken existing gates (Monte Carlo, CPCV/PBO, reproduction lanes).
- Keep changes backward compatible.
- LLM proposals must continue to pass early validation before expensive stages.

### Success Criteria
- Multi-axis scores and evidence grades are computed and persisted.
- Scoring reflects evidence grade + axis performance.
- 125+ tests passing.
- Changes align with architecture v2.
- `SPEC.md` updated to v1.8 upon completion.

### Out of Scope
- Full findings store / knowledge graph.
- Compositional generation improvements.
- Advanced LLM agent loops.

---

## Previous Increments Reference

- v1.4: Full Hypothesis Generation Layer + versioned mapping + lineage tracking.
- LLM provider integration (mostly complete as of this version).
- Architecture v2: Introduced multi-axis validation and evidence grading concepts.

---

*End of v1.7 definition. Focus on Validation Layer strengthening.*