# Night Shift Security — Research & Audit Methodology

**Status:** v2.0 (2026-06-14) — aligned with architecture v3.1 / SPEC v3.1.1  
**Purpose:** Operational research and audit process for Night Shift Security.

---

## Core philosophy

Disciplined, hypothesis-driven adversarial research:

- Move fast in iteration; slow and rigorous in validation.
- Prioritize **novel** vectors over catalogue replay.
- Maintain provenance and evidence grading.
- Distinguish lab/simulation from deployed constraints.
- Produce structured, auditable outputs.

---

## Research loop

**Recon → Generate & Rank → Rapid Validation → Task Verify → Reality Check → Document & Refine**

Executed iteratively. Weak hypotheses discarded early; promising ones refined through bounty loop RSI and Coordinator debrief.

### Phase breakdown

| Phase | Activities | Outputs |
|-------|------------|---------|
| **Recon** | Map invariants, on-chain state, design assumptions | `sources/*/recon.json`, triage scores |
| **Generate & Rank** | Systematic attack ideas, novelty/impact/testability | Ranked hypotheses, proposals sidecar |
| **Rapid Validation** | Simulation, MC, Darwinian, fork/validator replay | Multi-axis scores, CPCV/PBO |
| **Task Verify** | Balance delta ground truth (`DELTA_WEI`, `MEASURED_DELTA_LAMPORTS`) | Verifier pass/fail on novel |
| **Reality Check** | Deployed viability, catalogue analogue flag | `deployed_viable`, evidence grade |
| **Document & Refine** | Lab notebook, RSI, Coordinator, HIPIF fold | Notebook entry, improvement ledger |

---

## Day Shift vs Night Shift methodology

| Shift | Method |
|-------|--------|
| **Day Shift** | Planned session arcs in `day_shift/current.md`; infra, tests, triage, intel; handoff to Night Shift |
| **Night Shift** | HIPIF bounty-depth chain; autonomous scan → depth → hunt → RSI → refine → gate |

Day Shift does not duplicate assays Night Shift already completed — check lab notebook **same vs different** before re-planning.

---

## HIPIF operational methodology (v3.1)

The night chain compresses context via folding (`hipif fold`) after each subgoal:

1. **Scan** — unified Immunefi + Cantina (`min-bounty` filter)
2. **Depth passes** — Wormhole (12 trials), bridge refinement, KLend live (5 trials)
3. **Cantina slates** — pendle, morpho, euler with fork depth
4. **Fork-ready hunt** — wormhole, morpho, euler, ethena (not catalogue smokes)
5. **RSI** — `improve` CLI aggregates store signals
6. **Refine** — top refinement queue entries with proposals or depth pin
7. **Coordinator** — Kamino mission cycles
8. **Gate** — hard stop on `submit_ready`; else journal and wait for human

Mandatory: lab notebook entry per run (`lab-notebook` skill). Folded history: `hipif/folded_context.json`.

---

## Hypothesis generation

- Systematic generation over ad-hoc only.
- Priority to **novel vectors** (no obvious external shocks).
- Ranking: impact, novelty, testability, research focus alignment.
- `compose()` for multi-stage attacks.
- LLM assistance bounded — always `validate_hypothesis()`; `metadata.trusted=false`.

---

## Validation & evidence

**Multi-axis:** Likelihood, Impact, Stealth/Realism, Generality.

**Evidence grading:**
- Level 1: Structural + Monte Carlo
- Level 2: CPCV/PBO survival
- Level 3: Fork or validator reproduction
- Level 4: Root cause + reproducible artifacts

**External reporting bar:** Level 3+ minimum; `submit_ready` requires grade 4 + balance verifier + non-catalogue + credible harness.

**Strict signals:**
- EVM: `fork_reproduced`
- Solana: `solana_reproduced` (not fixture in submit path when `klend_require_live`)

**Lab vs reality:** Always record whether vector survives deployed parameters.

---

## Documentation standards

Required artifacts:

- Ranked hypotheses with test status
- Evidence-graded findings with lab/reality distinction
- Lineage in findings store
- Lab notebook entry (`data/security_results/lab_notebook/YYYY-MM-DD-*.md`)
- HIPIF folded context for night runs
- Operator checkpoint before session rollover

---

## Integration with architecture

| Layer | Methodology role |
|-------|------------------|
| 1 Hypothesis Generation | Ranked, novel-focused creation |
| 4 Validation & Gates | Multi-axis, grading, verifier |
| 6 Orchestration | Bounty loop, RSI, Coordinator |
| 6.5 HIPIF | Night chain folding, repetition guard |

See `adversarial_research_architecture.md` v3.1.

---

## Continuous improvement

Methodology evolves from lab notebook learnings. Significant patterns → update this doc, `AUDIT.md` gaps, and architecture priorities.

---

*Current working methodology for Night Shift Security research and audit work.*