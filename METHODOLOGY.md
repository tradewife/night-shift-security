# Night Shift Security — Research & Audit Methodology

**Status**: Initial version (2026-06-08)  
**Purpose**: Define the operational research and audit process used in Night Shift Security. This document captures effective patterns from high-signal adversarial work and integrates them with the Night Shift research philosophy.

---

## Core Philosophy

Night Shift Security follows a disciplined, hypothesis-driven approach to adversarial research. The goal is to generate high-quality attack hypotheses, validate them rigorously, and produce findings that are reproducible and useful for both internal improvement and external bounty work.

Key principles:
- Move fast in iteration, but slow and rigorous in validation.
- Prioritize novel attack vectors over obvious ones.
- Maintain strong provenance and evidence grading.
- Distinguish clearly between lab/simulation results and real deployment constraints.
- Produce structured, auditable outputs.

---

## Recommended Research Loop

The core operational loop is:

**Recon → Generate & Rank Hypotheses → Rapid Validation → Reality Check → Document & Refine**

This loop should be executed iteratively. Promising hypotheses are refined through multiple cycles. Weak hypotheses are discarded early.

### Phase Breakdown

| Phase | Activities | Key Outputs | Notes |
|-------|------------|-------------|-------|
| **Recon** | Map protocol invariants, on-chain state, and design assumptions | Protocol model, state inspection tools, initial threat model | Use existing sources/ and decoding tools where possible |
| **Generate & Rank Hypotheses** | Systematically produce attack ideas and prioritize them | Ranked hypothesis list (with novelty, impact, and testability signals) | Use `attack_hypotheses/` + ranking metadata |
| **Rapid Validation** | Test hypotheses in controlled simulation environments | Test results, Monte Carlo outcomes, multi-axis scores | Leverage Simulation + Validation layers |
| **Reality Check** | Validate against actual deployed configuration and constraints | Lab vs. Deployed distinction, evidence grade | Critical for bounty-grade work |
| **Document & Refine** | Record findings with evidence and lineage; coordinator debrief → prioritize next mission | Structured findings, novel vector catalogs, debrief JSON, updated mission queue | Follow clear documentation standards; use `coordinator status` for machine-readable handoff |

---

## Hypothesis Generation

- Hypotheses should be generated systematically rather than purely ad-hoc.
- Explicit priority should be given to **novel vectors** (attacks that do not require obvious external conditions such as major price moves or governance attacks under normal participation).
- Use ranking signals: potential impact, novelty, testability, and alignment with current research focus.
- Support compositional attacks through `compose()` operations.
- LLM assistance is allowed but must remain bounded and always pass early validation gates.

---

## Validation & Evidence

Validation is multi-layered and evidence-aware:

**Multi-Axis Evaluation**:
- Likelihood under realistic conditions
- Economic or governance Impact
- Stealth and operational Realism
- Generality across similar protocol designs

**Evidence Grading**:
- Level 1: Basic survival of structural and Monte Carlo checks
- Level 2: Survival of overfitting detection (CPCV/PBO)
- Level 3: Successful reproduction on historical or mainnet-fork state
- Level 4: Clear root cause analysis with reproducible artifacts

Only Level 3+ findings should be considered high-confidence for external reporting.

**Lab vs. Reality**:
Always explicitly record whether a vector succeeds only in idealized conditions or remains viable under actual deployed parameters and constraints.

---

## Documentation Standards

High-quality documentation is part of the research process, not an afterthought. Recommended artifacts include:

- Ranked hypothesis lists with test status
- Novel attack vector catalogs
- Evidence-graded findings with clear lab/reality distinctions
- Lineage tracking for how findings evolved

These outputs support both internal iteration and external bounty submissions.

---

## Integration with Architecture

This methodology is designed to work with the Night Shift Security architecture (v2.1). In particular:
- Layer 1 (Hypothesis Generation) handles ranked and novel-focused hypothesis creation.
- Layer 4 (Validation & Gates) implements multi-axis evaluation and evidence grading.
- Layer 6 (Orchestration & Knowledge) supports the deterministic Coordinator, structured findings, and lineage tracking.

---

## Continuous Improvement

This document should evolve as we learn from real audit and research campaigns. Significant learnings should be reflected back into both this document and the architecture baseline.

---

*This is the current working methodology for Night Shift Security research and audit work.*