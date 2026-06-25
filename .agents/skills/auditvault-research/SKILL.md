---
name: auditvault-research
description: Use after the deterministic NSS HIPIF chain to mine the local Auditware AuditVault corpus (Obsidian-style markdown) for atlas-axis metadata, severity-ranked protocol coverage, and refinement-queue anchors. Use when wiring advisory audit data into Hermes proposals or surfacing cross-protocol axis gaps. AuditVault is informational only — never a substitute for live reproduction, fork validation, deployment viability, or any submission gate.
---

# AuditVault Research

Treat AuditVault as cross-protocol audit history (+2383 findings, +293 hacks, +826 protocols as of 2026-06-17). It complements Cyfrin Solodit by encoding Obsidian frontmatter (impact, auditors, atlas tags, sector) and wikilinked protocols. It is NOT evidence.

## Inputs

Read, in order:

1. `data/security_results/hipif/folded_context.json`
2. `data/security_results/platform/auditvault_findings.json`
3. `data/security_results/knowledge/auditvault_patterns.jsonl`
4. `data/security_results/knowledge/auditvault_ids.jsonl`
5. `data/security_results/loop/refinement_hints.json`
6. `data/security_results/loop/state.json` (look for `auditvault_boosted_slugs`)

If `folded_context.json` is missing, incomplete, or not `gate_ok` equivalent, write a short skipped note and do not create proposals.

## Outputs to use

- `auditvault_findings.json` — normalized per-finding JSON, severity_score in 0–5
- `auditvault_patterns.jsonl` — compact pattern distillation for `enrich_with_audit_corpus`
- `auditvault_ids.jsonl` — per-slug severity table; consulted by `auditvault_boost_actions_for_slugs`
- `auditvault_summary` (CLI) — non-evidence dashboard metrics for HIPIF scan_all

## Workflow

1. Confirm the deterministic chain completed today and did not create `submission_alert.json`.
2. Run `python -m night_shift_security.cli.main platform auditvault-summary` to enumerate slugs and atlas-axis distribution.
3. Cross-reference `auditvault_boosted_slugs` (RSI) with `state.json` saturation list — never boost a slug already marked saturated.
4. Convert only concrete protocol + axe matches into Hermes proposal parameters; mark every record as untrusted:

```json
{
  "template": "access_control_escalation",
  "parameters": {},
  "lineage": ["auditvault:<auditvault_id>"],
  "delegate_note": "AuditVault analogue: <title>; severity=<n>; axes=<list>; still requires NSS validation",
  "metadata": {
    "trusted": false,
    "source": "auditvault-research"
  }
}
```

5. Stage the payload under `data/security_results/hermes_proposals/auditvault-YYYYMMDD.json` and bump `latest.json` to the new file.
6. Log the new advisory coverage into a lab notebook entry referencing the trust boundary (SPEC §2).

## Proposal Contract

```json
{
  "run_id": "auditvault-YYYYMMDD",
  "campaign_id": "auditvault-hybrid-YYYY-MM",
  "target_slug": "<target>",
  "required_config": "src/night_shift_security/config/<target-config>.json",
  "allowed_templates": ["access_control_escalation"],
  "source_artifacts": [
    "data/security_results/knowledge/auditvault_patterns.jsonl",
    "data/security_results/knowledge/auditvault_ids.jsonl"
  ],
  "force_target": true,
  "metadata": {
    "trusted": false,
    "source": "auditvault-research"
  },
  "proposals": []
}
```

Prefer one target per proposal file. If multiple targets look useful, choose the one with the highest severity_max in `auditvault_ids.jsonl` and an active refinement hint.

## Gotchas

- AuditVault clone lives under `sources/auditvault/repo` (gitignored). If missing, `platform auditvault-sync` is a no-op (`status: skipped_no_repo`).
- Atlas axes (`bridge`, `oracle`, `lending`, `amm`, `staking`, `governance`, `perpetuals`, `messaging`, `mev`) are advisory topology tags, not evidence of exploitability.
- Severity 1-5 is taken from the `impact` or `class` frontmatter token; informational entries are score 1.
- `enrich_with_audit_corpus` stamps `auditvault_refs`, `auditvault_severity_max`, `atlas_axes`, and `audit_corpus_score` into vector metadata. None of these affect `qualifies_for_submission()`.
- `auditvault_priority_bump` and `auditvault_atlas_axis_gap` are advisory ranking signals — they never filter a candidate out of the queue.
- The conviction bonus (`auditvault_bonus` default 0.05) only fires when `auditvault_min_severity` is met; it cannot move a revoked candidate into `proceed`.
- Only HIGH/CRITICAL severity ≥ 3 AuditVault rows trigger an `auditvault_boost` RSI action. Lower severities are logged but ignored.
- The lab notebook MUST record the trust-boundary check (`qualifies_for_submission()` reading no AuditVault keys) before the corpus may influence any pipeline fold.
