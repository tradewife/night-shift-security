---
name: modular-analysis-skill
description: Drop-in skill adapted from Glider query engine for static analysis, taint tracking, CFG/DFG traversal in bug bounty. Supports lazy reference loading, creativity layer for audited targets, integrates with bounty-loop. EVM priority with Solana compatibility.
---

# Modular Analysis Skill

**Purpose**: Enable high-signal static analysis and query-driven bug hunting using Glider-inspired fluent patterns elevated into NSS rigor. Combines discipline (traceability, gates) with creativity for heavily audited codebases.

## Core Philosophy
- Lazy/on-demand reference loading via references/ table.
- Metadata enforcement in docstrings.
- Static Analysis, Not Semantics principle.
- Creativity Layer: Neurodivergent pattern-mapping + relentless experimentation on top of gates.
- Hard-first on Primary Target Subsystem.

## References to Load
| Task | Reference File |
|------|----------------|
| Query examples | references/glider-query-recipes.md |
| Linting rules | references/lint-gates.md |

## Usage in Bounty-Loop
Integrate as --skill modular-analysis-skill in bounty loop for hypothesis expansion and invariant mining.

## Creativity Layer (Bug Bounty Domination)
Layer neurodivergent pattern-mapping, wild hypotheses, and relentless experimentation on disciplined static analysis for finding bugs missed by heavy audits. EVM priority lift while maintaining chain-agnostic foundation.

**Integration with Existing**: Feeds hypothesis-expansion and ultrafuzz-discovery. Use in bounty-loop with --creativity-mode full.