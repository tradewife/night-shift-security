# SPEC + handover — Night Shift Security v5 real value-moving delta + Phase 4 rotation rollout + Aave v3 first measured delta — fresh agent pickup

**Paste this entire document into your next session as context.**

You are a fresh agent. Four sequential sessions shipped the v5 audit corrections
C1 + C2 + C3 + C4 + C5 + C6 + C7 (`SYSTEM_AUDIT_2026-06-18.md`), the
Phase 3 row 1 close-out (Morpho Blue harness + honest zero-delta
envelope), and the Phase 3 row 2 skeleton (Aave v3 harness + Foundry
parity at live RPC). Phase 4 rotation is shipped opt-in. The C5
chain-wide env widening inside `depth_env()` is in place. All seven
audit corrections are now closed.

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

Your job is to:

1. **Capture a Morpho Blue value-moving probe** so the harness reaches `ready` — this is the **canonical Phase 3 row 1 promotion**. Audit C2's contract: a positive `measured_impact_oracle.v1` delta recorded against live RPC. The previous agent shipped an honest zero-delta envelope because the canonical USDC/WETH Morpho Blue market has no on-chain positions to probe. Your options:
   - **Option A (preferred):** exercise a real `accrueInterest` call via a deployed `IrmAdapter` (Adaptive IRM at `0x87596F75DE0d9Bbc04a989e0f59b64Ad42DD0B61E…` on Ethereum) on a market that *does* have liquidity (USDC/USDC stablecoin pair, WBTC/WETH, or pick a market with $>1 active position from the Morpho subgraph). Measure `market(bytes32)` before/after.
   - **Option B (fallback if Morpho Blue has no liquid markets):** capture a `market(bytes32)` pre/post snapshot around a known same-block liquidity event (morpho subgraph "supply events" stream) so we have evidence of motion. If still zero, document the gap.
2. **Capture the first Aave v3 measured delta** so the Aave v3 skeleton reaches `ready` (Phase 3 row 2 promotion). Audit C2 contract: positive `measured_impact_oracle.v1` delta. Easiest probe: snapshot `IPoolDataProvider.getReserveData(asset)` for the USDC reserve (block N vs N+K), capture the supplied `liquidityIndex` / `currentLiquidityRate` / `lastUpdateTimestamp` drift.
3. **Decide the Phase 4 rotation rollout** for the production cron. Today it's opt-in. Decide either: **(a)** enable `NSS_PHASE4_ROTATION_ENABLED=1` on the 04:00 cron after one dryrun validates cold/warm ordering, or **(b)** keep opt-in and add a **saturation-vs-rotation safety check** that prevents cold programs from floating onto a saturated slot. Either path keeps the trust boundary intact.

Hard constraints intact from `SYSTEM_AUDIT_2026-06-18.md` §"What does not need to change":
no synthetic substrate edits, no submission-gate loosening, no new
packages, no `nss-hipif-chain.sh` edits.

---

## 1. Current state at session start

- `git status --porcelain` clean except `goal-reference.md` + `solodit-api-ref.md` (user-owned; ignore).
- Last commit: `b33a34b` (Morpho honest delta + Phase 4 rotation + Aave v3 skeleton; pushed).
- `git log --oneline -1` = `b33a34b SPEC 5.0.0 Morpho Blue measured-delta + Phase 4 rotation opt-in + Aave v3 skeleton`.
- Pytest: `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` -> **568 passed, 6 skipped** (+31 net since C3+C4+C5+C7).
- Native manifest `data/security_results/loop/native_harness_status.json`:
  - `uniswap_v4`: `status=ready`, contract=`0x000000000004444c5dc75cB358380D2e3dE08A90`, source_commit intact (slot0 delta, payment-card canonical).
  - `morpho_blue`: `status=harness_built`, contract=`0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD`, source_commit `55d2d99304fb3fb930c688462ae2ccabb1d533ad` (v1.0.0).
  - `aave_v3`: `status=harness_built`, contract=`0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4e2` (canonical Ethereum mainnet Pool), source_commit `b74526a7` (v1.19.4).
  - `ready_count=1`.
- Sources cloned: `sources/{auditvault, kamino, uniswap_v4, wormhole, morpho, aave_v3}/repo`.
- Evidence files in `data/security_results/impact/` (gitignored):
  - `uniswap_v4_measured_delta.json` (positive slot0 init measurement).
  - `morpho_blue_measured_delta.json` (honest zero-delta envelope: market ID `0xb859…`, USDC/WETH no on-chain positions).
- `data/security_results/knowledge/concrete_candidates.jsonl` ≥ 50 Morpho Blue entries + ≥ 50 Aave v3 entries from the previous session.
- Cron bootstrap (`hermes/scripts/nss-hipif-chain.sh`): `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default; `depth_env(...)` now sets `NSS_PREFER_FULL_REGISTRY=1` chain-wide.
- Phase 4 rotation: opt-in behind `NSS_PHASE4_ROTATION_ENABLED` (default off). Live in `bounty/native_picker.py`:
  - `phase4_rotation_enabled` — env-var reader.
  - `rotate_target(state, slug, *, now=None)` — records `state["last_touched"][slug] = now.isoformat()`.
  - `_days_since_last_touched(slug, state, *, now=None)` — returns float days.
  - `pick_next_target_v6_phase4(...)` — score = `(bounty_usd * state_multiplier) * max(days_since_touched, 1)`, sorts descending.
- Wired into `bounty_loop.py` via `pick_next_target`: if `phase4_rotation_enabled()`, swaps to the v6_phase4 path; else legacy path. Calls `rotate_target(state, slug)` after a successful pick on either path (the previous agent confirmed `last_touched` is populated regardless of phase4 flag).

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — focus on D3 (impact oracle), the Phase 4 refresh-14d rotation language, and "Phase 3 scale".
2. `SPEC.md` §3 (baseline) and §26-31 (Implementation Status). Confirm baseline test count = **568 / 6 skipped**.
3. `AUDIT.md` "Current v5 Gaps" + v5 Pivot table. Confirm:
   - C3, C4, C5, C6, C7 are all closed.
   - Morpho Blue row: `harness_built`.
   - Aave v3 row: `harness_built`.
   - Phase 4 rotation row exists.
4. `CHANGELOG.md` — read **latest 2026-06-19 entry** for the previously-shipped `b33a34b` work so you do not duplicate. Also read the C6 entry under `95b5b79` for the `_has_native_bind` context.
5. `data/security_results/lab_notebook/2026-06-19-HANDOVER-v5-measured-delta-phase4.md` — the **previous session's charter**, now historical. Treat as the contract the previous agent honoured.
6. `data/security_results/lab_notebook/2026-06-18-v5-c3-pick-next-target.md` — historical lab entry for context.
7. `src/night_shift_security/native/morpho_blue.py` — harness you exercise for value-moving probe. Public surface: `selectors()`, `signatures()`, `load_abi()`, `resolve_market(market_params, rpc_url, block=…)`, `MarketParams`, `MarketResolution`. It also has `expected_market_id(market_params)` for synthetic market-id derivation.
8. `src/night_shift_security/native/aave_v3.py` — Phase 3 row 2 skeleton. Public surface: `selectors()` (10 pool + 7 view + 2 provider), `signatures()`, `load_abi()`, `resolve_pool(asset_address)`, `Pool`, `PoolResolution`. (**NB: confirm the actual public surface in the file** — the previous handover called this `PoolResolution`, your reading of the actual file will confirm the dataclass name.)
9. `src/night_shift_security/impact/measured_oracle.py` — `MeasureSpec`, `compute_pre_state`, `compute_post_state`, `delta()`, `build_evidence_envelope`, `write_evidence`. **Read this thoroughly** — both new probes depend on its predicates. Pay attention to `MEASURED_DELTA_THRESHOLD` and the `measured_impact: true|false` decision rule.
10. `src/night_shift_security/bounty/native_picker.py` — Phase 4 wrapper surface (`pick_next_target_v6_phase4`, `rotate_target`, `_days_since_last_touched`, `phase4_rotation_enabled`). Confirm `last_touched` is `state["last_touched"][slug]` and is auto-populated by `pick_next_target` after a successful selection.
11. `hermes/scripts/nss-hipif-chain-run.py` — locate `depth_env()`, `bounty_depth`, `hunt_rotation`, `refinement_passes`, `wormhole_core_bridge_refinement`. Confirm `NSS_PREFER_FULL_REGISTRY=1` is set chain-wide (no longer narrow-blast-radius).
12. `data/security_results/impact/morpho_blue_measured_delta.json` — current zero-delta envelope. Mirror its structure for the new captures.
13. `data/security_results/impact/uniswap_v4_measured_delta.json` — the proof-of-capture template you copy.

**Do NOT re-read**:

- `tests/test_api.py` (sandbox socket restrictions).
- Solodit / AuditVault corpus (advisory-only).
- The synthetic substrate under `domain/attack_templates/` (kept for regression fixtures).

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean except user-owned notes |
| Last commit | `b33a34b` | pushed |
| Pytest baseline | `tests/ --ignore=tests/test_api.py` | **568 passed, 6 skipped** |
| Native manifest | `native_harness_status.json` | uniswap_v4: ready; morpho_blue, aave_v3: harness_built; ready_count=1 |
| Evidence (Uniswap) | `impact/uniswap_v4_measured_delta.json` | gitignored, present, positive |
| Evidence (Morpho) | `impact/morpho_blue_measured_delta.json` | gitignored, present, zero-delta honest envelope |
| Evidence (Aave v3) | `impact/aave_v3_measured_delta.json` | NOT YET PRESENT — ship it in this session |
| Cron bootstrap | `hermes/scripts/nss-hipif-chain.sh` | unchanged; `NSS_HIPIF_PAUSE_FOR_NATIVE=1` default |
| Chain env | `depth_env()` in `nss-hipif-chain-run.py` | `NSS_PREFER_FULL_REGISTRY=1` set chain-wide (post C5 widening) |
| Phase 4 rotation | `bounty/native_picker.py` | opt-in behind `NSS_PHASE4_ROTATION_ENABLED` |
| Synthetic substrate | `domain/attack_templates/*`, `core/hypothesis.py`, `parameter_spaces.py` | UNTOUCHED — regression fixtures |
| Trust boundary | `validation/submission_gates.py`, `validation/evidence_grading.py`, `validation/novel_gate.py`, `validation/task_verifier.py` | UNTOUCHED |

If pytest drops below **568 / 6 skipped**, stop and revert. If `ready_count` ever drops below 1, stop and ask — the cron pause gate depends on it.

---

## 4. The goal of YOUR session

| # | Goal | Mandatory? | Status at end |
|---|------|-----------|--------------|
| 1 | Morpho Blue value-moving probe → `ready` | YES, priority 1 | morpjo_blue ready (positive delta) OR `harness_built` with documented gap |
| 2 | Aave v3 first measured delta → `ready` | YES, priority 2 | aave_v3 ready (positive delta) OR `harness_built` with documented gap |
| 3 | Phase 4 rotation rollout decision | YES, priority 3 | Either env-on-for-cron OR saturation-vs-rotation safety check |
| 4 | Pendle PT start (Phase 3 row 3 sketch) | NO, optional | Only if time allows |

At session end:

1. **`data/security_results/impact/morpho_blue_measured_delta.json`** is overwritten with a fresh positive-delta capture. If positive measured delta is observed, the manifest flips `morpho_blue: ready` via:
   ```bash
   .venv/bin/python -m night_shift_security.cli.main native mark \
     --slug morpho_blue --status ready --or-status harness_built \
     --notes "Phase 3 row 1 promotion: <delta summary>" \
     --contract-address 0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD \
     --source-commit 55d2d99304fb3fb930c688462ae2ccabb1d533ad
   ```

2. **`data/security_results/impact/aave_v3_measured_delta.json`** is created with a positive-delta `measured-oracle.v1` envelope (USDC reserve at block N vs N+K is the simplest probe). If positive measured delta:
   ```bash
   .venv/bin/python -m night_shift_security.cli.main native mark \
     --slug aave_v3 --status ready --or-status harness_built \
     --notes "Phase 3 row 2 promotion: <delta summary>" \
     --contract-address 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4e2 \
     --source-commit b74526a7
   ```

3. **Phase 4 rotation decision landed**:
   - **Option A** (rollout): `hermes/cron/jobs.example.yaml` (and any docs) updated to set `NSS_PHASE4_ROTATION_ENABLED=1` on the 04:00 cron line (after a clean dryrun validates cold/warm ordering). Add a regression test confirming `phase4_rotation_enabled` returns True when the cron profile sets it.
   - **Option B** (rollout with safety check): add `def is_saturated_for_rotation(slug, state)` to `bounty/native_picker.py` that returns True if the candidate is `harness_built` and was last touched within `rotation_window_days`. Modify `pick_next_target_v6_phase4` to skip saturated-for-rotation candidates. Add ≥ 4 tests:
     - saturated-for-rotation candidates are skipped
     - non-saturated cold programs float
     - saturated-for-rotation candidates re-enter after window elapses
     - empty result when all candidates are saturated-for-rotation
   - **Default to Option B** if neither path is fully validated by session end — keeps non-surprising behaviour for the 04:00 cron.

4. **Tests**: ≥ 14 net new tests:
   - `tests/test_morpho_value_moving.py` ≥ 4 cases (Morpho `accrueInterest` snapshot, capture round-trip, manifest promotion, fall-back when RPC unavailable).
   - `tests/test_aave_v3_measured_delta.py` ≥ 4 cases (USDC reserve snapshot, capture round-trip, manifest promotion, fall-back when RPC unavailable).
   - `tests/test_phase4_rotation_rollout.py` ≥ 3 cases (env-on-default, saturation-skip, cold-floats-above-saturated-warm).
   - `tests/test_measured_oracle.py` ≥ 3 new (Morpho + Aave v3 evidence round-trip; one for each capture script).
   All net new = ≥ 14. Baseline ≥ **582 / 6 skipped**.

5. **`AUDIT.md`** — Morpho Blue and Aave v3 rows promoted to `ready` (positive delta captured) OR kept at `harness_built` with documented RPC gap.

6. **`SPEC.md` §3** baseline test count updated.

7. **`CHANGELOG.md`** — add `2026-06-XX — v5 Morpho Blue value-moving delta + Aave v3 first delta + Phase 4 rotation rollout (audit Phase 3 row 1+2 close-out + Phase 4 enabled/guarded)` entry.

8. **Lab notebook entry** — write `data/security_results/lab_notebook/2026-06-XX-v5-real-delta-phase4-on.md` (this document — the new handover IS the lab entry; do not duplicate it; instead, write a 30-line "today's session" addendum dated today at the same path that records what landed).

9. **Commit + push** to `main` with the suggested message below.


---

## 5. Hard constraints — DO NOT violate

- **Do NOT loosen `submission_gates.py` / `evidence_grading.py` / `novel_gate.py` / `task_verifier.py`.** Dead-ends (catalog replay, triage-only, fee-only, fake-positive) must remain rejected. Capture a real on-chain delta; never a synthetic one.
- **Do NOT touch the synthetic substrate.** `domain/attack_templates/*`, `core/hypothesis.py`, `parameter_spaces.py` stay intact.
- **Do NOT add new packages.** urllib + stdlib. Pure-Python Keccak lives in `crypto/__init__.py`.
- **Do NOT remove existing tests.** Keep `tests/test_phase4_rotation.py` (8 cases), `tests/test_cron_registry_flip.py` (5 cases incl. widening), `tests/test_native_aave_v3.py` (17 cases), `tests/test_native_morpho_blue.py` (21 cases), `tests/test_fork_validation_abi_idl.py` (8 cases), and `tests/test_pick_next_target_*` green.
- **Do NOT paste API keys** (`ALCHEMY_API_KEY`, `ETHEREUM_RPC_URL`, private keys). Canonical addresses (USDC, WETH, PoolManager, StateView, Morpho Blue, Aave v3 PoolAddressesProvider, Aave v3 IPoolDataProvider) ARE OK.
- **Do NOT edit `nss-hipif-chain.sh`.** It only sets `NSS_HIPIF_PAUSE_FOR_NATIVE`.
- **Do NOT mark `morpho_blue` or `aave_v3` as `ready` without a positive `measured_impact_oracle.v1` delta.** Audit C2's contract is non-negotiable: status only flips when the oracle reports positive measured motion against live state. Zero-delta or missing-RPC stays `harness_built` with documented gap.
- **Do NOT silently flip `NSS_PHASE4_ROTATION_ENABLED=1` as a global default.** The decision is binary: enable the cron line **after a clean dryrun** (Option A) OR add a saturation-vs-rotation guard (Option B). Anything in between is opt-in only.
- **Do NOT widen the `depth_env()` C5 flag again.** It is already chain-wide per `b33a34b`. Don't contradict this.

---

## 6. Detailed playbook

### Step 6.1 — Morpho Blue value-moving probe

#### 6.1.1 Build the probe contract

The USDC/WETH market is empty. To exercise `accrueInterest` you need a market with at least one active position. Two authoritative ways to find one:

- **The Morpho Blue subgraph** (hosted at `https://api.morpho.org/blue/v1/graphql` per Morpho documentation, public endpoint). Query: `query { markets(where: { totalSupplyAssets_gt: "1000000" }, first: 5) { id loanToken collateralToken totalSupplyAssets totalBorrowAssets } }`. Pick the first result with a non-zero state.
- **The `morpho-blue-offchain-widgets/` companion repo**: contains canonical MarketParams snapshots per network with liquidity classification.

Alternative if neither works: **borrow a market from a known Curve/Convex/Aave fork that proxies through Morpho Blue**. E.g. `Gauntlet USDC Prime` (USDC market on Morpho Blue) is well-known and has $M+ TVL.

#### 6.1.2 Foundry probe (`foundry/test/MorphoBlueMeasure.t.sol`)

The file already exists per `b33a34b`. **Extend** it:

```solidity
contract MorphoBlueMeasure {
    IMorpho internal constant MORPHO = IMorpho(0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD);

    function testAccrueInterestMovesMarket(uint256 preBlock, uint256 postBlock) external {
        // 1) Capture market(b) at preBlock (selector 0xa6460d65 = market(bytes32))
        // 2) Wait: vm.roll to postBlock
        // 3) Wait: vm.warp forward N seconds
        // 4) Issuer: morpho.accrueInterest(preBlock-market-id)  [NOT a state-changing probe — read-only is fine]
        // 5) Capture market(b) at postBlock
        // 6) Assert totalSupplyAssets[t] - totalSupplyAssets[p] > MEASURED_DELTA_THRESHOLD
        // 7) emit log_named_uint("PRE.totalSupplyAssets",  preMarket.totalSupplyAssets);
        //    emit log_named_uint("POST.totalSupplyAssets", postMarket.totalSupplyAssets);
        //    emit log_named_uint("DELTA",                   delta);
        //    emit log_named_uint("MARKET_ID_HEX_32",        uint256(marketId));
    }
}
```

The capture script `scripts/_capture_morpho_measurement.py` (per `b33a34b`) already parses this output into `data/security_results/impact/morpho_blue_measured_delta.json`. **Audit the script**:
- Does it round-trip forge output through `measured_oracle.build_evidence_envelope`?
- Does it honour `MEASURED_DELTA_THRESHOLD`?
- Does it gracefully fall back to the "RPC unavailable" branch?

If the **forge test runs** (RPC available), produce a fresh capture with positive delta → `morpho_blue: ready`.

If **RPC unavailable**, the lab entry must explicitly say so. **Default fallback** path: keep `harness_built`, append a §"RPC unavailable" note. **No sneaky promotion.**

#### 6.1.3 Promotion

```bash
.venv/bin/python -m night_shift_security.cli.main native mark \
  --slug morpho_blue --status ready \
  --notes "Phase 3 row 1 promotion: <delta summary>" \
  --contract-address 0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD \
  --source-commit 55d2d99304fb3fb930c688462ae2ccabb1d533ad
```

Now `ready_count=2` (uniswap_v4 + morpho_blue).

### Step 6.2 — Aave v3 first measured delta

#### 6.2.1 Probe

The simplest Aave v3 probe: snapshot `IPoolDataProvider.getReserveData(asset)` with `asset = USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` across two adjacent Ethereum blocks. The reserve data structure includes `liquidityRate`, `variableBorrowIndex`, `lastUpdateTimestamp`. Across 7200-block windows (1 day), `lastUpdateTimestamp` increments by ≥ 3600 s reliably when there is on-chain demand; `liquidityRate` moves.

```python
# scripts/_capture_aave_measurement.py
from src.night_shift_security.impact.measured_oracle import build_evidence_envelope, write_evidence
from src.night_shift_security.native.aave_v3 import resolve_pool

def main():
    pre = resolve_pool(USDC_ADDR, rpc_url=ETH_RPC_URL, block=PRE_BLOCK)
    post = resolve_pool(USDC_ADDR, rpc_url=ETH_RPC_URL, block=POST_BLOCK)
    spec = MeasureSpec(scope='native-mandatory', market='aave_v3', asset='USDC', pre_block=PRE_BLOCK, post_block=POST_BLOCK)
    envelope = build_evidence_envelope(spec, pre_state=pre, post_state=post)
    write_evidence('aave_v3_measured_delta.json', envelope)
    # Returns: 0 (zero-delta honest) or positive-delta (oracle stamps measured_impact: True)
```

Where `resolve_pool` returns a serialisable `ReserveResolution` dataclass (or whatever the existing file calls it) — **read the file first to confirm the names**.

If `lastUpdateTimestamp` doesn't increment in your probe window (no demand) AND no other rate moves, the oracle correctly stamps `measured_impact: false`. Aave v3 stays `harness_built` only if you have no positive delta. But rate moves are usually non-zero across a 24-block window on Ethereum mainnet during US business hours.

For a **deterministic** capture, use a known historical block: pick a block where Aave v3 had a USDC liquidation or supply event (per `events.aave_v3_history_search` — extend if not present).

#### 6.2.2 Promotion

Once positive delta obtained:

```bash
.venv/bin/python -m night_shift_security.cli.main native mark \
  --slug aave_v3 --status ready \
  --notes "Phase 3 row 2 promotion: <delta summary>" \
  --contract-address 0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4e2 \
  --source-commit b74526a7
```

Now `ready_count=3` (uniswap_v4 + morpho_blue + aave_v3).

### Step 6.3 — Phase 4 rotation rollout decision

Two paths. Default path is Option B (safer).

#### Option A: enable `NSS_PHASE4_ROTATION_ENABLED=1` on the 04:00 cron line

1. Run a single isolated dryrun with the flag on:
   ```bash
   NSS_PHIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1 \
     NSS_PHASE4_ROTATION_ENABLED=1 timeout 90 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -20
   ```
   Confirm the picker rotates cold programs onto the queue (look for `pick_next_target_v6_phase4` log names).
2. Update `hermes/cron/jobs.example.yaml` — add `NSS_PHASE4_ROTATION_ENABLED=1` to the 04:00 cron line's env.
3. Update `AGENTS.md` cron settings table to reflect the rotated default.
4. Add ≥ 1 regression test `tests/test_phase4_rotation_rollout.py::test_cron_yaml_includes_phase4_flag` (assertion reads `jobs.example.yaml`, confirms the flag is set on the 04:00 line).

#### Option B: saturation-vs-rotation safety check (default if Option A isn't ready)

Add to `bounty/native_picker.py`:

```python
def is_saturated_for_rotation(slug, state, *, now=None, window_days=14):
    """True if `slug` was last touched within `window_days` and is a harness_built
    candidate — these are de-prioritized but NOT excluded, because the rotation
    score already handles cold/warm ordering. This function is a guard for callers
    who want strict rotation behaviour."""
    state = state or {}
    last_touched = dict(state.get("last_touched") or {}).get(slug)
    if not last_touched:
        return False
    days = _days_since_last_touched(slug, state, now=now)
    return 0.0 <= days <= float(window_days)
```

Modify `pick_next_target_v6_phase4` to skip `is_saturated_for_rotation(...)` candidates. Add ≥ 4 tests:
- `test_saturated_for_rotation_skipped`: candidate touched 3 days ago is skipped.
- `test_cold_floats_above_saturated_warm`: cold non-saturated candidate preferred over warm saturated.
- `test_saturated_candidate_re_enters_after_window`: candidate touched 20 days ago re-enters.
- `test_empty_returns_none_when_all_saturated`: full skip returns None.

Add the rollout regression test regardless of which path:
- `test_cron_yaml_defaults_phase4_off`: until operator decides otherwise, the cron YAML keeps the flag off.

#### Decision rule

| Decision | Conditions |
|----------|-----------|
| Option A | dryrun succeeds with cold/warm ordering visible; manifest has ≥ 2 `ready` harnesses |
| Option B (default) | Neither dryrun nor manifest ready for Option A; OR operator has not signed off |

If both are ready, **default to Option B** unless the dryrun output was cherry-picked. The audit's "no auto-promotion" applies to manifests AND cron configs.

### Step 6.4 — Verification

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
```

Pre-pickup: **568 / 6 skipped**. Post-pickup: ≥ **582 / 6 skipped**.

### Step 6.5 — Cron smoke (dryrun)

```bash
NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1 \
  timeout 60 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -12
```

The bootstrap header must reflect:
- `pause_for_native=0` (you overrode it for dryrun),
- `bounty_depth=1`,
- the chain either runs to `chain_status=complete` within the timeout, or prints a benign "no uninvestigated targets" notice (acceptable in dryrun state).

If you rolled out Phase 4 Option A, also smoke-test with the flag on:
```bash
NSS_PHASE4_ROTATION_ENABLED=1 timeout 60 bash hermes/scripts/nss-hipif-chain.sh
```


---

## 7. Anti-patterns to avoid

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Marking `morpho_blue: ready` on USDC/WETH with no positions | Audit C2's contract is explicit — `ready` requires a positive measured delta. Pick a market with liquidity, or stay `harness_built` honestly |
| Marking `aave_v3: ready` because "we read some bytecode" | Aave v3 needs a positive `measured_impact_oracle.v1` delta (e.g. `lastUpdateTimestamp`, `liquidityRate`, or `totalSupplied` motion). Reading bytecode ≠ capturing motion |
| Flipping Phase 4 ON by default in code (not just cron YAML) | Whoever inherits the code base shouldn't be surprised. Rotation's behaviour in dryrun is documented; in production the cron line configures it |
| Importing `requests` / `httpx` / `web3` for the capture scripts | urllib + stdlib only. Pure-Python Keccak lives in `crypto/__init__.py`. These constraints exist for several reasons (no supply chain, easy replay) |
| Using the same RPC URL everywhere | Have a fallback for when `ETHEREUM_RPC_URL` is unset or 429s. The capture script should exit gracefully and write a `status=rpc-unavailable` envelope rather than crash |
| Slicing concrete_candidates.jsonl retroactively | New additions only. Existing entries are honest evidence and must remain |
| Promoting `morpho_blue` while skipping Aave v3 | Don't cherry-pick. The mandate is "capture both delta probes + decide Phase 4." Both probes gets `count=2` of new promotions; either both `ready` or neither |
| Adding tests that import the `morpholink` Python package | It's a third-party npm package, not Python. The capture script uses urllib + raw ethers JSON-RPC |
| Forgetting to update the `last_touched` state between sessions | The Phase 4 ranker needs the timestamp. `rotate_target()` writes it after selection; subsequent picks see cold/warm ordering. Confirm `rotate_target` survives process restarts (state persists to `data/security_results/` JSON — verify path) |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except user notes (`goal-reference.md`, `solodit-api-ref.md`)
- [ ] `git log --oneline -3` shows `b33a34b` (Morpho honest delta + Phase 4 rotation + Aave v3 skeleton), `0d17789` (handover replace), `95b5b79` (C6 + Morpho harness)
- [ ] `head SPEC.md` -> `5.0.0-draft`
- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> **568 passed, 6 skipped**
- [ ] `native status` -> uniswap_v4: ready; morpho_blue: harness_built; aave_v3: harness_built; ready_count=1
- [ ] `find sources -maxdepth 1 -type d` -> auditvault, kamino, uniswap_v4, wormhole, morpho, aave_v3 (all present)
- [ ] `cat data/security_results/impact/morpho_blue_measured_delta.json | head -5` -> zero-delta honest envelope visible
- [ ] `cat data/security_results/impact/aave_v3_measured_delta.json` -> **file does NOT exist yet — this is YOUR gap**

### Closing (10 min)

- [ ] `pytest tests/ --ignore=tests/test_api.py -q` -> ≥ **582 / 6 skipped** (+14 net new minimum)
- [ ] `data/security_results/impact/morpho_blue_measured_delta.json` overwritten with fresh positive-delta capture, OR explicit "RPC unavailable" branch documented in today's lab addendum
- [ ] `data/security_results/impact/aave_v3_measured_delta.json` exists with `schema_version=measured-oracle.v1`
- [ ] `native status` reflects the new state (morpho_blue and/or aave_v3 may have promoted to `ready` based on capture); if either stays `harness_built` the lab entry must justify
- [ ] Phase 4 rotation rollout decision recorded: either Option A cron YAML change OR Option B safety check added
- [ ] `pick_next_target_v6_phase4` (`bounty/native_picker.py`) integration with `bounty_loop.py` still works (`phase4_rotation_enabled` reads env var, `rotate_target` records `last_touched`)
- [ ] Lab addendum written: `2026-06-XX-v5-real-delta-phase4-on.md` (the same file as this handover, with a 30-line addendum at the top recording what landed)
- [ ] `AUDIT.md` "Current v5 Gaps" updated: morpho_blue and/or aave_v3 closed; Phase 4 row notes rollout
- [ ] `SPEC.md` §3 test count updated
- [ ] `CHANGELOG.md` 2026-06-XX entry added
- [ ] `git status --porcelain` clean except user notes
- [ ] Push to `origin main`

---

## 9. Blockers playbook

- **No `ETHEREUM_RPC_URL` for value-moving probes**: The probe scripts must gracefully fall back. Pre-existing `data/security_results/impact/{uniswap_v4, morpho_blue}_measured_delta.json` were captured by the original sessions with a working RPC. If the new RPC is rate-limited or down, document in the lab addendum and exit gracefully (don't fake a delta). **The honest zero-delta fallback is the same envelope produced by `b33a34b`** — copy the structure verbatim.

- **Morpho Blue subgraph requires API key**: the public endpoint `https://api.morpho.org/blue/v1/graphql` does NOT require auth (per Morpho documentation as of 2026). If you hit a 401/403, write a fallback that uses the canonical USDC/WETH market ID `0xb859…` or fetch via on-chain `morpho.idToMarketParams(...)` per event log. Document the gap.

- **Aave v3 `lastUpdateTimestamp` doesn't move in the probe window**: this is normal for low-demand blocks. Try a window that includes a known Aave v3 event (see `events.aave_v3_history_search`). If still zero, capture an "RPC quiet" envelope and move on without promotion.

- **Phase 4 Option B saturation guard races with rotation ticking**: `is_saturated_for_rotation` reads `state["last_touched"][slug]`. If state is reset between sessions, all candidates look cold and the guard is a no-op. Document this in the function docstring.

- **Forge build complains about Solidity version**: Aave v3 and Morpho Blue both pin `pragma solidity ^0.8.20` or similar; match the version in your test files (look at the existing `UniV4Measure.t.sol` and `MorphoBlueMeasure.t.sol`).

- **Native mark CLI is missing a `--status-record` flag**: review `cli/main.py` `native mark` subcommand; do NOT add new CLI flags unless necessary — pass via existing args.

- **`bounty_depth()` overrides `phase4_rotation_enabled` env on launch**: it shouldn't, but check. If it does, accept it as the cron-line ownership (the cron YAML is the source of truth; `bounty_depth` is honouring the operator's choice).

---

## 10. Files this session is expected to touch

```
src/night_shift_security/native/morpho_blue.py                    (read-only inspection; extend only if probe needs helpers)
src/night_shift_security/native/aave_v3.py                        (read-only inspection; possibly extend resolve_pool for round-trip)
src/night_shift_security/impact/measured_oracle.py                (read-only inspection; predicates used by capture scripts)
src/night_shift_security/bounty/native_picker.py                  (extend with is_saturated_for_rotation if Option B)
scripts/_capture_morpho_measurement.py                            (re-instrument for value-moving probe Option A; fall back to RPC-unavailable)
scripts/_capture_aave_measurement.py                              (new — Aave v3 measured delta capture)
data/security_results/impact/morpho_blue_measured_delta.json      (overwrite with new capture; OR keep existing zero-delta envelope + lab rationale)
data/security_results/impact/aave_v3_measured_delta.json          (new — envelope)
data/security_results/loop/native_harness_status.json             (morpho_blue and/or aave_v3 may flip ready)
hermes/cron/jobs.example.yaml                                     (Phase 4 Option A only: cron line updated)
AGENTS.md                                                          (Phase 4 Option A only: cron settings table note)
tests/test_morpho_value_moving.py                                 (new — ≥ 4 cases)
tests/test_aave_v3_measured_delta.py                              (new — ≥ 4 cases)
tests/test_phase4_rotation_rollout.py                             (new — ≥ 3 cases)
tests/test_measured_oracle.py                                     (extend — ≥ 3 cases)
AUDIT.md                                                            (close morpho_blue and/or aave_v3 rows; add Phase 4 rollout line)
SPEC.md                                                             (§3 baseline test count)
CHANGELOG.md                                                        (2026-06-XX entry titled)
data/security_results/lab_notebook/2026-06-XX-v5-real-delta-phase4-on.md  (this file's new home, with today's addendum at top)
```

---

## 11. Final word

Stay tight. The v5 audit corrections are all closed; you are promoting **proven harnesses to `ready` on the strength of real on-chain delta evidence**. The leverage is enormous: every newly-ready harness unblocks a new bounty lane for the 04:00 cron.

Priority ordering for your day:

1. **Morpho Blue value-moving probe** — most leverage (canonical row 1 of Phase 3).
2. **Aave v3 first measured delta** — canonical row 2.
3. **Phase 4 rotation rollout** — optional but recommended. Default to Option B (safety guard). Promote to Option A only after a clean dryrun.
4. **Pendle PT sketch** — optional, only after the three above are shipped.

Two-promotions (`morpho_blue` and `aave_v3` to `ready`) is the realistic ceiling. If you only get one: prioritise Morpho Blue. If RPC unavailable everywhere, the capture scripts gracefully exit with `status=rpc-unavailable` envelopes and the manifest stays honest at `harness_built` for both.

The agent is one **real on-chain liquidation / rate update / interest accrual** away from tripling the ready count. The protocols are accurate, the harnesses are tested, the foundation is solid. Capture the value motion and the system does the rest.

### Suggested commit message (one line)

```
SPEC 5.0.0 Morpho Blue value-moving delta + Aave v3 first delta + Phase 4 rotation rollout
```

### Suggested commit message (descriptive)

```
SPEC 5.0.0 Morpho Blue value-moving delta + Aave v3 first delta + Phase 4 rotation rollout

- data/security_results/impact/morpho_blue_measured_delta.json: fresh
  positive-delta capture via either Morpho Blue accrueInterest probe on
  a market with liquidity, OR documented RPC-unavailable fallback with
  explicit width (zero-delta honest envelope reused if RPC missing).
- data/security_results/impact/aave_v3_measured_delta.json: live
  IPoolDataProvider.getReserveData(USDC) snapshot across an
  Ethereum-mainnet block window; oracle stamps measured_impact: true if
  liquidityRate / lastUpdateTimestamp / variableBorrowIndex shifts.
- data/security_results/loop/native_harness_status.json: morpho_blue
  promoted to ready if positive Morpho delta; aave_v3 promoted to ready
  if positive Aave delta. ready_count may rise 1 → 2 → 3.
- src/night_shift_security/bounty/native_picker.py: optional
  is_saturated_for_rotation helper if Phase 4 Option B path is chosen.
- hermes/cron/jobs.example.yaml: Phase 4 Option A path only —
  NSS_PHASE4_ROTATION_ENABLED=1 added to the 04:00 cron line after a
  clean dryrun.
- AGENTS.md: cron settings table updated to reflect Phase 4 Option A
  (if chosen).
- scripts/_capture_morpho_measurement.py: re-instrumented to honour
  the value-moving probe (accrueInterest snapshot) with fallback to
  RPC-unavailable branch.
- scripts/_capture_aave_measurement.py: capture script for Aave v3
  IPoolDataProvider snapshots.
- tests: test_morpho_value_moving.py (4), test_aave_v3_measured_delta.py
  (4), test_phase4_rotation_rollout.py (3), test_measured_oracle.py
  (+3).
- AUDIT.md: morpho_blue and/or aave_v3 closed; Phase 4 rollout line.
- SPEC.md §3 baseline test count updated.
- CHANGELOG.md: 2026-06-XX entry titled
  "v5 Morpho Blue value-moving delta + Aave v3 first delta + Phase 4
  rotation rollout (audit Phase 3 row 1+2 close-out + Phase 4
  enabled/guarded)".
- TESTS: ≥ 582 passed, 6 skipped (was 568 / 6; +14 net new minimum).
- Native manifest: ready_count may rise 1 → 2 → 3; remaining
  harness_built slugs kept honest.
```
