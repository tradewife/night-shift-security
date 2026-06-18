# Session handover — Night Shift Security v5 C3 (Pick-Next-Target + NativeHarness manifest gate)

**Paste this entire document into your next session as context.**

You are a fresh agent. The previous two sessions shipped audit corrections
**C1** (NativeHarness for Uniswap v4) and **C2** (MeasuredImpactOracle +
first real on-chain delta). Your job is **audit correction C3**: wire the
NativeHarness manifest into `bounty_loop.pick_next_target` so the loop
refuses to enqueue any slug whose native substrate is missing or whose
harness is not `ready`. Then extend the picker to **walk the full live
registry** (C5 from the audit) and surface the next-best target with a
real, measured-delta candidate. Finally, harden the **fork_reproduced
aggregator** (C7) so the metric labels differentiate catalogue-anchor
finds from live-program finds. These three corrections unlock the cron.

---

## 1. Where we are

You are continuing the **Night Shift Security v5 pivot** at SPEC
`5.0.0-draft`, most recent commit `fbd275c` ("SPEC 5.0.0 first measured
delta: uniswap_v4 MeasuredImpactOracle (audit C2)"). The chain:

| Commit | Phase | Deliverable |
|--------|-------|-------------|
| `018ee06` | v5 pivot | SPEC 5.0.0-draft — NativeHarness substrate gate |
| `1c09485` | C1 | First NativeHarness (Uniswap v4 PoolManager + IHooks + Keccak + Foundry stub). `uniswap_v4: harness_built` |
| `fbd275c` | C2 | MeasuredImpactOracle + Foundry fork probe + first on-chain slot0 delta. `uniswap_v4: ready`, `ready_count=1`, evidence JSON written |

The 04:00 cron now resumes automatically. The next thing it does is run
the legacy `pick_next_target` selector in `bounty_loop.py`, which (per
audit defect **D5**) returns the same 9-12 saturated programs every
cycle. C3 stops that loop from enqueueing targets that don't have a
native substrate AND walks the full live registry rather than curated 28.

**Repo state at session start**:

- pytest baseline: `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` -> **479 passed, 6 skipped**
- native manifest: `data/security_results/loop/native_harness_status.json` -> `uniswap_v4: ready`, `ready_count=1`
- evidence file: `data/security_results/impact/uniswap_v4_measured_delta.json` (gitignored)
- platform intel: `platform sync` -> 208 Immunefi + 52 Cantina (large registry); curated set is 28.
- co-located targets in scope (from Cantina slates): `uniswap, reserve-protocol, euler, polymarket, coinbase, morpho, pendle, okx, paxos`
- Uniswap v4 source at `sources/uniswap_v4/repo` @ `46c6834698c48bc4a463a86d8420f4eb1d7f3b75`

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — sections **D5** (self-saturating loop),
   **D1** (28-of-249 scope), **D7** (cron concentration), **C3** + **C5**
   + **C7**, "What does not need to change" (gates/trust/RSI are correct;
   the picker is upstream of the gates).
2. `SPEC.md` §3 (Current Shipped Baseline) and §1 (acceptance contract).
   §4 (root-cause audit) is historical pre-pivot context.
3. `AUDIT.md` — "Current v5 Gaps" table near the bottom. The two entries
   you must close:
   - "Loop precondition guard / C3 audit — `pick_next_target` should
     refuse slugs without populated `concrete_candidates.jsonl` and
     harness entry"
   - "Fork_reproduced label split" (deferred to C7, ship minimal
     evidence-path split in this session; full label rewrite is later)
4. `CHANGELOG.md` — read both 2026-06-19 entries (the C1 NativeHarness and
   the C2 MeasuredImpactOracle) so you do not duplicate them.
5. `data/security_results/lab_notebook/2026-06-19-uniswap-v4-measured-oracle.md`
   — the lab notebook you are building on top of. The "Out of scope" and
   "Next session" sections at the bottom describe the next agent's
   charter.
6. `AGENTS.md` — Day Shift on the Cantina slate. The cron is resumed at
   04:00, your session is the picker side.
7. `src/night_shift_security/bounty/loop.py` — specifically
   `pick_next_target`, `_pick_investigation_targets`, and
   `_maybe_mark_saturated`. Read each, understand the saturation
   contract before changing.
8. `src/night_shift_security/platform/scope_registry.py` and
   `platform/intel_registry.py` — the registry that should be walked in
   C5, not the 28-curated set.

**Do NOT re-read**:

- `tests/test_api.py` (sandbox socket restrictions)
- The Satellite / Solodit / AuditVault corpus (advisory-only, no C3
  relationship)
- The native/harness Pro / native/Keccak reams (`native/uniswap_v4.py`
  is reference only; C3 adds a manifest reader, not harness code).

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean except `goal-reference.md`, `solodit-api-ref.md` (user-owned; ignore) |
| Last commit | `fbd275c` | pushed |
| Pytest baseline | `tests/ ignore test_api.py` | **479 passed, 6 skipped** |
| Native manifest | `native_harness_status.json` | `uniswap_v4: ready`, `ready_count=1` |
| Evidence file | `impact/uniswap_v4_measured_delta.json` | gitignored, present |
| Cron bootstrap | `hermes/scripts/nss-hipif-chain.sh` | `NSS_HIPIF_PAUSE_FOR_NATIVE=1` still default; gate releases when ready_count>=1 (verified C2) |
| Legacy synthetic engine | `domain/attack_templates/*.py`, `core/hypothesis.py` | unchanged — leave alone |
| Trust boundary | `validation/submission_gates.py`, `validation/evidence_grading.py`, `validation/novel_gate.py` | unchanged — do NOT loosen |
| Tests | `tests/test_bounty_loop.py`, `tests/test_immunefi_investigate.py`, `tests/test_cantina_scan.py`, `tests/test_structural_filters.py`, `tests/test_platform_v330.py` | these are the C3 targets |

`git status --porcelain` at session open. Anything beyond the two
untracked notes is unexpected. If `ready_count != 1`, **stop and ask**;
the precondition gate has been lost.

---

## 4. The goal of YOUR session

Ship audit corrections **C3** (mandatory), **C5** (mandatory), **C7**
(minimal). At session end:

1. **`pick_next_target` honors the native-harness manifest.**
   - A slug whose `data/security_results/loop/native_harness_status.json`
     entry is missing OR `status in {missing, mapped}` is **refused**
     with a typed `PickRefused` exception or equivalent (do not
     silently skip; the loop caller must surface it).
   - A slug whose entry is `harness_built` is allowed but emits a
     warning ("running with unmeasured harness"); this preserves v5's
     "at least one ready" cron gate.
   - A slug whose entry is `ready` (and the entry's
     `measured_delta_count > 0`) is preferred.

2. **C5: walk the full live registry** (`platform/scope_registry.json`,
   not the 28-curated set). The picker returns the highest-priority
   `pick_next_target` candidate from the union of:
   - Cantina slates (current 9 slugs)
   - Immunefi Tier-A programs (currently 6 programs: jito, layerzero,
     gmx, sky, onre, uniswap)
   - Active NativeHarness-ready entries (one today: uniswap_v4)
   The picker prioritizes **(high_bounty_usd * bounty_multiplier)`** where
   `bounty_multiplier` is 0 for `ready`/2x for `harness_built`/0.25 for
   `missing` so the legacy analogue path doesn't terminate the queue.

3. **`_maybe_mark_saturated` honors measured-delta escape** (C4). A
   target stays unsaturated if at least one finding has
   `fork_evidence.evidence_kind == "measured_impact_oracle.v1"` and
   `delta.tokens[*].delta_raw_units > 0` OR
   `delta.pool_slots[*].sqrt_price_x96_delta != "0"` (the slot0 case
   shipped in C2). The audit explicitly asks for this gap.

4. **C7: minimal fork_reproduced label split** in the run-summary:
   - `fork_reproduced_catalog_anchor` (running count of catalog-only
     repros)
   - `fork_reproduced_live_program` (running count of repros against a
     program from the live registry)
   - `fork_reproduced_value_moving` (repros whose evidence indicates
     a non-zero token-unit OR slot0 delta)
   - `fork_reproduced_novel` (repros whose finding has a novel
     candidate_schema_version >= 4)
   The legacy `fork_reproduced` field remains the sum (so existing
   consumers don't break), but the four labelled counters are added.

5. **Tests**:
   - `tests/test_pick_next_target.py` (NEW): covers refusal when
     native manifest missing, preference when ready, fallback to
     harness_built with a warning.
   - `tests/test_full_registry_walk.py` (NEW): covers C5 — at least
     30 distinct slugs in the picker set when registry is full.
     Uses a synthetic fixture builder (do not depend on live registry
     sockets).
   - `tests/test_saturation_measured_escape.py` (NEW): covers C4 — a
     non-saturated target with a measured-delta finding.
   - Existing `tests/test_bounty_loop.py` and friends must remain
     green.
   - **At least 4 new tests, none requiring live RPC.**

6. **`native mark --status paused`** is NOT what you use; if a target is
   in `paused`, treat it same as `harness_built`.

7. **Pytest baseline at end of session >= 479 / 6 skipped.**

8. **Lab notebook**: write
   `data/security_results/lab_notebook/2026-06-19-or-2026-06-20-v5-c3-pick-next-target.md`
   (today's date or your session's date).

9. **`AUDIT.md`** "Current v5 Gaps" table: strike the Loop precondition
   guard row, add C4 (saturation) and C7 (label split) as approved.
   Mention native cockwalk walks the full registry.

10. **`SPEC.md` §3** baseline line updated with the new test count.

11. **`CHANGELOG.md`**: add a third 2026-06-19 (or later) entry.

12. **Commit + push** to `main` with the suggested message below.

---

## 5. Hard constraints — DO NOT violate

- **Do NOT loosen `submission_gates.py`**. The gates are correct; you
  extend inputs only. If the picker needs an additional gate field
  (e.g. `must_be_native_pinned=True`), add it as an opt-in not
  required-by-default.
- **Do NOT touch the synthetic substrate**. The legacy
  `domain/attack_templates/*.py` and the param-grid engine are kept for
  regression fixtures per audit §"What does not need to change".
- **Do NOT add new packages**. `pyproject.toml` unchanged. `urllib` and
  stdlib only.
- **Do NOT remove existing tests**. If you re-flavor a behavior in
  `bounty/loop.py`, keep a unit test path for the previous
  keys (`pick_investigation_targets` count, sort order) and add new
  ones for the new keys.
- **Do NOT paste any `ALCHEMY_API_KEY`, `ETHEREUM_RPC_URL`, or
  private-key material** into the staged files. The audit
  explicitly forbids new secrets in commits; canonical ABI addresses
  (USDC, WETH, PoolManager, StateView) ARE OK and have been
  used since C1.
- **Do NOT edit `nss-hipif-chain.sh`**. The cracker "edit the cron"
  trap is real. Test the gate behaviour via the embedded python
  heredoc directly; do not modify the script.

---

## 6. Detailed playbook

### Step 6.1 — Read the existing `pick_next_target` and friends

```bash
ls src/night_shift_security/bounty/
cat src/night_shift_security/bounty/loop.py | grep -n -A3 "def pick_next_target\|def _pick_investigation_targets\|def _maybe_mark_saturated\|def run_bounty_loop"
```

Then read those four functions in full. Confirm the saturation
contract:

- today: a target is saturated if **all** findings are `catalog_analogue==True`,
- after C3+C4: same, **OR** the target has zero native-harness entry.

### Step 6.2 — Implement the native-harness precondition

Add a small module `src/night_shift_security/bounty/native_picker.py`
with:

```python
class PickRefused(RuntimeError):
    """Raised when ``pick_next_target`` cannot find a valid candidate."""

class NativeStatusIncomplete(PickRefused):
    """Raised when the candidate slug lacks a ``ready`` native-harness entry."""


def filter_native_ready(slugs, *, manifest_path=None) -> list[str]:
    """Return the subset of slugs whose native-harness status is ``ready``.

    If ``manifest_path`` is missing or empty, every slug is refused
    (the cron has not been seeded with any harness yet)."""

def has_measured_delta(slug, *, knowledge_path=None) -> bool:
    """Return True if the candidate store draws a measured delta on
    this slug or if the impact-json evidence file has a positive delta
    for this slug."""
```

The picker uses these two helpers in `pick_next_target` (which currently
returns slugs via `_pick_investigation_targets`). Wrap the existing
function so the call sites stay the same:

```python
def pick_next_target(*, prefer_full_registry=True) -> str | None:
    candidates = _pick_investigation_targets(prefer_full_registry=prefer_full_registry)
    ready = filter_native_ready(candidates)
    if ready:
        return ready[0]
    # Fallback: at least one with harness_built
    for slug in candidates:
        status = native_status_of(slug)
        if status in {"harness_built", "ready"}:
            return slug
    raise NativeStatusIncomplete("no native-ready target found")
```

Mock/stub the new module; do not invoke it from the cron chain until
the unit tests pass.

### Step 6.3 — Walk the full registry (C5)

Read `src/night_shift_security/platform/scope_registry.py` — the
registry that holds 208 + 52 = 260 live slugs vs the
`IMMUNEFI_PROGRAMS` / `CANTINA_PROGRAMS` curated 28. The picker must
merge the curated set (Cantina slates + Tier-A) with the *live*,
non-deposit, non-zero-TV set from `scope_registry.json`. If
`scope_registry.json` is stale, the picker may fall back to curated
+ cron-budget to detect the gap (this is the audit recommendation).

Implement:

```python
def list_pickable_slugs(*, include_full_registry=True, max_slugs=64):
    out = []
    out.extend(CANTINA_SLA_TES)        # existing curated
    out.extend(IMMUNEFI_TIER_A)         # existing curated
    if include_full_registry:
        if scope_registry_path.is_file():
            out.extend(load_scope_registry_paths())
    dedup + cap at max_slugs
    return out
```

The `pick_investigation_targets` callers should be ergonomically
unaffected; only the *size and shape* of the candidate pool change.

### Step 6.4 — Saturation measured-delta escape (C4)

`_maybe_mark_saturated(target, findings)` in `bounty/loop.py`. Add an
escape clause:

```python
def _has_measured_delta_finding(findings):
    for f in findings:
        ev = getattr(f, "fork_evidence", {}) or {}
        if ev.get("evidence_kind") == "measured_impact_oracle.v1":
            delta = ev.get("on_chain_state_diff") or ev.get("delta") or {}
            if (
                int(ev.get("token_delta") or 0) > 0
                or int(delta.get("sqrt_price_x96_delta") or 0) != 0
            ):
                return True
    return False

def _maybe_mark_saturated(target, findings):
    if _all_findings_catalog_analogue(findings) and not _has_measured_delta_finding(findings):
        targets.add(target)
```

### Step 6.5 — `fork_reproduced` label split (C7)

In the run-summary recorder (likely `bounty/loop.py:_record_run`),
add four counters alongside `fork_reproduced`:

```python
labels = {
    "fork_reproduced_catalog_anchor": 0,
    "fork_reproduced_live_program": 0,
    "fork_reproduced_value_moving": 0,
    "fork_reproduced_novel": 0,
}
for f in run.findings:
    if not getattr(f, "fork_reproduced", False): continue
    labels["fork_reproduced"] += 1
    if is_catalog_anchor(f): labels["fork_reproduced_catalog_anchor"] += 1
    if is_live_program(f):   labels["fork_reproduced_live_program"] += 1
    if is_value_moving(f):   labels["fork_reproduced_value_moving"] += 1
    if is_novel(f):          labels["fork_reproduced_novel"] += 1
```

`is_catalog_anchor(f)` = `f.catalog_analogue` *or* `f.method == "catalog_fallback"`.
`is_live_program(f)` = `f.target_id` derives from `scope_registry.json`
(not a curated-only entry). `is_value_moving(f)` =
`f.fork_evidence.evidence_kind == "measured_impact_oracle.v1"`.
`is_novel(f)` = `f.candidate_schema_version >= 4 and not f.catalog_analogue`.

These labels are aliases: the legacy `fork_reproduced` count is the sum
of the four new labels. **Do not change the value** of any existing
field; additively add labels.

### Step 6.6 — Tests

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
```

Pre-pickup: **479 / 6 skipped**. Post-pickup: **>= 483 / 6 skipped**.

Add files (at minimum):

- `tests/test_pick_next_target.py` — at least 4 cases:
  - empty manifest -> PickRefused
  - missing slugs -> NativeStatusIncomplete
  - one ready slug -> returns it
  - harmonic priority (ready over harness_built over missing)
- `tests/test_full_registry_walk.py` — at least 2 cases:
  - matches `CANTINA_SLA_TES`+`IMMUNEFI_TIER_A` union when scope registry absent
  - exceeds 30 when full `scope_registry.json` fixture is loaded
- `tests/test_saturation_measured_escape.py` — at least 2 cases:
  - target with all-analogue + no measured-delta -> saturated
  - target with all-analogue + measured-delta -> **not** saturated
- `tests/test_fork_repro_labels.py` — at least 2 cases:
  - mixed finding -> labels sum to legacy `fork_reproduced`
  - value-moving label matches only measured_impact_oracle.v1 findings

Use synthetic finding fixtures; do not depend on live RPC. No external
network calls.

### Step 6.7 — Verify cron resume semantics

The 04:00 cron is already resumed because `ready_count=1`. So the
follow-up win is: the cron now picks better targets via the
`pick_next_target` filter. Verify by simulating the picker invocation:

```bash
.venv/bin/python -c "from night_shift_security.bounty.loop import pick_next_target; \
  print(pick_next_target())"
```

It should return a slug from the live registry, NOT just `uniswap` if a
lower-Tier target has a ready harness. Today there's only one ready
target, but `pick_next_target` must still produce **something** proper
on the current state.

### Step 6.8 — Lab notebook + commit

Write the lab entry. Update AUDIT.md / SPEC.md / CHANGELOG.md as in
§4 above.

```bash
git status --porcelain                     # only your staged files
git add -A                                 # audit posture: stage everything
                                            # not user-untracked
git diff --cached | grep -E "API_KEY|SECRET|TOKEN|PRIVATE_KEY" \
    || echo "no secrets"                    # audit; redaction-safe
git commit -m "SPEC 5.0.0 pick_next_target native-harness precondition + label split (audit C3+C4+C7)"
git push origin main
```

Droid-Shield may flag canonical mainnet addresses (USDC, WETH,
PoolManager, StateView) as potential secrets — those are public
deployed addresses and are intentional in source. Commit may or may
not run in Droid; if Droid refuses, produce the same commit-message
above and run `git commit` from the user's terminal.

---

## 7. Anti-patterns to avoid

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Replacing the synthetic templates with the new native picker | Audit §"What does not need to change" + AUDIT.md `synthetic substrate` removal is **deferred**, not "in this session" |
| Adding a registry re-pull API call to the picker | The cron already runs `platform sync` first; do not duplicate. The picker reads from disk. |
| "Skip" instead of refuse for missing native manifest | Audit D5 explicitly says the loop self-saturates by skipping silently; refusing forces the operator to see the gap. |
| Loosening `qualifies_for_submission()` | Forbids. The C3 picker produces better candidates; the gate still decides truth. |
| Hard-coding slugs in `pick_next_target` | Defeats C5 (full registry). Even if registry absent today, the helper must support a fixture. |
| Changing the legacy `fork_reproduced` semantics | Add labels only. Existing dashboard/alerts rely on the count. |
| Mark-and-pausing the only ready target | That re-locks the cron gate. |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except two untracked notes
- [ ] `git log --oneline -3` shows `fbd275c` + C2 lab commit
- [ ] `cat SPEC.md | head -10` -> `5.0.0-draft`
- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q`
      -> **479 passed, 6 skipped**
- [ ] `native status` -> `uniswap_v4: ready`, `ready_count=1`
- [ ] `cat data/security_results/loop/native_harness_status.json`
      records `measured_delta_count` etc. (NOT required; absent OK)
- [ ] `find sources -maxdepth 2 -type d` shows
      `sources/wormhole/repo`, `sources/kamino/klend`,
      `sources/auditvault/repo`, `sources/uniswap_v4/repo`

### Closing (10 min)

- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q`
      -> **>= 483 / 6 skipped**
- [ ] `.venv/bin/python -c "from night_shift_security.bounty.loop import pick_next_target; print(pick_next_target())"`
      -> a slug (the picker MUST return *something*, not `None`; if the
      picker raises `NativeStatusIncomplete` because no `ready` targets,
      re-check the integration)
- [ ] preview one manual cron invocation won't crash:
      ```bash
      NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=1 \
        bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -5
      ```
      (do NOT let it go past the gate; OK to see "Proceeding..." in the
      forward log line).
- [ ] Lab entry written, named
      `2026-06-XX-v5-c3-pick-next-target.md`.
- [ ] AUDIT.md / SPEC.md / CHANGELOG.md reflect C3 work.
- [ ] `git status --porcelain` clean except user notes.
- [ ] Push to `origin main`.

---

## 9. If you hit a blocker

- **`pick_next_target` raises** `NativeStatusIncomplete` after the
  patch: that is the *desired* behavior per spec; document it and
  unblock by running `platform auditvault-sync` (or your equivalent)
  to seed the registry. **Do not** silently downgrade the picker to
  return `None` on missing manifests; that's the audit's exact
  failure pattern.

- **`pytest` drops below 479**: something you changed in
  `bounty/loop.py` or `bounty/native_picker.py` broke an existing
  test. Revert the change and re-plan in narrower increments.

- **The cron script times out at the precondition check** when you run
  it locally: the script's `git pull` is slow on big repos. Wrap the
  call in `timeout 30 bash ...` for a smoke run only.

- **`fork_reproduced` totals in lab notebook show 0**: confirm the
  legacy count field name has not been renamed. Built-in regression
  tests assert field name parity.

- **`platform sync` is too slow or fails**: skip the live registry
  walk in this session; mergethe curated-only fallback in step 6.3.
  The full registry walk lives behind `prefer_full_registry=True` and
  is independent of this picker path. C3 still ships.

- **Droid-Shield refuses the commit**: this happens in C2 due to a
  false positive on a canonical USDC address. If that happens here,
  stop the in-tool commit and instruct the user to commit manually
  in their terminal.

---

## 10. Files this session is expected to touch

```
src/night_shift_security/bounty/native_picker.py        (new)
src/night_shift_security/bounty/loop.py                 (small patches: pick_next_target, _maybe_mark_saturated, _record_run)
src/night_shift_security/platform/scope_registry.py     (read-only browse; possibly small helper if the loader is duplicated)
tests/test_pick_next_target.py                          (new)
tests/test_full_registry_walk.py                        (new)
tests/test_saturation_measured_escape.py                (new)
tests/test_fork_repro_labels.py                         (new)
data/security_results/lab_notebook/2026-06-XX-v5-c3-pick-next-target.md (new)
AUDIT.md                                                (small edit — Current v5 Gaps)
SPEC.md                                                 (small edit — Baseline line)
CHANGELOG.md                                            (2026-06-19 third entry or 2026-06-20 first entry)
```

---

## 11. Final word

Stay narrow. Ship C3 + C4 + C5 (mandatory) and C7 (minimal). The audit
named these three corrections explicitly as the path to making the v5
loop pick the right target instead of running the same 9-12 saturated
programs forever.

The minimum-viable-v5 has now been crossed (C2's `ready`). The next
agent-session cascading from this one will scale to the next five
targets (Aave v3 / Morpho Blue / Pendle PT / Compound v3 / Euler v2)
once the picker reliably identifies them. Get there before broadening.

If the session ends with no live-target pick, that is **fine** —
document the picker behaviour, ship the tests and the manifest
read-protocol, and let the next session finish wiring the cron to
its output. A tight, well-tested picker beats a broken pick with
labels.

### Suggested commit message (one line)

```
SPEC 5.0.0 pick_next_target native-harness precondition + label split (audit C3+C4+C7)
```

### Suggested commit message (descriptive)

```
SPEC 5.0.0 pick_next_target native-harness precondition + label split (audit C3+C4+C7)

- src/night_shift_security/bounty/native_picker.py: filter_native_ready, has_measured_delta, PickRefused, NativeStatusIncomplete; reads manifest + impact evidence files.
- src/night_shift_security/bounty/loop.py: pick_next_target honors native-harness manifest, refuses missing/mapped slugs, prefers ready; _maybe_mark_saturated honors measured-delta escape (audit C4); _record_run adds fork_reproduced_{catalog_anchor,live_program,value_moving,novel} label split (audit C7) without changing the legacy counter.
- src/night_shift_security/platform/scope_registry.py: optional helper for full-registry walk (audit C5).
- tests: test_pick_next_target.py, test_full_registry_walk.py, test_saturation_measured_escape.py, test_fork_repro_labels.py (>= 4 new tests, none requiring live RPC).
- AUDIT.md / SPEC.md / CHANGELOG.md updated. Lab notebook added.
- Tests: >= 483 passed, 6 skipped (was 479 / 6 skipped).
- native manifest still uniswap_v4: ready, ready_count=1 (cron gate intact).
```
