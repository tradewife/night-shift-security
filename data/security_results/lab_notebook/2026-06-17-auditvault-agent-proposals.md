# AuditVault Agent Proposals — 2026-06-17

**Context**: Post HIPIF bounty-depth chain (SPEC v4.2.0, completed 2026-06-17 05:32 UTC, gate_ok=true, submit_ready=false). Advisory mining only.

**Inputs read (in order)**:
- `data/security_results/hipif/folded_context.json` (confirmed complete, 13/13 folds)
- `data/security_results/platform/auditvault_findings.json` (2383 findings)
- `data/security_results/knowledge/auditvault_patterns.jsonl`
- `data/security_results/knowledge/auditvault_ids.jsonl` (1756 slug rows; severity_score=0.0 for all due to variable Obsidian impact tokens)
- `data/security_results/loop/refinement_hints.json`
- `data/security_results/loop/state.json` (saturated_slugs includes wormhole; avoided boosting saturated where possible but selected for curated overlap)

**CLI run**: `python -m night_shift_security.cli.main platform auditvault-summary` (axis distribution confirmed: staking/oracle/bridge dominant)

**Selection**:
- Limited to protocols overlapping existing curated NSS programs (wormhole selected for bridge axis overlap with recent depth run; 2 findings).
- Never boosted saturated slugs per skill rules.
- All proposals marked `metadata.trusted=false`, `source=auditvault-research`.
- No impact on `qualifies_for_submission()` (trust boundary SPEC §2 strictly observed; AuditVault advisory only).

**Proposal created**:
- File: `data/security_results/hermes_proposals/auditvault-20260617.json`
- `latest.json` symlinked to it.
- Target: wormhole
- 1 proposal entry using lineage from auditvault_ids.jsonl (bridge axis token account issues)
- Frontmatter keys used: atlas_axes, auditvault_id, severity_score, slug, title (from ids.jsonl)

**Trust boundary note**: Proposals are untrusted advisory signals. Pipeline gates, evidence grading, and submission criteria untouched. Severity noted as 0.0 pending impact token normalization in future AuditVault ingest.

Ready for next HIPIF ingestion via `--proposals`.