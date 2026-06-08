# Night Shift Security — Technical Specification

**Version:** 1.8  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)

---

## Current State

- Architecture baseline is at **v2.1** (incorporates ranked hypothesis generation, novel vector focus, tighter research loop, and refined evidence grading from effective audit patterns).
- LLM provider integration is substantially complete.
- Validation Layer strengthening (multi-axis + evidence grading) is the active focus.
- 121+ tests passing.

---

## v1.8 Focus: Hypothesis Generation Improvements + Validation Layer Completion

**Goal**: Strengthen the front end of the research pipeline (Hypothesis Generation) while completing the Validation Layer work started in v1.7. This increment brings the system closer to producing high-quality, bounty-grade outputs.

### Part A: Hypothesis Generation Layer Improvements

- Add support for **ranked and prioritized hypothesis generation**.
- Introduce explicit focus on **novel attack vectors** (those that do not rely on obvious external conditions such as price crashes).
- Improve metadata on `AttackHypothesis` to include novelty signals and evidence potential.
- Support tighter iterative refinement loops (Hypothesis → Test → Validate → Refine).
- Maintain bounded LLM assistance with strong validation gates.

### Part B: Validation Layer Completion

- Implement full **Multi-Axis Validation** (Likelihood, Impact, Stealth, Generality).
- Complete **Evidence Grading** system (Levels 1–4) with clear criteria.
- Add explicit tracking of **lab vs. deployed reality** results.
- Update scoring to reflect evidence grade and multi-axis performance.
- Ensure the new validation capabilities work for both parametric and LLM-generated hypotheses.

### Success Criteria

- Hypothesis generation produces ranked outputs with novelty signals.
- Multi-axis scores and evidence grades are computed and used in promotion decisions.
- Clear distinction between lab success and real deployment viability.
- 130+ tests passing.
- Work aligns with architecture v2.1.
- `SPEC.md` updated to v1.9 upon completion.

### Constraints
- All existing gates (Monte Carlo, CPCV/PBO, reproduction) remain mandatory.
- LLM proposals must continue to pass early validation.
- No weakening of reproducibility or provenance requirements.

### Out of Scope
- Full findings/knowledge store (deferred).
- Major changes to orchestration or export layers.

---

*This increment focuses on improving the quality and discipline of the research loop while completing core validation improvements.*