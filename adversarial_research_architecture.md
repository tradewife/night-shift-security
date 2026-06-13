# Night Shift Security — Adversarial Research Architecture (v2.1)

**Status**: Revised baseline (2026-06-13, SPEC v2.0.10)  
**Purpose**: Define a rigorous, programmable adversarial research engine optimized for high-quality, bounty-grade security research.

---

## 1. Core Intent

Night Shift Security produces high-leverage public infrastructure for understanding protocol fragility. It must generate attack hypotheses at scale, explore them rigorously, validate them with statistical and empirical discipline, and only promote findings that carry clear evidence and reproducibility.

The system prioritizes:
- Depth and rigor over volume
- Novel attack vectors over obvious ones
- Strong provenance and auditability
- Outputs that are useful for builders and bounty programs

---

## 2. Key Inspirations

This version incorporates selected patterns from high-signal adversarial audit work (notably Percolator Heist) while preserving the original Night Shift philosophy.

**Integrated Elements**:
- Systematic, ranked hypothesis generation and prioritization
- Explicit focus on novel attack vectors (those that do not rely on obvious external conditions)
- Tight iterative research loop (Hypothesis → Test → Validate → Refine)
- Clear distinction between lab/simulation results and real deployment constraints
- Structured evidence grading and documentation habits

**Rejected Elements**:
- Unconstrained agentic exploration without strong gates
- Over-reliance on LLM judgment for validation or prioritization

---

## 3. Layered Architecture (v2.1)

| Layer | Name                        | Key Responsibilities & Refinements                                                                 | Influences                     |
|-------|-----------------------------|----------------------------------------------------------------------------------------------------|--------------------------------|
| 1     | Hypothesis Generation       | Ranked hypothesis generation, novel vector focus, compositional support, bounded LLM assistance   | Percolator Heist + internal   |
| 2     | Search & Optimization       | Parameterized sampling + Darwinian evolution with explicit lineage and prioritization             | Original Night Shift          |
| 3     | Simulation                  | Controlled execution environments (mock, foundry, Solana harness)                                 | —                            |
| 4     | Validation & Gates          | Multi-axis validation + Evidence Grading + lab vs. deployed reality checks                        | Clearwing + Percolator Heist  |
| 5     | Scoring & Promotion         | Evidence-grade-aware scoring with survival rates across axes and gates                            | Internal + Clearwing          |
| 6     | Orchestration & Knowledge   | Deterministic **Coordinator** (global attack-surface state, short-lived missions, debrief → prioritize) + campaign management + findings store with lineage | Percolator Heist + XBOW coordination patterns |

---

## 4. Hypothesis Generation Layer (v2.1)

**Core Principles**:
- Hypotheses should be generated and ranked systematically.
- Priority should be given to novel vectors (attacks that do not require obvious external shocks such as price crashes).
- The system should support both broad exploration and deep refinement of promising ideas.

**Key Capabilities**:
- Specialist generators per attack class
- `compose()` for multi-stage / chained attacks
- Bounded LLM assistance for hypothesis expansion (always gated)
- Explicit ranking and prioritization signals
- Strong metadata (provenance, generation method, novelty score, evidence potential)

**Process Influence**:
Hypothesis generation should follow a tight loop inspired by effective audit practice:
1. Recon & invariant mapping
2. Systematic hypothesis enumeration
3. Initial ranking (impact, novelty, testability)
4. Rapid validation feedback
5. Refinement or discard

---

## 5. Validation & Evidence Layer (v2.1)

This remains the core differentiator.

**Multi-Axis Validation**:
Every hypothesis is evaluated across:
- Likelihood under realistic conditions
- Economic/Governance Impact
- Stealth & Realism
- Generality across similar designs

**Evidence Grading** (refined):
- Level 1: Survives basic structural + Monte Carlo checks
- Level 2: Survives overfitting detection (CPCV/PBO)
- Level 3: Reproduces on historical or mainnet-fork state
- Level 4: Clear root cause + reproducible impact with artifacts

**Lab vs. Deployed Reality**:
The system must explicitly track whether a vector succeeds only under lab conditions or remains viable under actual deployed configuration and constraints. This distinction is critical for bounty-grade work.

---

## 6. Orchestration & Knowledge Layer (v2.1 + Coordinator)

Layer 6 separates **creative exploration** (bounded LLM / Hermes `delegate_task`) from **deterministic coordination**:

- **Coordinator** (`orchestration/coordinator.py`): owns global attack-surface coverage, emits one-template missions, runs post-mission debrief, and prioritizes the next mission from findings-store signals. No LLM in coordinator logic.
- **Bounty loop** (`orchestration/bounty_loop.py`): unified Immunefi + Cantina scan → target pick (saturation + cooldown) → full pipeline → `submit_now` gate; stops with human alert, never auto-posts externally.
- **Recursive self-improvement** (`orchestration/recursive_improvement.py`): deterministic store → state feedback (refinement seeds, cooldown extension, scan boost, plateau detection, improvement ledger). No LLM. Shared with Coordinator refinement logic.
- **Short-lived missions**: each mission scopes exactly one template; Hermes spawns delegate expansion for that mission only; mission retires after `coordinator cycle`.
- **Hermes outer loops**: `bounty-loop` (daily autonomous hunt) or `coordinator-cycle` (campaign-scoped). Trust boundary unchanged — proposals untrusted until `validate_hypothesis()`.
- **Findings store**: append-only JSONL lineage; coordinator reads store for coverage and refinement seeds; promotion still flows through evidence grading gates.

---

## 7. Knowledge & Documentation Layer

Night Shift Security should produce not just individual findings, but structured, reusable knowledge. This includes:
- Ranked hypotheses with test outcomes
- Novel attack vector catalogs
- Evidence-graded findings with clear lab/reality distinctions
- Lineage of how findings evolved

This supports both internal improvement and external outputs (bounty reports, public datasets, methodologies).

---

## 8. Research Loop (Adapted)

The recommended operational loop is:

**Recon → Generate & Rank Hypotheses → Rapid Validation → Reality Check → Document & Refine**

This loop should be fast in iteration but rigorous in validation gates.

---

## 9. Implementation Priorities

1. Strengthen Hypothesis Generation with ranking and novel vector focus
2. Complete Evidence Grading + multi-axis validation in the Validation Layer
3. Improve structured documentation and findings output quality
4. Build lightweight findings/knowledge store with lineage support

---

*This v2.1 document is the current architectural baseline.*