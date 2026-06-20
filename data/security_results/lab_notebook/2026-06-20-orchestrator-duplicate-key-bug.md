# 2026-06-20 — Critical bug found and fixed: duplicate JSON key drops 8 ready targets

**Author:** Orchestrator (self-evolving audit loop)
**Session:** First orchestrator session after v6 handoff
**Finding:** DATA CORRUPTION BUG — `native_harness_status.json` duplicate `"harnesses"` key
**Severity:** CRITICAL — silently drops 8 ready targets, stales `ready_count`, breaks bounty loop picker
**Status:** FIXED + defensive hardening in code

---

## What happened

Commit `482fd4f` (orchestrator handoff) added Ethena + Reserve entries to `native_harness_status.json` by appending a second `"harnesses"` key block at the bottom of the file. Per the JSON spec, duplicate keys at the same level result in the **last** value winning. Python's `json.loads()` silently discards the first `"harnesses"` dict (containing all 8 ready targets), keeping only the second (containing ethena_native + reserve).

**Impact:**
- `load_manifest()` returns only 2 harnesses (ethena_native + reserve) instead of 9
- `ready_count` metadata says 8, but actual ready count from the harnesses dict is 1 (reserve)
- `native_picker.filter_native_ready()` returns only 1 slug (reserve) instead of 8
- `pick_next_target_v6_phase4()` only sees reserve + ethena_native as candidates
- The bounty loop can no longer pick from the 8 established ready targets (uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca)
- The cron bootstrap gate passes (reserve is ready), but the loop's target selection is severely constrained

**Root cause:** Commit `482fd4f` manually edited the JSON file instead of using the `upsert_harness()` function, which correctly writes all entries under a single `"harnesses"` key.

## Discovery

The bug was discovered by running the full test suite. Test `test_cron_unpause.py::test_manifest_has_at_least_two_ready` failed:

```
AssertionError: assert 'uniswap_v4' in ['reserve']
```

The test iterates `data.get("harnesses").items()` and finds only `['reserve']` as ready, because Python's `json.loads` kept only the last duplicate `"harnesses"` key.

## Fix applied

### Data fix
Rewrote `data/security_results/loop/native_harness_status.json` to have a single `"harnesses"` key containing all 9 entries (8 ready + 1 scaffolded).

### Code fix (defensive hardening)
Modified `load_manifest()` in `src/night_shift_security/native/__init__.py` to **recompute `ready_count`** from the actual harnesses dict on every load, rather than trusting the file's `ready_count` metadata. This prevents future duplicate-key or manual-edit bugs from silently masking a stale count.

```python
# Defensive: recompute ready_count from the actual harnesses dict
# so stale metadata never masks a data-corruption bug (duplicated
# JSON keys, manual edits, etc.).
harnesses = data.get("harnesses") or {}
data["ready_count"] = sum(
    1 for h in harnesses.values()
    if isinstance(h, dict) and h.get("status") == "ready"
)
```

## Verification

- `python3 -m pytest tests/ -q` — **790 passed, 11 skipped, 0 failed**
- Direct verification: `load_manifest()` returns 9 harnesses, 8 ready, ready_count recomputed to 8
- The previously failing `test_cron_unpause.py` now passes (all 8 tests)

## Lesson learned

**Never manually edit JSON files with the same key appearing twice.** Always use the `upsert_harness()` function which writes all entries under a single key. The defensive recomputation in `load_manifest()` is now the permanent guard against this class of bug.

---

## Files modified

| File | Change |
|------|--------|
| `data/security_results/loop/native_harness_status.json` | Merged duplicate `"harnesses"` keys into single dict |
| `src/night_shift_security/native/__init__.py` | `load_manifest()` recomputes `ready_count` from harnesses dict |
| `data/security_results/lab_notebook/2026-06-20-orchestrator-duplicate-key-bug.md` | This file |
