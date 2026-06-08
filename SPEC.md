# Night Shift Security — Technical Specification

**Version:** 1.5  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Define the Hypothesis Generation Layer and its evolution.

---

## Current State (as of 2026-06-08)

**v1.4 merged into main**:
- Full Hypothesis Generation Layer implemented for all 7 templates.
- Versioned mapping layer (`mapping.py` with `MAPPING_VERSION = "1.0"` and explicit registry).
- `AttackHypothesis` with provenance (`parent_ids`, lineage).
- Pipeline integration in Stages 0, 1, and 3.
- `AttackVector.metadata` carries hypothesis lineage.
- Config flags: `hypothesis_generation` and `llm_expansion` (default off).
- 113 tests passing.

---

## Next Task: Real LLM Provider Integration (v1.5)

**Status**: Ready to start.  
**Owner**: Coding agent  
**Goal**: Replace the current parametric fallback with a real LLM provider behind the `llm_expansion` hook, while preserving all safety guarantees.

### Scope

- Implement support for at least one production LLM provider (LiteLLM, OpenAI, Anthropic, or Grok API recommended for simplicity).
- Wire the provider behind `llm_expansion.enabled: true` in config.
- Keep the existing parametric generation as the reliable fallback when the LLM call fails or `enabled: false`.
- **Mandatory safety gate**: Every LLM-proposed hypothesis **must** pass `validate_hypothesis()` before it is accepted into the pipeline.
- Add basic observability (simple logging of calls, success/failure, and rough token/cost estimates).
- Update tests in `tests/test_attack_hypotheses.py` (LLM path can be mocked for CI).
- Update relevant sections of this SPEC.md and add a short note in `adversarial_research_architecture.md` if the integration has architectural implications.
- Document how to enable the feature (env vars + config) so it is usable by others.

### Constraints

- Do **not** remove or weaken the existing parametric fallback.
- LLM proposals must remain untrusted for validation and scoring decisions.
- No changes to Stages 4–6 or the reproduction harnesses.
- Keep the implementation swappable (easy to add more providers later).

### Success Criteria

- Setting `llm_expansion.enabled: true` causes the system to attempt real LLM calls for hypothesis expansion.
- Failed LLM calls gracefully fall back to parametric generation without crashing the pipeline.
- All LLM-generated hypotheses pass structural validation before entering expensive simulation/evaluation stages.
- 120+ tests still passing.
- Feature is documented and toggleable via config.

### Out of Scope (for this increment)
- Advanced prompt engineering or multi-step agentic workflows.
- Cost tracking dashboards or production observability.
- Using LLM for anything other than hypothesis *proposal*.

---

## Previous Versions (for reference)

**v1.4** (merged): Full Hypothesis Generation Layer + versioned mapping + lineage tracking.
**v1.3 / v1.2**: Initial `attack_hypotheses/` package and pipeline wiring.

---

*End of current task definition. The agent should implement the LLM provider integration described above.*