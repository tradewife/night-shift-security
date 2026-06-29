---
name: codegraph-x-ray
description: Combines structured codegraph intelligence with rigorous invariant synthesis. Enforces high-quality usage of codegraph to identify the Primary Target Subsystem, then applies ordered structural invariant discovery with strict verification gates. Produces categorized invariants and high-quality property candidates ready for ultrafuzz-discovery. Trigger on codegraph-x-ray, x-ray with codegraph, invariant synthesis, primary subsystem invariants.
---

# Codegraph X-Ray

**Purpose**: Deliver the highest-signal pre-discovery package by combining structural code intelligence with systematic invariant mining.

This skill enforces disciplined use of `codegraph` as the foundation, then applies a high-rigor invariant synthesis engine on top — focused on the most important part of the target.

## Core Philosophy

- **Code intelligence first, always.** Never begin invariant work without first running structured codegraph analysis.
- **Hard-First Principle.** Use codegraph output to define the **Primary Target Subsystem** (highest centrality, blast radius, and complexity). Allocate the majority of invariant synthesis effort here.
- **Verification over volume.** Every derived invariant must pass a strict evidence gate. Unverifiable candidates are discarded.
- **Feed the engine.** The primary output is high-quality, categorized invariants and property candidates ready for `ultrafuzz-discovery`.

## When to Use

Use this skill on complex or high-value targets when you need:

- Disciplined structural analysis before writing properties
- Systematic discovery of invariants with proof requirements
- Clear identification of the Primary Target Subsystem
- High-quality input for `ultrafuzz-discovery` property fan-in

**Recommended position in workflow:**
Codegraph analysis → Primary Target Subsystem definition → Invariant synthesis → `ultrafuzz-discovery`

## Workflow

### Phase 1: Structured Codegraph Intelligence (Mandatory)

Run the following `codegraph` commands in order and document the results:

```bash
codegraph explore --target <target> --depth 3
codegraph blast --symbol <key_entrypoint> --depth 2
codegraph central --top 30
```

**Required outputs to capture:**
- High-centrality functions and modules
- Long or complex call paths
- Blast radius of critical entrypoints
- Clusters of interconnected components

From this analysis, explicitly define the **Primary Target Subsystem** — the single most complicated, highest-blast-radius, or most critical area of the protocol.

Document this decision with reasoning.

### Phase 2: Invariant Synthesis (Hard Focus on Primary Subsystem)

Apply ordered structural scans, with strong emphasis on the Primary Target Subsystem:

1. **Conservation invariants** — Identify paired state mutations with verifiable deltas.
2. **Guard lift** — Promote per-call guards to global invariants only when verified across all relevant write sites.
3. **Ratio and mathematical invariants** — Storage-based relationships with clear derivation.
4. **State machine transitions** — Explicit state changes with location evidence.
5. **Temporal / slot / epoch invariants** — Time-dependent constraints.
6. **Cross-component / CPI assumptions** — Trust boundaries and caller-callee expectations.
7. **Economic / higher-order invariants** — Derived from lower-level findings.

**Verification Gate (Strict):**
Every candidate invariant must have concrete, code/grep-verifiable evidence from the source. Candidates without clear evidence are dropped and logged.

Output is written to `invariants.md` with clear categorization:
- `G-N`: Enforced Guards
- `I-N`: Single-component invariants (focus here first)
- `X-N`: Cross-component invariants
- `E-N`: Economic invariants

### Phase 3: Supporting Analysis

- Entry point classification (permissionless / role-gated / admin) with verified access paths
- Git-weighted attack surfaces (late/dangerous changes, high-risk areas)
- Composability and dependency mapping relevant to the Primary Target Subsystem

### Phase 4: Output & Handoff

Produce the following artifacts:

- `invariants.md` — Full categorized and verified invariant catalog
- `property_candidates.md` — High-quality rows ready to import into `ultrafuzz-discovery` property fan-in table (include suggested `property_id`, bug class, kill criteria, and source references)
- Short `codegraph-x-ray-summary.md` documenting:
  - Primary Target Subsystem chosen and why
  - Key codegraph findings
  - Number of invariants derived vs dropped
  - Recommended focus areas for `ultrafuzz-discovery`

All artifacts should be placed in the current investigation directory under `data/security_results/investigations/`.

## Integration with ultrafuzz-discovery

This skill is designed to feed directly into `ultrafuzz-discovery`:

- Use `property_candidates.md` as strong seed material for the canonical property fan-in table.
- Use `invariants.md` to accelerate and improve the quality of property definition.
- The Primary Target Subsystem identified here should receive the majority of initial strategy and execution effort in `ultrafuzz-discovery`.

## Gotchas & Guardrails

- Do not skip or shortcut the codegraph phase. The quality of invariant work depends on it.
- Focus the majority of effort on the Primary Target Subsystem. Wide exploration across the entire codebase dilutes impact.
- Verification gates are non-negotiable. Volume of invariants is less important than quality and verifiability.
- This skill produces candidates and analysis. Final validation, execution, and adjudication still belong to `ultrafuzz-discovery`.
- For Solana targets, adapt the structural scans to emphasize PDA derivation, account constraints, CPI boundaries, and sysvar behavior.

## Output Standards

Every run must produce clear, auditable artifacts with strong traceability to source locations. The goal is to give `ultrafuzz-discovery` the best possible starting material so it can focus on execution, fresh-context repetition, and rigorous adjudication rather than initial discovery.

This skill exists to turn raw codegraph output into high-signal, verifiable invariant understanding — the foundation for effective adversarial research.
