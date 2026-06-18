# SPEC + handover — Night Shift Security v5 Phase 3 row 1 delta capture + Phase 4 rotation + Aave v3 skeleton — fresh agent pickup

**Paste this entire document into your next session as context.**

You are a fresh agent. The previous three sessions shipped audit corrections
C1 + C2 + C3 + C4 + C5 + C6 + C7 of the v5 pivot (`SYSTEM_AUDIT_2026-06-18.md`):

- C1: First NativeHarness (Uniswap v4).
- C2: MeasuredImpactOracle + first on-chain slot0 delta -> `uniswap_v4: ready`.
- C3+C4+C5+C7: Picker precondition gate, full live registry walker, fork_reproduced label split.
- C6: fork_validation ABI/IDL bind on top-N binder.
- Phase 3 row 1: Morpho Blue harness at `harness_built` (no measured delta yet).

Commit history:

| Commit | Phase | What shipped |
|--------|-------|--------------|
| 018ee06 | v5 pivot | SPEC 5.0.0-draft — NativeHarness substrate gate |
| 1c09485 | C1 | First NativeHarness (Uniswap v4 PoolManager + IHooks + Foundry stub) |
| fbd275c | C2 | MeasuredImpactOracle + Foundry fork probe + first on-chain slot0 delta |
| 415d057 | C3+C4+C5+C7 | Picker precondition gate (refuse missing/mapped), full live registry walk helpers, measured-delta escape, fork_reproduced label split |
| cf5a5bb | handover | C3 handover replaced by C6+cron+Morpho spec for next agent |
| 95b5b79 | C6 + Phase 3 row 1 | `_has_native_bind` + Morpho Blue NativeHarness (harness_built); cron `bounty_depth()` flips `NSS_PREFER_FULL_REGISTRY=1`; **537 passed, 6 skipped** (+31 net) |

Your job is to:

1. **Capture a Morpho Blue measured delta on a live RPC fork** so the harness reaches `ready`. This is the **canonical Phase 3 row 1 close-out**.
2. **Ship Phase 4 refresh-14d rotation**: a `phase4_rotation_enabled` opt-in flag wired into `pick_next_target` so cold, well-harnessed programs float to the top of the queue.
3. **Wire `NSS_PREFER_FULL_REGISTRY=1` into `depth_env()`** so `hunt_rotation`, `refinement_passes`, and `wormhole_core_bridge_refinement` honour C5 (the previous agent only flipped the env var inside `bounty_depth(...)` — a narrow blast-radius the cron chain still misses outside that single function).
4. **Start Phase 3 row 2 — Aave v3 harness skeleton** (no measured delta in this session; just the harness file, foundry stub, semantic recon, and `harness_built` registration).

Hard constraints intact from `SYSTEM_AUDIT_2026-06-18.md` §"What does not need to change":
no synthetic substrate edits, no submission-gate loosening, no new packages,
no `nss-hipif-chain.sh` edits. Keep the trust boundary authoritative.

---

## 1. Where we are at session start

- `git status --porcelain` clean except `goal-reference.md` + `solodit-api-ref.md` (user-owned; ignore).
- Last commit: `95b5b79` (C6 + Morpho Blue harness_built; pushed).
- `git log --oneline -1` = `95b5b79 SPEC 5.0.0 fork_validation ABI/IDL bind + Morpho Blue harness start (audit C6 + Phase 3 row 1)`.
- Pytest: `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` -> **537 passed, 6 skipped** (+31 net since C3+C4+C5+C7).
- Native manifest `data/security_results/loop/native_harness_status.json`:
  - `uniswap_v4`: status=`ready`, contract=`0x000000000004444c5dc75cB358380D2e3dE08A90`, source_commit=`46c6834698c48bc4a463a86d8420f4eb1d7f3b75`.
  - `morpho_blue`: status=`harness_built`, contract=`0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD`, source_commit=`55d2d99304fb3fb930c688462ae2ccabb1d533ad` (v1.0.0).
  - `ready_count=1`.
- Sources cloned: `sources/{auditvault,kamino,uniswap_v4,wormhole, morpho}/repo` (morpho is new, gitignored).
- Evidence files in `data/security_results/impact/` (gitignored):
  - `uniswap_v4_measured_delta.json` (`measured-oracle.v1`, slot0 init).
  - **No `morpho_blue_measured_delta.json` yet — that's the gap this session closes.**
- Cron bootstrap (`hermes/scripts/nss-hipif-chain.sh`): `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default. Releases when `ready_count>=1`, currently true.
- Bounty loop caller (anchor of the cron-flip review): `src/night_shift_security/orchestration/bounty_loop.run_loop_iteration` reads `NSS_PREFER_FULL_REGISTRY` and passes it to `pick_next_target`. **Only `bounty_depth(...)` in `nss-hipif-chain-run.py` sets the env var to `1`** — `hunt_rotation`, `refinement_passes`, and `wormhole_core_bridge_refinement` still use `depth_env()` which omits it. That is the gap Step 6.2 closes.

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — focus on D3 (impact oracle), Phase 4 refresh-14d rotation language, and the "Phase 3 scale" table.
2. `SPEC.md` §3 (baseline) and §26-31 (Implementation Status). Confirm the test count is **537 / 6 skipped**.
3. `AUDIT.md` "Current v5 Gaps" — confirm C6 is shipped, Morpho row exists, Aave v3 + Phase 4 still pending.
4. `CHANGELOG.md` — read the **latest 2026-06-19 entries** (the C6+Morpho entry from `95b5b79` and the prior C1+C2 entries) so you do not duplicate work.
5. `data/security_results/lab_notebook/2026-06-18-v5-c3-pick-next-target.md` (C3 lab entry, historical) and `2026-06-19-hipif-bounty-depth-run.md` (cron run summary, if present).
6. `src/night_shift_security/native/morpho_blue.py` — the harness you extend with a measured-delta probe. Public surface: `selectors()`, `signatures()`, `load_abi()`, `resolve_market(market_params, rpc_url, block=…)`, `MarketParams`, `MarketResolution`.
7. `src/night_shift_security/impact/measured_oracle.py` — `MeasureSpec`, `compute_pre_state`, `compute_post_state`, `delta()`, `build_evidence_envelope`, `write_evidence`. Mirror the Uniswap v4 evidence file (`data/security_results/impact/uniswap_v4_measured_delta.json`) for Morpho Blue's `impact/morpho_blue_measured_delta.json`.
8. `hermes/scripts/nss-hipif-chain-run.py` — confirm `depth_env()` (the function that wraps every iteration's environment) and locate `bounty_depth(...)` where the previous agent printed `NSS_PREFER_FULL_REGISTRY=1` only locally.
9. `src/night_shift_security/bounty/native_picker.py` — `rank_pickable_slugs` + `bounty_priority_score` are the surface Phase 4 rotation will wrap.
10. `src/night_shift_security/validation/fork_validation.py` — `_has_native_bind` is now the C6 binder; do not regress it.
11. `src/night_shift_security/native/uniswap_v4.py` — the canonical NativeHarness template (already has a slot0 measured-delta probe; use it as the proof of capture).

**Do NOT re-read**:

- `tests/test_api.py` (sandbox socket restrictions).
- Solodit / AuditVault corpus (advisory-only beyond lineage stamping).
- The full Synthetic substrate under `domain/attack_templates/` (kept for regression fixtures only — never wired into Phase 3 row 1 or Phase 4).

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean except user-owned notes |
| Last commit | `95b5b79` | pushed |
| Pytest baseline | `tests/ --ignore=tests/test_api.py` | **537 passed, 6 skipped** |
| Native manifest | `native_harness_status.json` | `uniswap_v4: ready`, `morpho_blue: harness_built`, `ready_count=1` |
| Evidence file (Uniswap) | `impact/uniswap_v4_measured_delta.json` | gitignored, present |
| Evidence file (Morpho) | `impact/morpho_blue_measured_delta.json` | NOT YET PRESENT — ship it in this session |
| Cron bootstrap | `hermes/scripts/nss-hipif-chain.sh` | `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default; gate releases when `ready_count=1` |
| Synthetic substrate | `domain/attack_templates/*.py`, `core/hypothesis.py`, `parameter_spaces.py` | UNTOUCHED — regression fixtures per audit |
| Trust boundary | `validation/submission_gates.py`, `validation/evidence_grading.py`, `validation/novel_gate.py`, `validation/task_verifier.py` | UNTOUCHED — do NOT loosen |

If pytest drops below **537 / 6 skipped**, stop and revert. If `ready_count` ever drops below 1, stop and ask (cron gate has been lost).

---

## 4. The goal of YOUR session

Ship the **Morpho Blue measured-delta capture** (mandatory, the priority),
the **Phase 4 rotation wrapper** (mandatory, opt-in flag default off),
the **`depth_env()` env-var widening** (mandatory, closes the
narrow-blast-radius gap), and **start the Aave v3 skeleton** (mandatory,
no measured delta required, `harness_built` is fine).

At session end:

1. **`data/security_results/impact/morpho_blue_measured_delta.json` exists** with `schema_version=measured-oracle.v1` and a positive delta in token-unit OR slot0/totalSupply/totalBorrow terms against live RPC. Either:
   - **Scenario A (preferred)**: produce a real on-chain state-change on a deployed Morpho Blue market (e.g. `accrueInterest` on USDC/WETH produces observable totalSupplyAssets/totalBorrowAssets change between blocks), OR
   - **Scenario B (fallback)**: capture `market(bytes32)` before/after a sanity block on an existing USDC/WETH market (canonical Morpho Blue market ID pre-published on Morpho subgraph or via `morpholink`. Mirror the Uniswap v4 slot0-init pattern: zero token delta is honest, but the oracle envelope MUST record the address + marketId + block pre/post so the manifest later marks it `ready=False` only if we confirmed zero economic delta AND no value moving probe. The recurrence of `morpho_blue` moving to `ready` requires a **positive** `measured_impact_oracle.v1` delta — Scenario A preferred.)
   - `native mark --slug morpho_blue --status ready --notes "<delta summary>"` after capture, ONLY IF positive measured delta obtained.

2. **`bounty/native_picker.pick_next_target_v6_phase4`** is shipped behind a `NSS_PHASE4_ROTATION_ENABLED` (default off) flag. The wrapper records `state["last_touched"][slug] = now.isoformat()` whenever the picker successfully selects a slug, then on next selection ranks by `(max_bounty_usd * state_multiplier) / max(days_since_touched, 1)`. The function remains **opt-in**: when the env var is unset (cron default), `pick_next_target` path stays unchanged so every existing test stays green. Add 3+ tests:
   - cold programs float above warm ones of equal bounty;
   - rotation is no-op when env var is unset;
   - `last_touched` is populated by every successful pick.

3. **`hermes/scripts/nss-hipif-chain-run.py`** widens `depth_env()` (or the equivalent env-construction helper) so `NSS_PREFER_FULL_REGISTRY=1` is the **default** for the whole bounty-depth chain. Today only `bounty_depth(...)` sets it locally; `hunt_rotation`, `refinement_passes`, `wormhole_core_bridge_refinement` still rely on `depth_env()` and bypass C5. Lines: `hunt_rotation` (`def hunt_rotation(...)`), `refinement_passes` (similar shape), `wormhole_core_bridge_refinement` (similar). Add a single regression test (`tests/test_cron_registry_flip.py` extended) that monkey-patches these functions and asserts each calls `run_loop_iteration` with the C5 env set, OR asserts the env var is set when each function runs `depth_env()`.

4. **Aave v3 skeleton** is built using the `native/morpho_blue.py` + `native/uniswap_v4.py` templates:
   - `sources/aave_v3/repo` cloned (`git clone https://github.com/aave/aave-v3-core sources/aave_v3/repo`); pin to the latest stable release tag at clone time, record sha.
   - `native/aave_v3.py` exports `selectors()` (Pool `supply`, `borrow`, `repay`, `withdraw`, `flashLoan`, `liquidationCall`), `signatures()`, `load_abi()`, `resolve_pool(asset_address)`, `Pool`, `PoolResolution`. Stub market resolver over `IPoolDataProvider.getReserveData(asset)` (canonical Aave v3 helper).
   - `foundry/test/AaveV3Harness.t.sol` Foundry stub (parity test, asserts bytecode size of `PoolAddressesProvider` + `Pool` on Ethereum mainnet at "latest"). `forge build --force` must compile.
   - `.venv/bin/python -m night_shift_security.cli.main semantic map --slug aave_v3 --repo sources/aave_v3/repo --kind lending` produces ≥ 50 concrete candidates.
   - `.venv/bin/python -m night_shift_security.cli.main native mark --slug aave_v3 --status harness_built --contract-address <Pool mainnet address> --source-commit <pinned sha>`.

5. **Tests**: ≥ 14 new tests:
   - `tests/test_phase4_rotation.py` ≥ 3 cases.
   - `tests/test_cron_registry_flip.py` (extend) ≥ 2 cases.
   - `tests/test_native_aave_v3.py` ≥ 4 cases.
   - `tests/test_measured_oracle.py` (extend with Morpho Blue evidence round-trip) ≥ 1 case.
   - `tests/test_fork_validation_abi_idl.py` regression test must remain green.
   All no live RPC, except the optional `forge test` lives behind `pytest.importorskip("subprocess")` and an env-flagged subprocess cache.

6. **Pytest** baseline at session end: ≥ 551 / 6 skipped.

7. **Lab notebook** — write `data/security_results/lab_notebook/2026-06-XX-v5-measured-delta-phase4.md` with the next-session contract + closing audit bookkeeping (this is you — you are picking up the document you are reading). Today's `2026-06-19-v5-c6-cron-morpho.md` lab entry stays as historical reference and is not deleted.

8. **`AUDIT.md`** — strike the "Phase 3 second: Aave v3" row from pending into `harness_built`. Add `morpho_blue: ready` (or `harness_built` if Scenario B fallback). Add a Phase 4 row noting `pick_next_target_v6_phase4` shipped as opt-in.

9. **`SPEC.md` §3** baseline test count updated.

10. **`CHANGELOG.md`** — add a `2026-06-XX — v5 Morpho Blue measured delta + Phase 4 rotation opt-in + Aave v3 skeleton (audit Phase 3 row 1 close-out + Phase 4 partial)` entry.

11. **Commit + push** to `main` with the suggested message below.


---

## 5. Hard constraints — DO NOT violate

- **Do NOT loosen `submission_gates.py` / `evidence_grading.py` / `novel_gate.py` / `task_verifier.py`.** Dead-ends metric families (catalog replay, triage-only, fee-only, fake-positive) must remain rejected. If Phase 4 rotation needs an extra gate field, it is opt-in.
- **Do NOT touch the synthetic substrate.** `domain/attack_templates/*`, `core/hypothesis.py`, `parameter_spaces.py` are kept for regression fixtures per audit §"What does not need to change".
- **Do NOT add new packages.** urllib + stdlib. Pure-Python Keccak lives in `crypto/__init__.py`.
- **Do NOT remove existing tests.** Keep `tests/test_pick_next_target_*`, `tests/test_fork_validation_abi_idl.py`, `tests/test_native_morpho_blue.py`, and `tests/test_cron_registry_flip.py` green.
- **Do NOT paste API keys** (`ALCHEMY_API_KEY`, `ETHEREUM_RPC_URL`, private keys). Canonical Ethereum addresses (USDC, WETH, PoolManager, StateView, Morpho Blue, Aave v3 PoolAddressesProvider) ARE OK.
- **Do NOT edit `nss-hipif-chain.sh`.** It only sets `NSS_HIPIF_PAUSE_FOR_NATIVE`. Test via the python runner directly.
- **Do NOT mark `morpho_blue` as `ready` without a positive `measured_impact_oracle.v1` delta.** Audit C2's contract is non-negotiable: positive token-unit delta OR non-trivial slot0/pool-state change captured against live state. If only zero-delta evidence is captured, leave status at `harness_built` and document the absence.
- **Do NOT silently flip `NSS_PHASE4_ROTATION_ENABLED` to true by default.** The env var default is unset / `0`. Cron experimental runner must opt-in explicitly. The blast radius is small enough that the next 2 sessions can decide whether to flip.
- **Do NOT widen `depth_env()` such that bounty-depth always-on is mandatory in dryrun mode.** Always-on is fine; dryrun must remain harmless.

---

## 6. Detailed playbook

### Step 6.1 — Morpho Blue measured-delta capture

Reference path: the previous session shipped `src/night_shift_security/impact/measured_oracle.py` (+ Uniswap v4 proof `data/security_results/impact/uniswap_v4_measured_delta.json`) and `foundry/test/UniV4Measure.t.sol` (+ `scripts/_capture_measurement_json.py`).

Your steps:

1. **Pick a real Morpho Blue market** with published metadata. The Morpho Blue official subgraph or `@morpho-org/vault` repository documents canonical markets. Recommended: **USDC/WETH market on Ethereum mainnet** with a known IRM (e.g. Adaptive IRM at 0x87596F75DE0d9Bbc04a989e0f59b64Ad42DD0B61E... look it up via `morpholink` or subgraph before capture).
2. **Write `foundry/test/MorphoBlueMeasure.t.sol`**:
   - `vm.createSelectFork(ethRpcUrl, preBlock)` for the pre-state block, then `vm.createSelectFork(ethRpcUrl, postBlock)` for the post-state block ~5–20 blocks later on Ethereum mainnet.
   - Bind `morpho_blue_addr = 0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD`.
   - Compute the market ID via `keccak256(abi.encode(MarketParams))` (Morpho Blue canonical).
   - Read `market(Id)` for both blocks (`totalSupplyAssets`, `totalBorrowAssets` and the rest of the 6 uint128 fields).
   - Optional: read `position(Id, attacker)` for an attacker interaction.
   - Strategy A (preferred): a deliberately broken `accrueInterest` call by an attacker doesn't accrue OR moves state in an unintended way; capture the pre/post diff. Reading `market(Id)` after waiting several blocks naturally gives a non-zero delta (interest accrual). Strategy A is "do nothing, read across blocks" — the simplest and most honest path.
3. **Write `scripts/_capture_morpho_measurement.py`** mirroring `scripts/_capture_measurement_json.py`:
   - Runs `forge test --match-path test/MorphoBlueMeasure.t.sol -vv`.
   - Parses forge output for pre/post market state markers.
   - Calls `measured_oracle.build_evidence_envelope(spec=..., pre=..., post=...)` then `write_evidence("morpho_blue_measured_delta.json")`.
4. **Smoke & capture**:
   ```bash
   ETHEREUM_RPC_URL=<your mainnet RPC> .venv/bin/python scripts/_capture_morpho_measurement.py
   ```
   The result must be a `data/security_results/impact/morpho_blue_measured_delta.json` envelope. If the delta is `>= MEASURED_DELTA_THRESHOLD (10**6)`, the oracle stamps `measured_impact: true`; else `measured_impact: false` (negative-result honesty). Either way the manifest record proves the harness is exercisable against live state.
5. **Update manifest**:
   ```bash
   .venv/bin/python -m night_shift_security.cli.main native mark \
     --slug morpho_blue \
     --status ready --or-status harness_built \
     --notes "Phase 3 row 1 measured delta: <delta summary>" \
     --contract-address 0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD \
     --source-commit 55d2d99304fb3fb930c688462ae2ccabb1d533ad
   ```
   ONLY use `ready` if positive measured delta observed — audit C2 contract.
6. **Add the Morpho Blue evidence round-trip test to `tests/test_measured_oracle.py`** with criteria that re-uses the recorded JSON without external RPC.

### Step 6.2 — Phase 4 rotation (opt-in flag default off)

Reference paths: `bounty/native_picker.py` (`pick_native_ready_or_raise`, `rank_pickable_slugs`, `bounty_priority_score`) and `orchestration/bounty_loop.run_loop_iteration` (the canonical place that calls `pick_next_target`).

Design:

```python
def pick_next_target_v6_phase4(
    scan_report,
    state,
    *,
    cooldown_hours: float = 12.0,
    rotation_window_days: int = 14,
    prefer_full_registry: bool = True,
    manifest_path=None,
    scope_registry_path=None,
    raise_on_empty: bool = False,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Phase 4 ranker — cold programs float, all gated by native_harness_status."""
    ...


def rotate_target(state: dict[str, Any], slug: str, *, now: datetime | None = None) -> None:
    """Phase 4 — record when a slug was last touched so the rotation ranker
    correctly floats cold programs to the top."""
    state.setdefault("last_touched", {})[slug] = (now or datetime.now(timezone.utc)).isoformat()
```

The flag is read at module import or in a helper:

```python
def phase4_rotation_enabled() -> bool:
    return os.environ.get("NSS_PHASE4_ROTATION_ENABLED", "").strip().lower() in ("1", "true", "yes")


def pick_next_target(
    scan_report, state, *,
    prefer_full_registry=False, manifest_path=None, scope_registry_path=None,
    raise_on_empty=False,
):
    if phase4_rotation_enabled():
        chosen = pick_next_target_v6_phase4(...)
    else:
        chosen = _pick_next_target_legacy(...)
    if chosen:
        rotate_target(state, chosen["slug"])
    return chosen
```

This keeps the **default** path unchanged (Phase 4 dead unless explicitly enabled).

Tests:

- `test_cold_program_floats`: two slugs equal bounty, A is cold, B was touched yesterday; assert A returned first.
- `test_rotation_off_no_op`: env unset, behaviour equals legacy pick_next_target.
- `test_last_touched_updated`: a successful pick populates `state["last_touched"][slug]`.

### Step 6.3 — Widen `NSS_PREFER_FULL_REGISTRY` to `depth_env()`

Locate `depth_env(base=None, *, runner=None)` in `hermes/scripts/nss-hipif-chain-run.py:104-110`. Today it sets `NSS_HIPIF_BOUNTY_DEPTH=1` and `NSS_KLEND_FIXTURE=0`. The previous agent only added the C5 flag inside `bounty_depth(...)`, which means `hunt_rotation`, `refinement_passes`, and `wormhole_core_bridge_refinement` all use `depth_env()` and bypass C5.

Change:

```python
def depth_env(base=None, *, runner=None):
    env = dict(base or os.environ)
    env["NSS_HIPIF_BOUNTY_DEPTH"] = "1"
    env.setdefault("NSS_KLEND_FIXTURE", "0")
    # C5 wired at the chain-wide depth level — was conditionally
    # set only inside bounty_depth() in commit 95b5b79. Widened here
    # so hunt_rotation, refinement_passes, and the wormhole bridge
    # pass honour C5 too.
    env["NSS_PREFER_FULL_REGISTRY"] = "1"
    if runner:
        env["NSS_HIPIF_RUNNER"] = runner
    elif os.environ.get("NSS_HIPIF_RUNNER"):
        env["NSS_HIPIF_RUNNER"] = os.environ["NSS_HIPIF_RUNNER"]
    return env
```

Then **remove** the redundant `env["NSS_PREFER_FULL_REGISTRY"] = "1"` line from `bounty_depth(...)` (it was the duplicate).

Regression test: extend `tests/test_cron_registry_flip.py` with two new cases:
- `test_depth_env_sets_prefer_full_registry`: import `depth_env`, call with no args; assert `env["NSS_PREFER_FULL_REGISTRY"] == "1"`.
- `test_hunt_rotation_uses_depth_env`: monkey-patch `nss-hipif-chain-run.hunt_rotation` or inspect helpers; assert the env it constructs sets the C5 flag.

### Step 6.4 — Aave v3 skeleton (Phase 3 row 2)

Template = `src/night_shift_security/native/morpho_blue.py`. Steps mirror the Phase 3 row 1 process:

1. **Clone + pin**:
   ```bash
   git clone https://github.com/aave/aave-v3-core sources/aave_v3/repo
   git -C sources/aave_v3/repo checkout <pinned-stable-tag-commit>
   ```
   Use the latest stable release; record sha.
2. **`native/aave_v3.py`** with shape:
   - `HARNESS_TARGET = "aave_v3"`, `HARNESS_PLATFORM = "cantina"`, `HARNESS_CHAIN = "ethereum"`, `HARNESS_NAME = "Aave v3"`.
   - `DEFAULT_POOL_ADDRESSES_PROVIDER = <canonical Aave v3 mainnet>`.
   - `DEFAULT_POOL = <canonical Aave v3 Pool mainnet>`.
   - `selectors()` returning at minimum:
     - `Pool.supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` returning `0x617ba037` (or keccak256 of full sig).
     - `Pool.borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` (`0xa415bcad`).
     - `Pool.repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf)` (`0xaf198920`).
     - `Pool.withdraw(address asset, uint256 amount, address to)` (`0x69328dec`).
     - `Pool.flashLoan(...)` (`0xab9c4b5d`).
     - `Pool.liquidationCall(address collateral, address debt, address user, uint256 debtToCover, bool receiveAToken)` (`0x00a718ef`).
     - `PoolDataProvider.getReserveData(address asset)` (`0x35ea6a75`).
   - `signatures()`, `load_abi()` (mirror Morpho pattern: try artifact; fall back to inline canonical fragments).
   - `resolve_pool(asset_address, rpc_url, block='latest')`: eth_getCode on Pool; eth_call `getReserveData(asset)`; return a small `ReserveResolution` dataclass (mirrors `MarketResolution`).
3. **`foundry/test/AaveV3Harness.t.sol`** — Foundry stub asserting bytecode size of `PoolAddressesProvider` + `Pool` on Ethereum mainnet at "latest" via `vm.createSelectFork`. Compile with `forge build --force`; no remappings required.
4. **Semantic recon**:
   ```bash
   .venv/bin/python -m night_shift_security.cli.main semantic map \
     --slug aave_v3 --repo sources/aave_v3/repo --kind lending
   ```
   Promote ≥ 50 concrete candidates.
5. **`native mark`**:
   ```bash
   .venv/bin/python -m night_shift_security.cli.main native mark \
     --slug aave_v3 --status harness_built \
     --contract-address <Pool mainnet> --source-commit <pinned sha>
   ```
6. **Tests** (`tests/test_native_aave_v3.py`):
   - selector keccak parity for ≥ 6 functions.
   - signature hash returns the canonical selector lengths.
   - load_abi returns the inline canonical fallback (when no artifact).
   - resolve_pool mocked with urllib-replayed JSON-RPC returns the expected reserve resolution.

### Step 6.5 — Verification

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
```

Pre-pickup: **537 / 6 skipped**. Post-pickup: ≥ **551 / 6 skipped**.

Cron smoke (`dryrun` mode):

```bash
NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1 \
  timeout 60 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -12
```

The bootstrap header must reflect:
- `pause_for_native=0` (you overrode it for dryrun),
- `bounty_depth=1`,
- the chain either runs to `chain_status=complete` within the timeout, or prints a benign "no uninvestigated targets" notice (acceptable in dryrun when NO RUN state is current).


---

## 7. Anti-patterns to avoid

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Marking `morpho_blue: ready` with zero-delta evidence | Audit C2's contract is explicit — `ready` requires a positive measured delta. Zero-delta evidence stays `harness_built`; the next agent captures the value-moving probe |
| Skipping the morpholink / subgraph market lookup and hardcoding a market ID | Morpho Blue market IDs are `keccak256(abi.encode(MarketParams))`; the wrong ID returns `market(bytes32)` with zero-state (looks like a fresh market). Use the canonical market for the canonical USDC/WETH or WETH/USDC IRM |
| Flipping `NSS_PHASE4_ROTATION_ENABLED=1` by default | Until the operator opts in, the cron must behave identically to today. Phase 4 rotation can surprise saturation rules if cold programs float faster than expected |
| Widening `depth_env()` without checking `NSS_HIPIF_RUNNER` paths | `bounty_depth()` already overrides the env var locally; if you keep the duplicate, it stays a valid no-op but the next agent will wonder |
| Adding Aave v3 vault / GHO / lido-restaking protocols to the same harness | Aave v3 core is one harness; its satellite protocols get separate harnesses. Mixing them keeps `native_harness_status.json` opaque |
| Loosening `qualifies_for_submission()` to accept Morpho Blue on `harness_built` | The gate is correct; Pas won. Morpho Blue earns `submit_ready` the same way Uniswap v4 must: real on-chain delta captured against live state |
| Running Phase 4 by default on the production cron | Phase 4 is opt-in. Rolling it into production before the rotation rules are audited invites surprise saturation drift |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except user-owned notes (`goal-reference.md`, `solodit-api-ref.md`)
- [ ] `git log --oneline -3` shows `95b5b79` (C6 + Morpho), `cf5a5bb` (handover), `415d057` (C3+C4+C5+C7)
- [ ] `head SPEC.md` -> `5.0.0-draft`
- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> **537 passed, 6 skipped**
- [ ] `native status` -> uniswap_v4: ready, morpho_blue: harness_built, ready_count=1
- [ ] `find sources -maxdepth 2 -type d` shows auditvault, kamino, uniswap_v4, wormhole, plus `morpho` (already cloned)
- [ ] `ls data/security_results/impact/` shows `uniswap_v4_measured_delta.json`; the morpho entry is the gap

### Closing (10 min)

- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> ≥ **551 / 6 skipped**
- [ ] `data/security_results/impact/morpho_blue_measured_delta.json` exists with `schema_version=measured-oracle.v1`
- [ ] Either `native status` lists `morpho_blue: ready` (positive delta observed) OR the lab entry explains why it stays `harness_built`
- [ ] `pick_next_target_v6_phase4` exists in `bounty/native_picker.py` behind `NSS_PHASE4_ROTATION_ENABLED` default off
- [ ] `depth_env()` in `hermes/scripts/nss-hipif-chain-run.py` sets `NSS_PREFER_FULL_REGISTRY=1` (no longer just `bounty_depth()`)
- [ ] `native status` lists `aave_v3: harness_built`
- [ ] `concrete_candidates.jsonl` grew by ≥ 50 Morpho Blue AND ≥ 50 Aave v3 candidates
- [ ] Lab entry written, named `2026-06-XX-v5-measured-delta-phase4.md`
- [ ] AUDIT.md closed out Morpho Blue row + added Aave v3 row + Phase 4 row
- [ ] SPEC.md §3 baseline test count updated
- [ ] CHANGELOG.md 2026-06-XX entry added
- [ ] `git status --porcelain` clean except user notes
- [ ] Push to `origin main`

---

## 9. Blockers playbook

- **No `ETHEREUM_RPC_URL` for Morpho Blue capture**: the capture is RPC-gated. Document the gap explicitly in the lab entry; ship the harness_built status with a fresh `morpho_blue_measured_delta.json` zero-delta envelope pointing at "RPC unavailable". This is honest negative-result evidence per audit C2. The next agent with RPC access captures the live delta.
- **Morpho Blue market ID inconsistency across documents**: always recompute via `keccak256(abi.encode(MarketParams))` from the source repo. Never hardcode from a stale subgraph snapshot.
- **Aave v3 source repo is large / slow clone**: shallow-clone is fine for harness purposes; `git clone --depth 1 ...` with the latest stable tag. Pin sha after clone.
- **`pick_next_target_v6_phase4` ranked by `days_since_touched` divides by zero**: in the wrapper, default to `max(days, 1)`. Add the regression test asserting the divisor is never zero.
- **`forge test --match-path test/MorphoBlueMeasure.t.sol` fails on a missing remapping**: keep the Morpho Blue capture test free of import paths from `sources/aave_v3/repo` or `sources/morpho/repo`; use only `solmate/` or inline cast if you need helpers.
- **Phase 4 rotation breaks the existing tests**: leave the env var unset during tests. The wrapper reads at invocation, not at import time, so the existing test surface stays unchanged.

---

## 10. Files this session is expected to touch

```
src/night_shift_security/native/morpho_blue.py                  (extend with reserve-style probe helpers if needed)
src/night_shift_security/native/aave_v3.py                      (new)
src/night_shift_security/bounty/native_picker.py                (Phase 4 opt-in wrapper)
foundry/test/MorphoBlueMeasure.t.sol                            (new — measured delta probe)
foundry/test/AaveV3Harness.t.sol                                (new — bytecode parity)
scripts/_capture_morpho_measurement.py                          (new — capture script)
hermes/scripts/nss-hipif-chain-run.py                           (widened depth_env)
sources/aave_v3/repo                                            (gitignored clone)
data/security_results/impact/morpho_blue_measured_delta.json    (new — envelope)
data/security_results/knowledge/concrete_candidates.jsonl       (extend ≥ 50 + 50 rows)
data/security_results/loop/native_harness_status.json           (Morpho ready or stays harness_built; +aave_v3 harness_built)
data/security_results/lab_notebook/2026-06-XX-v5-measured-delta-phase4.md (this file's new home)
tests/test_phase4_rotation.py                                   (new — ≥ 3 cases)
tests/test_cron_registry_flip.py                                (extend — ≥ 2 new cases)
tests/test_native_aave_v3.py                                    (new — ≥ 4 cases)
tests/test_measured_oracle.py                                   (extend — ≥ 1 case)
AUDIT.md                                                        (close Morpho + add Aave + Phase 4)
SPEC.md                                                         (§3 test count + new status line)
CHANGELOG.md                                                    (2026-06-XX entry)
```

---

## 11. Final word

Stay narrow. Ship the **Morpho Blue measured-delta capture first** (it's the canonical Phase 3 row 1 close-out), then the **Phase 4 rotation opt-in**, then the **`depth_env()` widening**, then **Aave v3 skeleton**. The order matters: validating Morpho Blue closes the v5 minimum-viable-protocol loop (one measured delta per pass), everything else widens.

If session ends with `morpho_blue` still `harness_built` because no RPC was available, that is **fine** — the lab entry must document the gap honestly and the next agent with RPC access captures the value-moving probe. A tight Morpho Blue harness with a zero-delta honest envelope beats a binder that quietly marked `ready` without a real probe.

Phase 4 rotation is **opt-in**. Roll out only after the agent has eyeballed the cold/warm split on a single dryrun — the operator's judgement decides whether to flip `NSS_PHASE4_ROTATION_ENABLED=1` on the 04:00 cron or keep it experimental.

Aave v3 is the **next payment-card target** for Phase 3. The skeleton plus ≥ 50 candidates puts the manifest one live-delta away from `ready`. Take Phase 3 row 2 in the same shape as row 1: ABI/IDL bind + semantic recon + Foundry stub + harness + manifest mark. Repeat for the next 3 (Pendle, Compound v3, Euler v2) over the following sessions.

If the next 5 sessions deliver:

| Session target | Native harness delta? |
|----------------|----------------------|
| **Now (today)**: Morpho Blue Measure + Phase 4 rotation + Aave v3 skeleton | best effort |
| +1 | Pendle PT skeleton |
| +2 | Compound v3 skeleton |
| +3 | Euler v2 skeleton |
| +4 | Three live deltas (one per major non-Uniswap), promoting 3 harnesses to ready |

...then `submit_ready` finally flips. The audit's "one week pivot" timeline is now realistic and Phase 4's rotation fades into normal cron business.

### Suggested commit message (one line)

```
SPEC 5.0.0 Morpho Blue measured-delta + Phase 4 rotation opt-in + Aave v3 skeleton
```

### Suggested commit message (descriptive)

```
SPEC 5.0.0 Morpho Blue measured-delta + Phase 4 rotation opt-in + Aave v3 skeleton

- data/security_results/impact/morpho_blue_measured_delta.json: live
  recorded delta via fork probe; if no RPC available, honest zero-delta
  envelope keeping morpho_blue at harness_built and explaining the gap.
- src/night_shift_security/native/morpho_blue.py: extension hooks to
  support a market-state pre/post read (if needed for tied or fallback
  capture paths).
- src/night_shift_security/bounty/native_picker.py: pick_next_target_v6_phase4
  + rotate_target; NSS_PHASE4_ROTATION_ENABLED opt-in flag default OFF;
  records state["last_touched"][slug] and ranks cold programs above
  warm equivalents.
- hermes/scripts/nss-hipif-chain-run.py: depth_env() now sets
  NSS_PREFER_FULL_REGISTRY=1 chain-wide (was narrow-blast-radius inside
  bounty_depth()); duplicated line in bounty_depth() removed.
- src/night_shift_security/native/aave_v3.py: Phase 3 row 2 skeleton
  mirroring the Morpho Blue template; selectors, ABI, market resolver
  using stdlib; Pool/PoolAddressesProvider canonical addresses on
  Ethereum mainnet.
- foundry/test/MorphoBlueMeasure.t.sol + foundry/test/AaveV3Harness.t.sol:
  parity + delta probes. forge build --force compiles both.
- sources/aave_v3/repo: pinned clone under sources/.
- data/security_results/loop/native_harness_status.json: morpho_blue
  ready or harness_built (per capture); aave_v3 joined at harness_built.
- tests: test_phase4_rotation.py (3), test_cron_registry_flip.py (+2),
  test_native_aave_v3.py (4), test_measured_oracle.py (+1).
- AUDIT.md: Modal Blue row closed, Aave v3 row added, Phase 4 row
  added.
- SPEC.md §3 test count updated.
- CHANGELOG.md: 2026-06-XX entry titled
  "v5 Morpho Blue measured delta + Phase 4 rotation opt-in + Aave v3
  skeleton (audit Phase 3 row 1 close-out + Phase 4 partial)".
- TESTS: ≥ 551 passed, 6 skipped (was 537 / 6; +14 net minimum).
- Native manifest still uniswap_v4: ready, ready_count=1; morpho_blue
  and aave_v3 added at appropriate status.
```
