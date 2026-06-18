# SPEC + handover — Night Shift Security v5 Phase 6: hunt rotation + depth expansion — fresh agent pickup

**Paste this entire document into your next session as context.**

You are a fresh agent. Five sequential sessions shipped the v5 audit corrections
C1 + C2 + C3 + C4 + C5 + C6 + C7 (`SYSTEM_AUDIT_2026-06-18.md`), the
Phase 3 row 1 close-out (Morpho Blue harness + honest zero-delta envelope),
and the Phase 3 row 2 close-out (Aave v3 harness + positive measured delta
→ `ready`). Phase 4 Option B (saturation guard) is shipped. All seven
audit corrections are now closed. `ready_count=2` (uniswap_v4 + aave_v3).

Current commit history:

| Commit | Phase | What shipped |
|--------|-------|--------------|
| 018ee06 | v5 pivot | SPEC 5.0.0-draft — NativeHarness substrate gate |
| 1c09485 | C1 | First NativeHarness (Uniswap v4 PoolManager + IHooks + Foundry stub) |
| fbd275c | C2 | MeasuredImpactOracle + Foundry fork probe + first on-chain slot0 delta |
| 415d057 | C3+C4+C5+C7 | Picker precondition gate, full live registry walk helpers, measured-delta escape, fork_reproduced label split |
| cf5a5bb | handover | C3 handover replaced by C6+cron+Morpho spec |
| 95b5b79 | C6 + Phase 3 row 1 | `_has_native_bind` + Morpho Blue NativeHarness (`harness_built`); `bounty_depth()` flips `NSS_PREFER_FULL_REGISTRY=1`; 537 / 6 skipped |
| 0d17789 | handover | C6+Morpho handover replaced by measured-delta-phase4 spec |
| b33a34b | Phase 3 row 1 close-out + row 2 skeleton | Morpho honest zero-delta, Phase 4 rotation opt-in (8 tests), `depth_env()` widening (2 tests), Aave v3 skeleton (17 tests); 568 / 6 skipped |
| cc3832a | handover | measured-delta-phase4 handover replaced |
| b3f0f32 | Phase 5 | Aave v3 positive measured delta → `ready`, Phase 4 Option B saturation guard, 26 net new tests; 594 / 6 skipped |

Your job is to advance the v5 NativeHarness substrate from "two ready harnesses" toward "ready to run the cron with real targets." The system has two ready harnesses (uniswap_v4 + aave_v3) and one honest zero-delta (morpho_blue). The 04:00 cron is paused (`NSS_HIPIF_PAUSE_FOR_NATIVE=1`). You must decide whether to unpause the cron with the two ready targets, or build the next harness first.

---

## 1. Current state at session start

- `git status --porcelain` clean except `goal-reference.md` + `solodit-api-ref.md` (user-owned; ignore).
- Last commit: `b3f0f32` (Aave v3 measured delta + Phase 4 Option B; pushed).
- `git log --oneline -1` = `b3f0f32 v5 Phase 5: Aave v3 first measured delta + Phase 4 Option B saturation guard`.
- Pytest: `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` -> **594 passed, 6 skipped** (+26 net since b33a34b).
- Native manifest `data/security_results/loop/native_harness_status.json`:
  - `uniswap_v4`: `status=ready`, contract=`0x000000000004444c5dc75cB358380D2e3dE08A90`, source_commit intact (slot0 delta, payment-card canonical).
  - `morpho_blue`: `status=harness_built`, contract=`0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb`, source_commit `55d2d99304fb3fb930c688462ae2ccabb1d533ad` (v1.0.0).
  - `aave_v3`: `status=ready`, contract=`0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2`, source_commit `b74526a7` (v1.19.4).
  - `ready_count=2`.
- Sources cloned: `sources/{auditvault, kamino, uniswap_v4, wormhole, morpho, aave_v3}/repo`.
- Evidence files in `data/security_results/impact/` (gitignored):
  - `uniswap_v4_measured_delta.json` (positive slot0 init measurement).
  - `morpho_blue_measured_delta.json` (honest zero-delta envelope: market ID `0xb859…`, USDC/WETH no on-chain positions).
  - `aave_v3_measured_delta.json` (positive delta: liquidityIndex +1.56e21, variableBorrowIndex +2.02e21, isolationModeTotalDebt +252,930,327).
- `data/security_results/knowledge/concrete_candidates.jsonl` ≥ 50 Morpho Blue entries + ≥ 50 Aave v3 entries from the previous session.
- Cron bootstrap (`hermes/scripts/nss-hipif-chain.sh`): `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default; `depth_env(...)` sets `NSS_PREFER_FULL_REGISTRY=1` chain-wide.
- Phase 4 rotation: opt-in behind `NSS_PHASE4_ROTATION_ENABLED` (default off). Live in `bounty/native_picker.py`:
  - `phase4_rotation_enabled()` — reads `NSS_PHASE4_ROTATION_ENABLED` env var (default off).
  - `rotate_target(state, slug, *, now=None)` — records `state["last_touched"][slug] = now.isoformat()`.
  - `_days_since_last_touched(slug, state, *, now=None)` — returns float days.
  - `is_saturated_for_rotation(slug, state, *, now=None, window_days=14)` — returns True if candidate is `harness_built` and touched within `window_days`.
  - `pick_next_target_v6_phase4(...)` — score = `(bounty_usd * state_multiplier) * max(days_since_touched, 1)`, sorts descending, skips saturated-for-rotation.
- Wired into `bounty_loop.py` via `pick_next_target`: if `phase4_rotation_enabled()`, swaps to the v6_phase4 path; else legacy path. Calls `rotate_target(state, slug)` after a successful pick on either path.

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — focus on D5 (saturated_slugs + pick_investigation_targets lock the loop), D7 (cron architecture concentrates compute where there's no harness), and "Phase 4 — Reinstate the cron with new precondition gates."
2. `SPEC.md` §3 (baseline) and §26-31 (Implementation Status). Confirm baseline test count = **594 / 6 skipped**.
3. `AUDIT.md` "Current v5 Gaps" + v5 Pivot table. Confirm:
   - C3, C4, C5, C6, C7 are all closed.
   - Morpho Blue row: `harness_built`.
   - Aave v3 row: `ready`.
   - Phase 4 rotation row: shipped (Option B).
4. `CHANGELOG.md` — read **latest 2026-06-19 entries** for the previously-shipped `b3f0f32` work so you do not duplicate.
5. `data/security_results/lab_notebook/2026-06-19-HANDOVER-v5-real-delta-phase4-on.md` — the **previous session's handover** with Phase 5 lab addendum at top. Treat as the contract the previous agent honoured.
6. `src/night_shift_security/native/morpho_blue.py` — harness you exercise for value-moving probe. Public surface: `selectors()`, `signatures()`, `load_abi()`, `resolve_market(market_params, rpc_url, block=…)`, `MarketParams`, `MarketResolution`. It also has `expected_market_id(market_params)` for synthetic market-id derivation.
7. `src/night_shift_security/native/aave_v3.py` — Phase 3 row 2 harness. Public surface: `selectors()` (10 pool + 7 view + 2 provider), `signatures()`, `load_abi()`, `resolve_pool(asset_address)`, `Pool`, `PoolResolution`.
8. `src/night_shift_security/impact/measured_oracle.py` — `MeasureSpec`, `compute_pre_state`, `compute_post_state`, `delta()`, `build_evidence_envelope`, `write_evidence`. **Read this thoroughly** — both new probes depend on its predicates. Pay attention to `MEASURED_DELTA_THRESHOLD` and the `measured_impact: true|false` decision rule.
9. `src/night_shift_security/bounty/native_picker.py` — Phase 4 wrapper surface (`pick_next_target_v6_phase4`, `rotate_target`, `_days_since_last_touched`, `is_saturated_for_rotation`, `phase4_rotation_enabled`). Confirm `last_touched` is `state["last_touched"][slug]` and is auto-populated by `pick_next_target` after a successful selection.
10. `hermes/scripts/nss-hipif-chain-run.py` — locate `depth_env()`, `bounty_depth`, `hunt_rotation`, `refinement_passes`, `wormhole_core_bridge_refinement`. Confirm `NSS_PREFER_FULL_REGISTRY=1` is set chain-wide.
11. `data/security_results/impact/morpho_blue_measured_delta.json` — current zero-delta envelope.
12. `data/security_results/impact/aave_v3_measured_delta.json` — positive-delta evidence template.
13. `data/security_results/impact/uniswap_v4_measured_delta.json` — the proof-of-capture template.
14. `foundry/test/AaveV3Measure.t.sol` — positive-delta Foundry test (vm.createSelectFork).
15. `foundry/test/MorphoBlueMeasure.t.sol` — zero-delta Foundry test.
16. `scripts/_capture_aave_v3_measurement.py` — Aave v3 capture script.
17. `scripts/_capture_morpho_measurement.py` — Morpho Blue capture script.

**Do NOT re-read**:

- `tests/test_api.py` (sandbox socket restrictions).
- Solodit / AuditVault corpus (advisory-only).
- The synthetic substrate under `domain/attack_templates/` (kept for regression fixtures).

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean except user-owned notes |
| Last commit | `b3f0f32` | pushed |
| Pytest baseline | `tests/ --ignore=tests/test_api.py` | **594 passed, 6 skipped** |
| Native manifest | `native_harness_status.json` | uniswap_v4: ready; aave_v3: ready; morpho_blue: harness_built; ready_count=2 |
| Evidence (Uniswap) | `impact/uniswap_v4_measured_delta.json` | gitignored, present, positive |
| Evidence (Morpho) | `impact/morpho_blue_measured_delta.json` | gitignored, present, zero-delta honest envelope |
| Evidence (Aave v3) | `impact/aave_v3_measured_delta.json` | gitignored, present, positive |
| Cron bootstrap | `hermes/scripts/nss-hipif-chain.sh` | unchanged; `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default |
| Chain env | `depth_env()` in `nss-hipif-chain-run.py` | `NSS_PREFER_FULL_REGISTRY=1` set chain-wide |
| Phase 4 rotation | `bounty/native_picker.py` | Option B shipped (saturation guard); opt-in behind `NSS_PHASE4_ROTATION_ENABLED` |
| Synthetic substrate | `domain/attack_templates/*`, `core/hypothesis.py`, `parameter_spaces.py` | UNTOUCHED — regression fixtures |
| Trust boundary | `validation/submission_gates.py`, `validation/evidence_grading.py`, `validation/novel_gate.py`, `validation/task_verifier.py` | UNTOUCHED |

If pytest drops below **594 / 6 skipped**, stop and revert. If `ready_count` ever drops below 2, stop and ask — the cron pause gate depends on it.

---

## 4. The goal of YOUR session

| # | Goal | Mandatory? | Status at end |
|---|------|-----------|--------------|
| 1 | Decide: unpause cron with 2 ready targets OR build next harness first | YES, priority 1 | Decision recorded with rationale |
| 2 | If building next harness: Morpho Blue value-moving probe → `ready` | CONDITIONAL | morpho_blue ready OR harness_built with documented gap |
| 3 | If unpausing cron: dryrun validation of the chain with 2 ready targets | CONDITIONAL | dryrun succeeds or documented gap |
| 4 | Phase 4 rotation: enable `NSS_PHASE4_ROTATION_ENABLED=1` in cron config | NO, optional | Only after dryrun confirms cold/warm ordering |
| 5 | ≥ 14 net new tests | YES | ≥ 608 / 6 skipped |

At session end:

1. **Decision recorded** in AUDIT.md: either "cron unpaused with 2 ready targets" or "next harness built, cron stays paused." The decision must reference D5/D7 from `SYSTEM_AUDIT_2026-06-18.md`.

2. **If building Morpho Blue** (Option B from previous handover — find a market with active positions):
   - Find a Morpho Blue market with active positions (subgraph query or on-chain `morpho.idToMarketParams(...)`).
   - Extend `foundry/test/MorphoBlueMeasure.t.sol` to probe that market.
   - Overwrite `data/security_results/impact/morpho_blue_measured_delta.json` with fresh positive-delta capture.
   - Promote via:
     ```bash
     .venv/bin/python -m night_shift_security.cli.main native mark \
       --slug morpho_blue --status ready --or-status harness_built \
       --notes "Phase 3 row 1 promotion: <delta summary>" \
       --contract-address 0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb \
       --source-commit 55d2d99304fb3fb930c688462ae2ccabb1d533ad
     ```

3. **If unpausing cron** (Option A — cron with 2 ready targets):
   - Set `NSS_HIPIF_PAUSE_FOR_NATIVE=0` in the cron bootstrap or environment.
   - Run a single isolated dryrun:
     ```bash
     NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1 \
       timeout 90 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -20
     ```
   - Confirm the chain runs to `chain_status=complete` or "no uninvestigated targets" (acceptable in dryrun state).
   - Update `AGENTS.md` cron settings table to reflect the unpaused state.

4. **Phase 4 rotation enablement** (only after dryrun succeeds):
   - Add `NSS_PHASE4_ROTATION_ENABLED=1` to the cron line in `hermes/cron/jobs.example.yaml`.
   - Add regression test confirming the flag is set.

5. **Tests**: ≥ 14 net new tests:
   - If building Morpho Blue: `tests/test_morpho_value_moving.py` ≥ 4 cases (Morpho `accrueInterest` snapshot, capture round-trip, manifest promotion, fall-back when RPC unavailable).
   - If unpausing cron: `tests/test_cron_unpause.py` ≥ 4 cases (dryrun succeeds, manifest has ≥2 ready, pause gate respects env var, chain completes in dryrun).
   - `tests/test_measured_oracle.py` ≥ 3 new cases.
   - `tests/test_phase4_rotation_rollout.py` ≥ 3 new cases.
   All net new = ≥ 14. Baseline ≥ **608 / 6 skipped**.

6. **`AUDIT.md`** — update the Morpho Blue row or add cron unpausing row.

7. **`SPEC.md` §3** baseline test count updated.

8. **`CHANGELOG.md`** — add `2026-06-XX — v5 Phase 6: <what shipped>` entry.

9. **Lab notebook entry** — write `data/security_results/lab_notebook/2026-06-XX-v5-phase6-hunt-and-rotate.md` (the same file as this handover, with a 30-line "today's session" addendum at the top recording what landed).

10. **Commit + push** to `main` with the suggested message below.

---

## 5. Hard constraints — DO NOT violate

- **Do NOT loosen `submission_gates.py` / `evidence_grading.py` / `novel_gate.py` / `task_verifier.py`.** Dead-ends (catalog replay, triage-only, fee-only, fake-positive) must remain rejected. Capture a real on-chain delta; never a synthetic one.
- **Do NOT touch the synthetic substrate.** `domain/attack_templates/*`, `core/hypothesis.py`, `parameter_spaces.py` stay intact.
- **Do NOT add new packages.** urllib + stdlib. Pure-Python Keccak lives in `crypto/__init__.py`.
- **Do NOT remove existing tests.** Keep `tests/test_phase4_rotation.py` (8 cases), `tests/test_cron_registry_flip.py` (5 cases), `tests/test_native_aave_v3.py` (17 cases), `tests/test_native_morpho_blue.py` (21 cases), `tests/test_fork_validation_abi_idl.py` (8 cases), `tests/test_morpho_value_moving.py` (5 cases), `tests/test_aave_v3_measured_delta.py` (8 cases), `tests/test_phase4_rotation_rollout.py` (10 cases), and `tests/test_pick_next_target_*` green.
- **Do NOT paste API keys** (`ALCHEMY_API_KEY`, `ETHEREUM_RPC_URL`, private keys). Canonical addresses (USDC, WETH, PoolManager, StateView, Morpho Blue, Aave v3 PoolAddressesProvider, Aave v3 IPoolDataProvider) ARE OK.
- **Do NOT edit `nss-hipif-chain.sh`.** It only sets `NSS_HIPIF_PAUSE_FOR_NATIVE`.
- **Do NOT mark `morpho_blue` as `ready` without a positive `measured_impact_oracle.v1` delta.** Audit C2's contract is non-negotiable: status only flips when the oracle reports positive measured motion against live state. Zero-delta or missing-RPC stays `harness_built` with documented gap.
- **Do NOT silently flip `NSS_PHASE4_ROTATION_ENABLED=1` as a global default.** The decision is binary: enable the cron line **after a clean dryrun** (Option A) OR add a saturation-vs-rotation guard (Option B). Anything in between is opt-in only.
- **Do NOT widen the `depth_env()` C5 flag again.** It is already chain-wide per `b3f0f32`. Don't contradict this.
- **Do NOT unpause the cron (`NSS_HIPIF_PAUSE_FOR_NATIVE=0`) without a dryrun first.** The pause gate exists because D5/D7 showed the old cron ran the same 9-12 programs in a self-saturating loop. With only 2 ready targets, the cron will only probe uniswap_v4 + aave_v3 — this is the intended "discovery mode" per D7. But it must be validated via dryrun.

---

## 6. Detailed playbook

### Step 6.1 — Decision: unpause cron or build next harness?

Two viable paths. The decision depends on your assessment of D5/D7 risk with only 2 ready targets.

#### Path A: Unpause cron with 2 ready targets (recommended if dryrun succeeds)

Rationale: `SYSTEM_AUDIT_2026-06-18.md` D7 says "the cron should hand out one new target per nightly run." With 2 ready targets (uniswap_v4 + aave_v3), the cron will probe these two in the bounty-depth pass, which is the correct "discovery mode" — real targets, real forks, real deltas. This is better than waiting for a third harness because:
- The two ready targets already cover the two biggest Cantina/Immunefi pots (Uniswap $15.5M, Aave v3 is well-known).
- The cron's `platform sync` will refresh the registry each run, discovering new programs.
- The saturation guard (Phase 4 Option B) prevents re-touching recently probed targets.

Steps:
1. Run dryrun (see Step 6.4).
2. If dryrun succeeds: update `AGENTS.md` to reflect `NSS_HIPIF_PAUSE_FOR_NATIVE=0`.
3. Optionally enable Phase 4 rotation (`NSS_PHASE4_ROTATION_ENABLED=1`) in cron config after dryrun confirms cold/warm ordering.

#### Path B: Build Morpho Blue harness next (recommended if dryrun fails or you want 3 ready targets)

Rationale: Morpho Blue has a clean harness (`harness_built`) and is the canonical Phase 3 row 1. The previous agent could not find a liquid market because the subgraph was unreachable. This session can try:
- Query the Morpho Blue subgraph (`https://api.morpho.org/blue/v1/graphql`) for markets with `totalSupplyAssets_gt: "1000000"`.
- Use on-chain `morpho.idToMarketParams(...)` to find active markets.
- Pick the first market with active positions and probe `accrueInterest`.

Steps:
1. Find a liquid Morpho Blue market (see Step 6.2).
2. Extend `foundry/test/MorphoBlueMeasure.t.sol` to probe that market.
3. Capture positive delta → promote to `ready`.
4. Then unpause cron with 3 ready targets.

### Step 6.2 — Morpho Blue value-moving probe (if Path B)

The USDC/WETH market is empty. To exercise `accrueInterest` you need a market with at least one active position.

Two authoritative ways to find one:

- **The Morpho Blue subgraph** (hosted at `https://api.morpho.org/blue/v1/graphql` per Morpho documentation, public endpoint). Query: `query { markets(where: { totalSupplyAssets_gt: "1000000" }, first: 5) { id loanToken collateralToken totalSupplyAssets totalBorrowAssets } }`. Pick the first result with a non-zero state.
- **On-chain `morphoBlue.idToMarketParams(marketId)`**: iterate known market IDs from `data/security_results/knowledge/concrete_candidates.jsonl` and check `totalSupplyAssets > 0`.

If neither works (subgraph unreachable, all markets empty): keep `harness_built` with documented gap. Do NOT fabricate a positive delta.

The capture script `scripts/_capture_morpho_measurement.py` already parses forge output into `data/security_results/impact/morpho_blue_measured_delta.json`. Audit it:
- Does it round-trip forge output through `measured_oracle.build_evidence_envelope`?
- Does it honour `MEASURED_DELTA_THRESHOLD`?
- Does it gracefully fall back to the "RPC unavailable" branch?

If the **forge test runs** (RPC available), produce a fresh capture with positive delta → `morpho_blue: ready`.

If **RPC unavailable**, the lab entry must explicitly say so. **Default fallback** path: keep `harness_built`, append a §"RPC unavailable" note. **No sneaky promotion.**

### Step 6.3 — Aave v3 already `ready`

Aave v3 was promoted to `ready` in the previous session (b3f0f32). The positive-delta evidence is at `data/security_results/impact/aave_v3_measured_delta.json`. No further work needed on Aave v3 unless you want to probe a different asset (e.g. WETH, DAI).

### Step 6.4 — Cron dryrun (if Path A)

```bash
NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1 \
  timeout 90 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -20
```

The bootstrap header must reflect:
- `pause_for_native=0` (you overrode it for dryrun),
- `bounty_depth=1`,
- the chain either runs to `chain_status=complete` within the timeout, or prints a benign "no uninvestigated targets" notice (acceptable in dryrun state with only 2 ready targets).

If you rolled out Phase 4 rotation, also smoke-test with the flag on:
```bash
NSS_PHASE4_ROTATION_ENABLED=1 timeout 90 bash hermes/scripts/nss-hipif-chain.sh
```

### Step 6.5 — Verification

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
```

Pre-pickup: **594 / 6 skipped**. Post-pickup: ≥ **608 / 6 skipped**.

### Step 6.6 — Docs and commit

Update `AUDIT.md`, `SPEC.md` §3, `CHANGELOG.md`. Write lab addendum at top of this file. Commit + push.

---

## 7. Anti-patterns to avoid

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Unpausing cron without dryrun | D5/D7 showed the old cron ran the same 9-12 programs in a self-saturating loop. The dryrun validates that the chain works with the new native-harness gate |
| Marking `morpho_blue: ready` on USDC/WETH with no positions | Audit C2's contract is explicit — `ready` requires a positive measured delta. Pick a market with liquidity, or stay `harness_built` honestly |
| Waiting forever to build a third harness | The system has 2 ready targets. That's enough to start probing real protocols. Don't let perfect be the enemy of good |
| Flipping Phase 4 ON by default in code (not just cron YAML) | Whoever inherits the code base shouldn't be surprised. Rotation's behaviour in dryrun is documented; in production the cron line configures it |
| Importing `requests` / `httpx` / `web3` for the capture scripts | urllib + stdlib only. Pure-Python Keccak lives in `crypto/__init__.py`. These constraints exist for several reasons (no supply chain, easy replay) |
| Using the same RPC URL everywhere | Have a fallback for when `ETHEREUM_RPC_URL` is unset or 429s. The capture script should exit gracefully and write a `status=rpc-unavailable` envelope rather than crash |
| Forgetting to update the `last_touched` state between sessions | The Phase 4 ranker needs the timestamp. `rotate_target()` writes it after selection; subsequent picks see cold/warm ordering |
| Adding tests that import the `morpholink` Python package | It's a third-party npm package, not Python. The capture script uses urllib + raw ethers JSON-RPC |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except user notes (`goal-reference.md`, `solodit-api-ref.md`)
- [ ] `git log --oneline -3` shows `b3f0f32` (Aave v3 measured delta + Phase 4 Option B), `cc3832a` (handover replace), `b33a34b` (Phase 3 row 1 + row 2 skeleton)
- [ ] `head SPEC.md` -> `5.0.0-draft`
- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> **594 passed, 6 skipped**
- [ ] `native status` -> uniswap_v4: ready; aave_v3: ready; morpho_blue: harness_built; ready_count=2
- [ ] `find sources -maxdepth 1 -type d` -> auditvault, kamino, uniswap_v4, wormhole, morpho, aave_v3 (all present)
- [ ] `cat data/security_results/impact/aave_v3_measured_delta.json | head -5` -> positive-delta envelope visible
- [ ] `cat data/security_results/impact/morpho_blue_measured_delta.json | head -5` -> zero-delta honest envelope visible
- [ ] `cat data/security_results/impact/uniswap_v4_measured_delta.json | head -5` -> positive-delta envelope visible

### Closing (10 min)

- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> ≥ **608 / 6 skipped** (+14 net new minimum)
- [ ] Decision recorded in AUDIT.md: unpause cron with 2 ready targets OR build next harness
- [ ] If unpausing: dryrun succeeded (`chain_status=complete` or "no uninvestigated targets")
- [ ] If building Morpho Blue: `morpho_blue_measured_delta.json` overwritten with fresh positive-delta capture, OR explicit "RPC unavailable" branch documented in today's lab addendum
- [ ] `native status` reflects the new state
- [ ] Phase 4 rotation rollout decision recorded: either Option A cron YAML change OR existing Option B
- [ ] Lab addendum written: `2026-06-XX-v5-phase6-hunt-and-rotate.md` (the same file as this handover, with a 30-line addendum at the top recording what landed)
- [ ] `AUDIT.md` "Current v5 Gaps" updated
- [ ] `SPEC.md` §3 test count updated
- [ ] `CHANGELOG.md` 2026-06-XX entry added
- [ ] `git status --porcelain` clean except user notes
- [ ] Push to `origin main`

---

## 9. Blockers playbook

- **No `ETHEREUM_RPC_URL` for value-moving probes**: The probe scripts must gracefully fall back. Pre-existing evidence files were captured by the original sessions with a working RPC. If the new RPC is rate-limited or down, document in the lab addendum and exit gracefully (don't fake a delta). **The honest zero-delta fallback is the same envelope produced by `b33a34b`** — copy the structure verbatim.

- **Morpho Blue subgraph requires API key**: the public endpoint `https://api.morpho.org/blue/v1/graphql` does NOT require auth (per Morpho documentation as of 2026). If you hit a 401/403, write a fallback that uses on-chain `morpho.idToMarketParams(...)` per event log. Document the gap.

- **Aave v3 `lastUpdateTimestamp` doesn't move in the probe window**: this is normal for low-demand blocks. Aave v3 is already `ready` — no further work needed.

- **Phase 4 Option B saturation guard races with rotation ticking**: `is_saturated_for_rotation` reads `state["last_touched"][slug]`. If state is reset between sessions, all candidates look cold and the guard is a no-op. Document this in the function docstring.

- **Forge build complains about Solidity version**: Aave v3 and Morpho Blue both pin `pragma solidity ^0.8.20` or similar; match the version in your test files (look at the existing `UniV4Measure.t.sol` and `MorphoBlueMeasure.t.sol`).

- **Dryrun shows "no uninvestigated targets"**: This is acceptable with only 2 ready targets if they've already been probed. The cron's `platform sync` will refresh the registry and discover new programs. Document this as "ready to probe new targets on next run."

- **`bounty_depth()` overrides `phase4_rotation_enabled` env on launch**: it shouldn't, but check. If it does, accept it as the cron-line ownership (the cron YAML is the source of truth; `bounty_depth` is honouring the operator's choice).

---

## 10. Files this session is expected to touch

```
src/night_shift_security/native/morpho_blue.py                    (read-only inspection; extend only if probe needs helpers)
src/night_shift_security/impact/measured_oracle.py                (read-only inspection; predicates used by capture scripts)
src/night_shift_security/bounty/native_picker.py                  (read-only inspection; Phase 4 already shipped)
scripts/_capture_morpho_measurement.py                            (re-instrument for value-moving probe if Path B)
foundry/test/MorphoBlueMeasure.t.sol                              (extend if Path B)
data/security_results/impact/morpho_blue_measured_delta.json      (overwrite with new capture if Path B; OR keep existing zero-delta envelope + lab rationale)
data/security_results/loop/native_harness_status.json             (morpho_blue may flip ready if Path B)
hermes/cron/jobs.example.yaml                                     (Phase 4 Option A only: cron line updated)
AGENTS.md                                                          (cron unpausing or Phase 4 Option A)
tests/test_morpho_value_moving.py                                 (extend — ≥ 4 cases if Path B)
tests/test_cron_unpause.py                                        (new — ≥ 4 cases if Path A)
tests/test_measured_oracle.py                                     (extend — ≥ 3 cases)
tests/test_phase4_rotation_rollout.py                             (extend — ≥ 3 cases)
AUDIT.md                                                            (update Morpho Blue row or add cron unpausing row)
SPEC.md                                                             (§3 baseline test count)
CHANGELOG.md                                                        (2026-06-XX entry titled)
data/security_results/lab_notebook/2026-06-XX-v5-phase6-hunt-and-rotate.md  (this file's new home, with today's addendum at top)
```

---

## 11. Final word

Stay tight. The v5 audit corrections are all closed. You have two `ready` harnesses producing real on-chain deltas and one honest zero-delta `harness_built`. The system is ready to either unpause the cron and start probing real protocols, or build the third harness and triple the ready count.

Priority ordering for your day:

1. **Decision: unpause cron or build next harness?** — this is the session's primary deliverable. Both paths are valid; pick the one with the least risk.
2. **If Path A (unpause cron): dryrun validation** — run the chain with `NSS_HIPIF_PAUSE_FOR_NATIVE=0` and confirm it works.
3. **If Path B (build harness): Morpho Blue value-moving probe** — find a liquid market and capture positive delta.
4. **Phase 4 rotation enablement** — only after dryrun succeeds.
5. **Tests** — ≥ 14 net new to reach 608 / 6 skipped.

The agent is one **dryrun** away from unpausing the cron with real targets, or one **Morpho Blue accrueInterest** away from tripling the ready count. The protocols are accurate, the harnesses are tested, the foundation is solid. Pick the path with the least risk and ship it.

### Suggested commit message (one line)

```
SPEC 5.0.0 Phase 6: <unpause cron with 2 ready targets|next harness + dryrun>
```

### Suggested commit message (descriptive)

```
SPEC 5.0.0 Phase 6: <unpause cron with 2 ready targets|next harness + dryrun>

- AUDIT.md: <cron unpaused with uniswap_v4 + aave_v3|morpho_blue promoted to ready>
- data/security_results/loop/native_harness_status.json: <ready_count=2|ready_count=3>
- AGENTS.md: <NSS_HIPIF_PAUSE_FOR_NATIVE=0|Phase 4 rotation enabled>
- hermes/cron/jobs.example.yaml: <NSS_PHASE4_ROTATION_ENABLED=1 added|unchanged>
- data/security_results/impact/morpho_blue_measured_delta.json: <fresh positive-delta capture|kept zero-delta honest envelope>
- tests: <cron_unpause.py 4|Morpho value_moving 4> + <measured_oracle 3> + <phase4_rollout 3>
- AUDIT.md §3 baseline: ≥ 608 passed, 6 skipped (was 594 / 6; +14 net new minimum)
- CHANGELOG.md: 2026-06-XX entry titled "v5 Phase 6: <what shipped>"
```
