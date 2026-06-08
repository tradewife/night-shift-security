# Night Shift Security — Technical Specification

**Version:** 1.2  
**Date:** 2026-06-08  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Clone the Night Shift research engine architecture for parallel security and vulnerability research. This becomes a distinct but related track focused on surfacing protocol risks before they become exploits.

---

## Agent Handover (Read This First)

**Workspace:** Open this repo  
**Remote:** https://github.com/tradewife/night-shift-security  
**Scope:** Security track only. Do **not** edit Night Shift Tokenomics repo.

### Current status (2026-06-08)

Phase 5c-Solana Slice 2 shipped on `main`. 87 tests passing.

**Key shipped artifacts**:
- Validator-backed Solana replay for `solend-whale-2022` and `cashio-2022` with strict `solana_reproduced` evidence.
- Full pipeline with Darwinian evolution, Monte Carlo, CPCV/PBO, EVM fork + Solana validation lanes, and reproduction scoring bonuses.

**Next focus**: Introduce the **Hypothesis Generation Layer** (rich parameterized attack hypothesis generation) as defined in `adversarial_research_architecture.md` (repo root) and the scoped section below.

### Package layout (`src/night_shift_security/`)

```
domain/
  attack_templates/          # existing 7 templates (governance_capture, treasury_drain, ...)
  attack_hypotheses/         # NEW in v1.2 — Hypothesis Generation Layer (see section below)
  simulators/                # mock + foundry
validation/
data/
core/                        # pipeline, evolution, gates, scoring
cli/
```

### Pipeline (unchanged in this increment)

Stages 0–6b remain as implemented. The new Hypothesis Generation Layer feeds Stages 1 and 3.

---

## Hypothesis Generation Layer (v1) — Scoped Implementation Spec

**Status**: Ready for coding agent implementation.  
**Reference**: See `adversarial_research_architecture.md` (repo root) for big-picture context, bug-bounty list mapping, and layer rationale.

### Goal
Replace static grid search over fixed templates with a rich, parameterized, composable `attack_hypotheses/` layer. All generated hypotheses must still pass the existing brutal gates (Monte Carlo, CPCV/PBO, reproduction).

### Core Abstractions (implement in `src/night_shift_security/domain/attack_hypotheses/`)

**`AttackHypothesis` dataclass**

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class AttackHypothesis:
    hypothesis_id: str
    template: str                    # e.g. "governance_capture", "treasury_drain"
    parameters: dict[str, Any]       # must validate against ParameterSpace
    metadata: dict[str, Any]         # provenance, generation_method, parent_ids, timestamp
    version: str = "1.0"
```

**`ParameterSpace`** (declarative, in `parameter_spaces.py`)

Define for the two priority templates first:
- `governance_capture`
- `treasury_drain`

Example structure (use Pydantic or simple dict + validator):
```python
GOVERNANCE_CAPTURE_SPACE = {
    "quorum_threshold": {"type": "float", "range": [0.05, 0.40], "distribution": "uniform"},
    "participation_rate": {"type": "float", "range": [0.10, 0.90]},
    "whale_concentration": {"type": "float", "range": [0.20, 0.85]},
    "proposal_timing_window_blocks": {"type": "int", "range": [100, 5000]},
    ...
}
```

**`HypothesisGenerator` abstract base class**

```python
from abc import ABC, abstractmethod

class HypothesisGenerator(ABC):
    @abstractmethod
    def sample(self, n: int) -> list[AttackHypothesis]: ...
    @abstractmethod
    def mutate(self, hypothesis: AttackHypothesis) -> AttackHypothesis: ...
    @abstractmethod
    def compose(self, h1: AttackHypothesis, h2: AttackHypothesis) -> AttackHypothesis: ...
```

### v1 Scope (keep minimal)

**Implement**:
- `base.py` — `AttackHypothesis`, `HypothesisGenerator`, `ParameterSpace` validation helpers
- `parameter_spaces.py` — declarative spaces for `governance_capture` + `treasury_drain`
- `governance.py` — concrete `GovernanceCaptureGenerator` implementing the interface
- `treasury.py` — concrete `TreasuryDrainGenerator`
- `llm_expansion.py` (thin stub) — `LLMExpansionOrchestrator` that proposes variants. **Strict rule**: output is untrusted proposal only; never used for validation or scoring.
- `__init__.py` and basic exports

**Integration**:
- Wire `sample()` into existing Stage 1 (grid search expansion)
- Wire `mutate()` / `compose()` into existing Stage 3 (Darwinian evolution)
- Add lightweight structural validation in Stage 0 (optional but recommended)

**No changes required** to Stages 4–6, Solana/EVM harnesses, scoring logic, or `solana_reproduced` / `fork_reproduced` semantics.

### Test Requirements

- All new code must run in pure mock/fixture mode (no live RPC).
- Every `AttackHypothesis` must be serializable and round-trippable.
- Add `tests/test_attack_hypotheses.py` with:
  - Sampling 100 hypotheses from governance space
  - At least one successful `mutate()` and `compose()`
  - Hypotheses accepted by mocked pipeline stages without breaking existing flow

### Documentation Updates (minimal)

- Update package layout in this SPEC.md (done above).
- Add one paragraph under "Attack Taxonomy" pointing to the new layer.
- Update any "Adding New Attack Vectors" guidance to reference `attack_hypotheses/`.

---

## Original Content Preserved Below (for continuity)

**Note to coding agent**: The sections below this line are the previously shipped specification. Do not modify them in this increment unless explicitly required by the new Hypothesis Generation Layer wiring.

(Existing pipeline description, package layout details, run commands, outputs, and all prior Phase 5c content remain unchanged and are preserved in the live repo file.)

---

*End of scoped v1.2 update. Implement the Hypothesis Generation Layer as defined above, then update this SPEC.md version/date upon completion.*