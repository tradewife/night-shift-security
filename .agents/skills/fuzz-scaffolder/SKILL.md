---
name: fuzz-scaffolder
description: Optional accelerator and scaffolder for ultrafuzz-discovery. Brings parallel specialized invariant discovery agents, automated harness/handler scaffolding, coverage-driven refinement loops, property tagging, and reproducible test generation helpers from high-quality EVM fuzz patterns. Designed to speed up property fan-in and executable attempts phases while preserving NSS rigor, fresh-context pass@k, adjudication, and Crucible usage. Trigger on fuzz-scaffolder, accelerate invariant discovery, generate fuzz harness, scaffold handlers.
---

# Fuzz Scaffolder

**Role**: Optional accelerator and scaffolder.  
**Never replaces** `ultrafuzz-discovery`. Use it to bootstrap faster, then hand off to the core rigorous workflow (property fan-in table, strategy fan-out, fresh-context attempts, strict adjudication, Crucible for Solana).

This skill extracts and elevates the highest-value meta-patterns from mature automated fuzz harness generation systems (parallel discovery agents, scaffolding, coverage loops, tagging) and makes them available inside the NSS evidence-driven loop.

## When to Use

Invoke during these phases of `ultrafuzz-discovery`:

- Early property fan-in (to accelerate initial invariant candidate generation)
- Harness setup / executable attempts (to rapidly scaffold starting handlers and fixtures)
- New target onboarding where manual harness writing is the current bottleneck
- EVM/Foundry targets (stronger direct support)
- Solana targets (use for faster Crucible fixture bootstrapping + initial property candidates only)

**Do not** use for:
- Final adjudication or submission decisions
- Claims of honest-zero or empirical-FNR
- Pure Solana sequence bugs where Crucible typed actions are already mature

## Core Principles

- **Accelerator, not authority**: Generated candidates and harnesses are starting points only. All must pass through `ultrafuzz-discovery` gates (property table, pass@k, adjudication, substrate confirmation).
- **Preserve NSS rigor**: Every output must clearly mark what is proposed vs validated. No bypassing fresh-context repetition or failure preservation.
- **Target-specific**: Scaffolding and discovery agents must be adapted to the protocol's actors, account model, trust boundaries, and bounty scope.
- **Handoff discipline**: Always produce clear artifacts that drop cleanly into `property_fanin.md`, `strategies/`, and investigation directories.

## Workflow

### 1. Invocation & Context Loading

Read (in order):
1. Current `ultrafuzz-discovery` investigation directory and `property_fanin.md` (if exists)
2. Target source, IDL/ABI, account map, prior recon
3. Bounty scope and known high-impact surfaces

Create or update investigation artifacts under the existing run directory.

### 2. Parallel Specialized Discovery Agents (Optional Accelerator)

When property fan-in is thin or the target is complex, optionally spawn parallel discovery agents focused on different invariant classes:

- Conservation / accounting invariants
- Authority / access control / PDA constraints
- Ordering / sequencing / flash-loan style
- Oracle / price / time / slot dependent
- Token-2022 / extension accounting
- Cross-program / composability assumptions
- Economic / incentive invariants

Each agent produces candidate properties with:
- Clear invariant statement
- Proposed `property_id` prefix suggestion
- Location / derivation evidence (source references)
- Suggested `bug class`
- Initial `kill criteria`
- Guarantee tag: `SHOULD-HOLD` (structurally enforced) or `EXPLORATORY` (inferred, needs more evidence)

**Output**: Updated `property_fanin.md` with new candidate rows clearly marked as "Agent-proposed".

**Rule**: Agent proposals never count toward pass@k or honest-zero claims until manually reviewed and executed in fresh-context attempts.

### 3. Harness & Handler Scaffolding

Generate starting harness / fixture / handler code using protocol-aware templates:

- For **Crucible (Solana)**: Produce `TargetFixture` skeleton with `setup()`, typed action methods, and initial invariant test stubs. Include comments for PDA derivation, signer constraints, and state snapshots.
- For **Foundry (EVM)**: Produce test contract skeleton with `setUp()`, handler functions, and invariant tests using `fuzz_assert_*` style where possible.

Include:
- Realistic deployment and role setup based on protocol analysis
- Clamping / edge-case handling stubs for inputs
- Coverage target comments (e.g. "Aim for 80%+ on core state transitions")
- Clear handoff markers: "// TODO: Review and harden before pass@k runs"

**Output**: Files placed in `harness_scaffold/` inside the investigation directory, ready for manual refinement.

### 4. Coverage-Driven Refinement Recommendations

Provide a short, actionable refinement plan:

- Recommended coverage targets per major component
- Suggested iteration loop (run → measure coverage → adjust handlers/actions → repeat)
- Priority order for handler implementation (highest blast-radius surfaces first)
- When to switch from broad exploration to targeted strategies

This feeds directly into the "Executable attempts" phase of `ultrafuzz-discovery`.

### 5. Property Tagging Support

Add optional metadata columns to `property_fanin.md`:
- `guarantee_level`: `SHOULD-HOLD` | `EXPLORATORY`
- `discovery_source`: `manual` | `agent-proposed` | `scaffold-derived`

This helps prioritization during strategy fan-out and adjudication without changing core NSS classification.

### 6. Reproducible Test Helpers

When violations are found during scaffolding or early runs, provide helpers to generate clean, deterministic repro tests (Foundry-style for EVM, minimized Crucible sequences for Solana).

These are **starting points** only — final repros must still go through `ultrafuzz-discovery` failure preservation and `crucible tmin` (or equivalent) processes.

### 7. Handoff & Documentation

Always produce:
- Updated `property_fanin.md` with agent proposals clearly separated
- `harness_scaffold/` directory with generated starting code + README explaining what was auto-generated vs what needs manual work
- Short `scaffolder_notes.md` summarizing decisions, assumptions, and recommended next manual steps

Never mark any scaffolded artifact as validated. All validation happens in the parent `ultrafuzz-discovery` workflow.

## Gotchas & Guardrails

- Scaffolding speed must not replace rigorous property definition or fresh-context repetition.
- For Solana, never treat generated Crucible fixtures as production-ready without full review of PDA seeds, authority constraints, and CPI restrictions.
- `SHOULD-HOLD` tags are suggestions only — final classification is done via adjudication in `ultrafuzz-discovery`.
- Coverage targets are heuristics. Real pass@k evidence comes from executed fresh-context attempts on the substrate.
- This skill increases velocity on new targets. It does not change NSS evidence standards or submission gates.

## Integration with ultrafuzz-discovery

Recommended call points inside `ultrafuzz-discovery`:

1. After initial source reading, before writing the first property fan-in table → optional `fuzz-scaffolder` invocation for agent-proposed candidates.
2. During harness setup → optional scaffolding of starting fixtures/handlers.
3. After early fuzz runs show coverage gaps → use refinement recommendations.

The parent skill remains responsible for:
- Canonical property table ownership
- Strategy creation
- All pass@k execution and recording
- Failure preservation
- Adjudication
- Summary and handoff

## Output Standards

Every run must leave behind clear, auditable artifacts that another NSS agent can continue without re-deriving the scaffolding decisions.

This skill exists to make the hard parts of `ultrafuzz-discovery` (property discovery and harness creation) faster and more consistent, while protecting the uncompromising rigor that makes NSS submissions defensible.
