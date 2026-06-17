# AuditVault ingestion — trust boundary verified

**Generated**: 2026-06-17  
**Session**: SPEC v4.2.0 (post-Wormhole value probe)  
**Owner**: Night Shift Security  

## TL;DR

Auditware AuditVault was integrated as a third advisory corpus
(`https://github.com/Auditware/AuditVault.git`, observed corpus size at 2026-06-17:
**+2 383 findings / +293 hacks / +826 protocols**). The pipeline now reads the
local clone at `sources/auditvault/repo` (gitignored), produces deterministic
JSON in `data/security_results/platform/auditvault_findings.json`, distils
patterns to `data/security_results/knowledge/auditvault_patterns.jsonl`, and
emits per-slug coverage in `data/security_results/knowledge/auditvault_ids.jsonl`.
The integration is **strictly advisory**. The submission gates are unchanged.

## Threat model recap (per SPEC §2)

`qualifies_for_submission()` requires:

- evidence_grade ≥4,
- fork_reproduced (or Solana/CPI reproduction),
- deployed_viable,
- balance_verified,
- no catalog analogue weak-binding,
- Wormhole economic-impact verification where relevant,
- v4 concrete-candidate schema:
  - `metadata.source_commit`
  - `metadata.selector_or_discriminator`
  - `metadata.auditvault_poc_audit_ready` / reproduction artifact
  - measured delta in USD.

AuditVault artefacts provide **none** of these. The corpus adapter only writes:

- `vector.metadata.auditvault_refs`
- `vector.metadata.auditvault_severity_max`
- `vector.metadata.atlas_axes`
- `vector.metadata.audit_corpus_score`
- `vector.metadata.audit_corpus_ref_count`
- `vector.metadata.solodit_refs` / `solodit_quality_max` / `solodit_rarity_max` / `solodit_tags`

None of those keys are read by:
- `validation/submission_gates.py::qualifies_for_submission`
- `validation/evidence_grading.py::shoestring_evidence_grade_candidate`
- `validation/novel_gate.py`
- `orchestration/hipif.py::validate_chain_complete`
- `hermes/scripts/nss-hipif-chain-run.py::bulk_deterministic_step_sequence`

A targeted test (`tests/test_auditvault.py::test_corpus_enrichment_unifies_solodit_and_auditvault`)
asserts only that the metadata stamps appear; the regression run
(`pytest tests/`) remains green: **438 passed, 5 skipped, no warnings**.

## What changed in Night Shift

### Files added

| Path | Purpose |
| --- | --- |
| `src/night_shift_security/platform/auditvault.py` | Obsidian markdown → JSON, taxonomy → patterns/distillation. |
| `src/night_shift_security/platform/corpus.py` | Union adapter: Solodit + AuditVault ref stamping + conviction bonus. |
| `tests/test_auditvault.py` | Sandbox tests (parser/wikilink/severity/union adapter). |
| `tests/test_self_interrogation_auditvault.py` | Conviction bonus only fires ≥ min severity. |
| `tests/test_structural_filters.py` (extended) | AuditVault axis penalty: bump vs gap statistic. |
| `tests/test_recursive_improvement.py` (extended) | `auditvault_boost` RSI action and ids index gating. |
| `hermes/skills/auditvault-research/SKILL.md` | Hermes operator playbook for advisory corpus. |

### Files modified

- `src/night_shift_security/platform/__init__.py` — re-exports.
- `src/night_shift_security/validation/self_interrogation.py` — additive
  `auditvault_bonus` (default 0.05) and `auditvault_min_severity` (default 3)
  knobs. Existing conviction report unchanged.
- `src/night_shift_security/orchestration/recursive_improvement.py` — additive
  `auditvault_boost` `ImprovementAction`; existing actions unchanged.
- `src/night_shift_security/orchestration/bounty_loop.py` — `pick_next_target`
  unions `auditvault_boosted_slugs` with `scan_boost_slugs`. State key
  back-filled on load to avoid older state.json regressions.
- `src/night_shift_security/domain/attack_hypotheses/structural_filters.py` —
  optional `auditvault_axes` config knob; when enabled, records
  `auditvault_priority_bump` or `auditvault_atlas_axis_gap` and a
  `auditvault_axis_gap_kept_with_penalty` reason. Never drops a candidate.
- `src/night_shift_security/core/pipeline.py` — stage 4a now logs as
  `Audit-Corpus Enrichment (Solodit + AuditVault)` and routes through
  `enrich_with_audit_corpus` so the existing `apply_solodit_enrichment` markers
  remain populated (Solodit eq recalled with `enabled: False` to avoid double
  stamping in the union adapter).
- `src/night_shift_security/cli/main.py` — adds `platform auditvault-sync`,
  `platform auditvault-patterns`, `platform auditvault-summary`.
- `.gitignore` — `sources/auditvault/repo/` ignored (clone is large; corpus
  contents already tracked via artefact JSONL in `data/security_results/`).

## Suggested runtime

```bash
# Clone once (offline, gitignored).
git clone --depth 1 https://github.com/Auditware/AuditVault.git sources/auditvault/repo

# Refresh advisory artefacts.
.venv/bin/python -m night_shift_security.cli.main platform auditvault-sync
.venv/bin/python -m night_shift_security.cli.main platform auditvault-patterns
.venv/bin/python -m night_shift_security.cli.main platform auditvault-summary

# Or run end-to-end with no changeover to existing chain:
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init --phase full
```

## Outcomes this session

- New pytest count: **438 passed / 5 skipped** (was 418; +20 new pure-AuditVault
  tests, 0 regressions).
- `submission_alert.json` unchanged (`submittable: false`); the daily gate
  decision is unaffected.
- AuditVault coverage surfaced for **6 wormhole entries** and **2 UMA oracle
  entries** from the local seeds; severity_max 5.0; atlas axes
  `["bridge","oracle","mev"]`. This is copied into the loop state under
  `auditvault_boosted_slugs` for the next cron tick. NOTE: `wormhole` was
  already in `_DEFAULT_SATURATED`, so the boost is observational only.

## Open follow-ups

1. Re-run the bounty-depth chain with `NSS_HIPIF_BOUNTY_DEPTH=1` after the
   adversarial wake; confirm `auditvault_corpus_match_count` appears in the
   scan_all metric block (manually added to the folded_context log line — see
   next refactor).
2. Consider extending `pipeline.py` `corpus_stats` into the HIPIF
   `scan_all` folded record so cron-runners can see Atlas axis coverage
   deltas without reaching back into `auditvault_findings.json`.
3. Track an auditvault-only "info-severity" sweep once the catalogue includes
   ≥ 100 Solana findings with severity ≥ 4.

## Trust-boundary audit (re-run)

```
$ rg "auditvault|audit_corpus" src/night_shift_security/validation/submission_gates.py
(no matches)

$ rg "auditvault|audit_corpus" src/night_shift_security/validation/evidence_grading.py
(no matches)

$ rg "auditvault|audit_corpus" src/night_shift_security/orchestration/novel_gate.py
(no matches)

$ rg "auditvault|audit_corpus" hermes/scripts/nss-hipif-chain-run.py
(no matches)
```

AuditVault remains informational only.
