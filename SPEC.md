# Night Shift Security — Technical Specification

**Version:** 1.7  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State (2026-06-08)

- Architecture baseline updated to **v2** (`adversarial_research_architecture.md`).
- Hypothesis Generation Layer (v1.4) merged.
- **LLM provider integration shipped** (v1.5): `llm_provider.py`, `LLMExpansionOrchestrator`, LiteLLM support, mandatory `validate_hypothesis()` gate, parametric fallback, observability logging.
- `AGENTS.md` added with solo developer workflow guidance.
- 121 tests passing (pre-validation layer).

---

## Enabling LLM Expansion

1. Install optional LLM dependency:
   ```bash
   pip install -e ".[llm]"
   ```
2. Set API key (example for OpenAI via LiteLLM):
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Enable in config (`config/default.json` or override):
   ```json
   {
     "llm_expansion": {
       "enabled": true,
       "provider": "litellm",
       "model": "gpt-4o-mini",
       "api_key_env": "OPENAI_API_KEY",
       "fallback": "parametric",
       "variants_per_seed": 2,
       "max_seeds": 5
     }
   }
   ```

**Safety invariants**: LLM output is untrusted (`metadata.trusted = false`). Every proposal passes `validate_hypothesis()` before pipeline entry. Failed calls fall back to parametric generation. LLM never participates in gate or scoring decisions.

---

## v1.7 Focus: Validation Layer Strengthening

**Status**: In progress (primary remaining work).

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

- v1.5: Real LLM provider integration behind `llm_expansion` hook.
- v1.4: Full Hypothesis Generation Layer + versioned mapping + lineage tracking.
- Architecture v2: Multi-axis validation and evidence grading concepts.

---

*End of v1.7 definition. Validation Layer strengthening in progress.*