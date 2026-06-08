# Night Shift Security — Adversarial Research Architecture (v2)

**Status**: Revised baseline (2026-06-08)  
**Purpose**: Define a rigorous, programmable adversarial research engine that systematically explores attack surfaces while maintaining statistical discipline, provenance, and reproducibility.

---

## 1. Core Intent

Night Shift Security exists to create high-leverage public infrastructure for understanding protocol fragility. It must:

- Generate large volumes of attack hypotheses.
- Explore them through parameterized and evolutionary search.
- Subject every candidate to brutal, multi-layered validation.
- Only promote findings that are reproducible and carry clear evidence of impact.
- Maintain strong provenance, lineage, and auditability.

This is the original Night Shift research philosophy re-domained to adversarial security.

---

## 2. Key Inspirations & Selective Integration

We reviewed advanced open-source autonomous security projects (Clearwing, anamnesis-release, pentest-ai, and related agentic systems). Only elements that strengthen our core principles were integrated.

### Integrated Elements

**From Clearwing** (strongest influence):
- Evidence grading and confidence tiers.
- Multi-axis validation thinking (adapted to Likelihood, Impact, Stealth, Generality).
- Structured parallel exploration with shared state and deduplication.
- Emphasis on sandboxing, reproducibility, and human oversight for high-stakes paths.

**From anamnesis-release**:
- Iterative primitive building and feedback loops for complex attack chains.
- Compositional hypothesis generation (`compose()`).

**From pentest-ai** (and similar specialist systems):
- Specialist generators per attack class.
- Findings correlation and attack chaining support.
- Strong human-in-the-loop and scoping patterns (adapted for research campaigns).

### Explicitly Rejected
- Unconstrained ReAct/agentic loops as the primary mechanism.
- LLM judgment for validation or scoring.
- Overly general tool-calling without strong parameterization and lineage.

---

## 3. Revised Layered Architecture

| Layer | Name                        | Key Refinements                                      | Primary Influences          |
|-------|-----------------------------|------------------------------------------------------|-----------------------------|
| 1     | Hypothesis Generation       | Specialist generators + bounded LLM expansion + compositional (`compose()`) support | anamnesis + pentest-ai     |
| 2     | Search & Optimization       | Parameterized sampling + Darwinian evolution with explicit lineage | Original Night Shift       |
| 3     | Simulation                  | Unchanged (mock + foundry + Solana harness)         | —                         |
| 4     | Validation & Gates          | Multi-axis validation + evidence grading + stronger reproduction tiers | Clearwing                  |
| 5     | Scoring & Promotion         | Evidence grade + survival rate across gates         | Clearwing + internal       |
| 6     | Orchestration & Knowledge   | Campaign orchestration + lineage-aware findings store | Clearwing + pentest-ai     |

**Guiding Principle**: Creativity lives in Layer 1. Brutality, statistical rigor, and auditability live in Layers 4–5.

---

## 4. Hypothesis Generation Layer (Refined)

**Core Abstractions**:
- `AttackHypothesis` with rich metadata (`mapping_version`, `parent_ids`, `generation_method`, `evidence_grade`).
- `ParameterSpace` (declarative and versioned).
- `HypothesisGenerator` interface (`sample()`, `mutate()`, `compose()`).
- Specialist generators per template class.

**Strengthened Capabilities**:
- **Compositional Generation**: `compose(h1, h2)` is first-class for building multi-stage attacks.
- **LLM Expansion**: Remains strictly proposal-only. Every proposal must pass `validate_hypothesis()` before pipeline entry. Future bounded iterative refinement is allowed under gate control.
- **Evidence-Aware Generation**: Generators can bias toward hypotheses likely to reach higher evidence grades.

---

## 5. Validation Layer (Strengthened)

This is our primary differentiator.

**Multi-Axis Validation** (adapted from Clearwing-style thinking):

Each hypothesis is evaluated across four axes:
1. **Likelihood** — Probability of success under realistic conditions (Monte Carlo + regime variation).
2. **Impact** — Economic or governance damage.
3. **Stealth / Realism** — Detectability and operational plausibility.
4. **Generality** — How broadly the breaking condition applies.

**Evidence Grading**:

Findings receive increasing evidence grades:
- Level 1: Survives Monte Carlo + structural checks
- Level 2: Survives CPCV/PBO overfitting detection
- Level 3: Achieves reproduction (`fork_reproduced` / `solana_reproduced`)
- Level 4: Clear root cause + reproducible impact artifacts

Only Level 3+ findings receive high-visibility promotion.

---

## 6. Knowledge & Orchestration Layer

Introduce a lightweight but structured **findings store** that captures:
- Full hypothesis lineage (`parent_ids`)
- Validation results across all axes and gates
- Evidence grade
- Correlated attack chains

This enables future capabilities such as lineage survival analytics and campaign-level insights.

---

## 7. Differentiation

| Dimension              | Typical Autonomous Agent Projects | Night Shift Security (v2)                  |
|------------------------|-----------------------------------|--------------------------------------------|
| Primary Mechanism      | Unconstrained agent loops         | Parameterized + evolutionary search under statistical gates |
| Validation             | LLM judgment or basic execution   | Multi-axis + evidence-graded + reproduction-based |
| Provenance             | Usually weak                      | First-class (lineage, mapping version, generation method) |
| Reproducibility        | Variable                          | Strong (Monte Carlo, CPCV/PBO, historical reproduction) |
| Output                 | Findings / exploits               | Scored, evidence-graded datasets + methodologies + playbooks |

---

## 8. Implementation Priorities (Next Increments)

1. ~~**Validation Layer strengthening** (multi-axis evaluation + evidence grading)~~ — **shipped v1.7**.
2. ~~**Real LLM provider integration** behind `llm_expansion`~~ — **shipped v1.5**.
3. **Findings store** with lineage support.
4. **Compositional and bounded iterative refinement** in Hypothesis Generation.

---

*This document is now the baseline architecture for Night Shift Security.*