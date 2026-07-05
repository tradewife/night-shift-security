---
name: vault-pattern-match
description: Cross-references a graphified target codebase (codegraph-x-ray output) against the local AuditVault corpus to surface structurally analogous historical vulnerabilities. Run after codegraph-x-ray has completed and produced invariants.md and property_candidates.md. Produces ranked pattern-match hits with per-finding graph anchor evidence. Pattern matches are advisory signals only — never evidence of exploitability and never a substitute for live reproduction or submission-gate validation.
---

# Vault Pattern Match

**Purpose**: Given a graphified target codebase, walk every high-centrality node and invariant candidate produced by `codegraph-x-ray` and look up structurally similar historical bugs in AuditVault. Output is a ranked, evidence-anchored hit list that accelerates `ultrafuzz-discovery` hypothesis generation.

This skill is a bridge layer. It does not reproduce bugs. It does not produce proposals. It produces pattern-match scaffolding — ranked AuditVault analogues with codegraph anchor evidence — that downstream skills consume.

## Prerequisites

Both of the following must be present before this skill runs:

1. `codegraph-x-ray` completed for the current target — `invariants.md`, `property_candidates.md`, and `codegraph-x-ray-summary.md` exist under `data/security_results/investigations/<target>/`
2. AuditVault corpus is populated — `data/security_results/knowledge/auditvault_patterns.jsonl` and `data/security_results/knowledge/auditvault_ids.jsonl` exist and are non-empty

If either prerequisite is missing, write a short `vault-pattern-match-skipped.md` explaining which gate failed and stop.

## Inputs

Read, in order:

1. `data/security_results/investigations/<target>/codegraph-x-ray-summary.md` — Primary Target Subsystem, key centrality nodes, blast radius findings
2. `data/security_results/investigations/<target>/invariants.md` — Categorised invariants (`G-N`, `I-N`, `X-N`, `E-N`)
3. `data/security_results/investigations/<target>/property_candidates.md` — Bug class column is the primary match key
4. `data/security_results/knowledge/auditvault_patterns.jsonl` — Normalised AuditVault pattern distillation; each line has `auditvault_id`, `bug_class`, `axis_tags`, `severity_score`, `root_cause_summary`, `protocol`
5. `data/security_results/knowledge/auditvault_ids.jsonl` — Per-slug severity table for boost decisions
6. `data/security_results/platform/auditvault_findings.json` — Full finding detail; load lazily, only for confirmed hits needing deeper context

## Matching Strategy

### Step 1: Build the Target Signature

From the codegraph-x-ray outputs, extract:

- **Primary Target Subsystem** name and its dominant bug-class hypotheses (from `property_candidates.md` bug class column)
- **Atlas axis inference**: map the subsystem type to one or more AuditVault atlas axes:
  - AMM / swap logic → `amm`
  - Vault / yield / cToken → `lending`
  - Oracle price feeds → `oracle`
  - Cross-program / bridge calls → `bridge` or `messaging`
  - Governance / timelock → `governance`
  - Staking / reward distribution → `staking`
  - Perps / funding / mark price → `perpetuals`
  - MEV / sandwich / front-run surface → `mev`
- **Invariant classes present**: note which of `G`, `I`, `X`, `E` categories are populated and which are sparse (sparse categories are likely underexplored attack surface)
- **High-centrality symbols**: list the top 5–10 function names / module paths from the `codegraph central` output

### Step 2: Query AuditVault

For each entry in `auditvault_patterns.jsonl`, score a match against the target signature using the following criteria:

| Criterion | Weight |
|---|---|
| `bug_class` matches a bug class in `property_candidates.md` | 3 |
| `axis_tags` overlaps with inferred atlas axes | 2 |
| `root_cause_summary` keywords appear in high-centrality symbol names or invariant descriptions | 2 |
| `severity_score` ≥ 3 | 1 |

Compute a `match_score` (max 8) for every `auditvault_patterns.jsonl` entry. Retain only entries with `match_score` ≥ 3.

### Step 3: Anchor to Graph Nodes

For each retained hit, identify the closest codegraph anchor — the specific function, module, or invariant ID from the x-ray outputs that most closely corresponds to the historical bug location. Record this as `graph_anchor`. If no anchor can be identified, set `graph_anchor: unanchored` and weight the hit lower in the final ranking.

### Step 4: Rank and Deduplicate

Sort the final hit list by:

1. `match_score` descending
2. `severity_score` descending
3. `graph_anchor != unanchored` (anchored hits first)

Deduplicate: if two hits share the same `bug_class` and `graph_anchor`, keep only the higher-scoring one and note the duplicate count in `duplicate_collapsed`.

Cap output at **20 ranked hits** to maintain signal quality. Log how many raw hits were scored and how many were below threshold.

## Outputs

Write all artifacts to `data/security_results/investigations/<target>/vault-pattern-match/`:

### `vault-pattern-match-hits.jsonl`

One JSON line per retained hit:

```json
{
  "rank": 1,
  "auditvault_id": "<id>",
  "protocol": "<protocol>",
  "bug_class": "<class>",
  "axis_tags": ["<tag>"],
  "severity_score": 4,
  "match_score": 7,
  "graph_anchor": "<function_or_invariant_id>",
  "root_cause_summary": "<1–2 sentence summary>",
  "duplicate_collapsed": 0,
  "trusted": false,
  "source": "vault-pattern-match"
}
```

### `vault-pattern-match-summary.md`

Human-readable report containing:

- Target name and Primary Target Subsystem
- Inferred atlas axes
- Total AuditVault entries scanned, hits above threshold, hits after dedup
- Top 5 hits as a table: `rank | protocol | bug_class | severity | match_score | graph_anchor`
- Coverage gaps: invariant categories that had zero matching AuditVault patterns (these are the least-precedented areas — flag them explicitly)
- Trust boundary reminder (one line): all hits are advisory; none affect `qualifies_for_submission()`

### `vault-pattern-match-skipped.md` (only if prerequisites are missing)

Short note stating which gate failed and what needs to run first.

## Handoff to Downstream Skills

- **`ultrafuzz-discovery`**: Consume `vault-pattern-match-hits.jsonl` as a seed signal when building the property fan-in table. Prioritise property candidates whose `bug_class` appears in the top-5 hits. Do not treat hits as validated hypotheses — treat them as warm starting points.
- **`auditvault-research`**: This skill does not replace `auditvault-research`. It uses the pre-computed output of that skill. If `auditvault_patterns.jsonl` is stale or missing, run `auditvault-research` first, then re-run this skill.
- **`hypothesis-expansion`**: Pass the top-ranked `graph_anchor` + `root_cause_summary` pairs as structured hypotheses for expansion.

## Gotchas & Guardrails

- This skill reads AuditVault outputs only — it never clones or re-syncs the vault. If the corpus is stale, that is a problem for `auditvault-research` to fix.
- `match_score` is a heuristic ranking signal. A score of 8 does not mean the bug exists in the target. A score of 3 does not mean it does not.
- `unanchored` hits are lower confidence. Do not build primary hypotheses on them without additional supporting evidence from codegraph or invariant work.
- For Solana targets, weight `X-N` cross-component invariants and `bridge`/`messaging` axis hits more heavily — CPI boundary bugs are the dominant historical pattern in the Solana AuditVault subset.
- Atlas axes are topology tags from AuditVault frontmatter, not a verified characterisation of the target. Verify axis inference against actual codegraph output before using it downstream.
- Coverage gaps (invariant categories with zero vault matches) are not proof of safety — they may indicate the target has a novel attack surface not yet represented in the corpus. Flag these to the lab notebook.
- Never write a Hermes proposal from this skill. Proposal generation belongs to `auditvault-research` and `hypothesis-expansion`.
- The lab notebook MUST record the trust-boundary check before any hit influences a pipeline fold.
