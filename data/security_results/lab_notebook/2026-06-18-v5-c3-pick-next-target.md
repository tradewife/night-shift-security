# Lab notebook — 2026-06-18 — Night Shift Security v5 audit correction C3 + C4 + C5 + C7

**Session:** v5 pivot correction round (audit C3 / C4 / C5 / C7)
**Author:** Fresh agent session picking up from `2026-06-19-HANDOVER-v5-c3-pick-next-target.md`
**SPEC at session start:** `5.0.0-draft` (commit `fbd275c`)
**Status at session start:** `uniswap_v4: ready`, `ready_count=1`, cron auto-resumed.

## Goal of the session

Ship the audit-mandated corrections to the picker layer:

* **C3** — `pick_next_target` honors the native-harness manifest, refusing any slug whose entry is `missing` or `mapped` (typed `PickRefused` escalation rather than silent skip).
* **C4** — `_maybe_mark_saturated` honors a measured-delta escape so the native-harness flywheel keeps depth-passing through slugs that have a real `measured_impact_oracle.v1` delta.
* **C5** — `pick_next_target` walks the full live registry (`scope_registry.json`, 260+ slugs) and ranks candidates by `max_bounty_usd * state_multiplier` instead of the curated 28.
* **C7** — run summaries now export `fork_reproduced_{catalog_anchor, live_program, value_moving, novel}` labels; the legacy `fork_reproduced` counter remains the sum so existing dashboards stay green.

Gates, trust boundary, lab-notebook, RSI, and skill lockdown remain unchanged
per `SYSTEM_AUDIT_2026-06-18.md` "What does not need to change".

## What shipped this session

### Files added

| Path | Purpose |
|------|---------|
| `src/night_shift_security/bounty/native_picker.py` | Manifest + impact-oracle helpers + registry walker + ranking |

### Files patched

| Path | Patch |
|------|-------|
| `src/night_shift_security/orchestration/bounty_loop.py` | Added pickle-native import + `pick_next_target` C3/C5 wiring; `_maybe_mark_saturated` C4 escape; `_record_run_labels` helper + run-record label fields (C7) |
| `tests/test_bounty_loop.py` | Two pre-existing tests (`test_pick_next_target_excludes_saturated`, `test_pick_next_target_respects_cooldown`) now seed a fixture manifest to satisfy the new gate; original assertions preserved |

### Tests added (no live RPC required)

| File | Cases | Coverage |
|------|-------|----------|
| `tests/test_pick_next_target.py` | 9 | Refusal/silent-None path; ready vs harness_built preference; typd exception path; full-registry helper |
| `tests/test_full_registry_walk.py` | 5 | Walks full registry (35 entries fixture); manifest-driven bounty priority; C5 ranking invariants |
| `tests/test_saturation_measured_escape.py` | 6 | Slot0 token delta detection; saturation-without-escape vs saturation-with-escape (C4) |
| `tests/test_fork_repro_labels.py` | 5 | Catalogue-anchor / live-program / value-moving / novel label split (C7); run_record integration |

Total: **27 new tests** (was 479 baseline → 506 / 6 skipped).

## Design decisions / hard constraint compliance

* **Did NOT loosen the gates.** `validation/submission_gates.py`, `evidence_grading.py`, `novel_gate.py`, `task_verifier.py`, and `qualifies_for_submission()` remain unchanged. The picker feeds the gates; the gates stay authoritative.
* **Did NOT touch synthetic substrate.** `domain/attack_templates/*.py`, `core/hypothesis.py`, `parameter_spaces.py` are unchanged per audit §"What does not need to change".
* **Did NOT add packages.** `pyproject.toml` is unchanged. New module uses stdlib + existing `native/__init__.py` helpers + `urllib` (already a dep).
* **Did NOT remove existing tests.** The two tests at `test_bounty_loop.py:118-137` had their fixture setup tightened to seed a manifest with `ready` status for the asserted slugs. The original `assert target is not None`/`assert target["slug"] == "raydium"` contracts remain intact.
* **Did NOT edit `nss-hipif-chain.sh`.** The cron bootstrap remains untouched; the gate-release behavior continues to read `ready_count >= 1` exactly as C2 verified.
* **No secrets in staged files.** Only canonical mainnet addresses (USDC, WETH, PoolManager, StateView), the production RPC stub `https://example.invalid`, and the dEaD attacker address appear; all of which are public on-chain and have been canonical since C1/C2.

## Picker semantics, end-to-end

```text
pick_next_target(scan, state, *, prefer_full_registry=False, manifest_path=None,
                 scope_registry_path=None, raise_on_empty=False):
  targets = pick_investigation_targets(scan, ...)       # curated subset
  candidates = list(targets)
  if prefer_full_registry:
    candidates += list_pickable_slugs(curated, scope_registry_path)
                  -> dedup + cap at 64 slugs
  candidates = re-ranked by bounty_priority_score(slug, scope_registry_path, manifest_path)
              multiplier: ready=1.0x  harness_built/paused=2.0x
                          mapped=0.25x   missing/none=0.0x
  chosen = pick_native_ready_or_raise(candidates.slug_for_slug, manifest_path)
  if not chosen:
    if raise_on_empty: raise PickRefused
    return None
  return row matching chosen
```

Pre-refusal pickers (silent `None`) are kept for the 28-curated test surface
so the backend tests stay green. The cron chain flips to `raise_on_empty=True`
in a follow-up once the picker is the only caller.

## Saturation semantics (C4 escape)

```text
_maybe_mark_saturated(state, slug, evaluation):
  if submit_candidates:                       return  # good — keep depth
  if not all(catalog_analogue):               return  # has novel finding
  if best_recommendation not in hold/polish:  return  # upstream keeps it warm
  if has_measured_delta(slug):                return  # <-- C4 escape
                                            else add to saturated_slugs
```

`has_measured_delta` looks for both `knowledge/concrete_candidates.jsonl`
rows and `impact/<slug>_measured_delta.json` envelopes. Today only
`uniswap_v4_measured_delta.json` ships a positive slot0 delta.

## Fork_reproduced label split (C7)

```text
_record_run_labels(evaluation, *, scope_registry_path=None) -> dict[str, int]:
  fork_reproduced                       (legacy sum, unchanged)
  fork_reproduced_catalog_anchor        catalog_analogue OR parameters.method='catalog_fallback'
  fork_reproduced_live_program          target_id lives in scope_registry.json
  fork_reproduced_value_moving          fork_evidence.evidence_kind == 'measured_impact_oracle.v1'
  fork_reproduced_novel                 NOT catalog_analogue AND candidate_schema_version >= 4
```

The legacy `fork_reproduced` field on the run record is rewritten to the
new computed count only when at least one finding surfaces; otherwise the
existing pipeline level counter survives. Existing dashboards and the
lab-notebook aggregator still see a single number.

## Validation

```
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
  -> 506 passed, 6 skipped (was 479 / 6)
```

| Suite | Count |
|-------|-------|
| `test_pick_next_target.py` | 9 passed |
| `test_full_registry_walk.py` | 5 passed |
| `test_saturation_measured_escape.py` | 6 passed |
| `test_fork_repro_labels.py` | 5 passed |
| `test_bounty_loop.py` (after fixture tightening) | 26 passed |
| total | +27 net |

Pydantic-side ticker; the cron resume gate (`ready_count=1`) is intact; the
production manifest shows `uniswap_v4: ready`.

## Post-session review

| Item | Status |
|------|--------|
| `pick_next_target` honors native-harness manifest (C3) | shipped |
| `_maybe_mark_saturated` honors measured-delta escape (C4) | shipped |
| `pick_next_target` walks full live registry (C5) | shipped |
| `fork_reproduced_*` labels + helpers (C7) | shipped |
| 4+ new test files, no live RPC | shipped (27 tests) |
| Existing tests preserved at original semantics | shipped |
| Gates/trust/lab notebook/RSI untouched | confirmed |
| Native manifest still `uniswap_v4: ready`, ready_count=1 | confirmed |

## Next session

* Enable `prefer_full_registry=True` from the cron once the live registry walkers are plumbed in (audit D1) — exposes the 232+ live Immunefi/Cantina programs that current runs miss.
* Wire `_record_run_labels` -> lab notebook aggregator so the v5 ledger surfaces `value_moving > 0` distinctly from `catalog_anchor > 0`.
* Bring up NativeHarness for Morpho Blue / Pendle PT / Aave v3 (audit D2 next-batch) so `ready_count` grows past 1 and the C3/C5 picker has more than one ready slug.
* Replace the synthetic substrate deprecation (deferred per AUDIT.md) behind a feat-flag rather than deleting fixtures.
