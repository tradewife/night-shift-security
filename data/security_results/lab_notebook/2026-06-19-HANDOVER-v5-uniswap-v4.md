# Session 2 Handover — Night Shift Security v5 NativeHarness build (Uniswap v4)

**Paste this entire document into your next session as context.**

---

## 1. Where we are

You are continuing the **Night Shift Security v5 pivot** started on 2026-06-18.

The system is sitting at SPEC v5.0.0-draft, commit `018ee06`. The previous
session produced a directed audit (`SYSTEM_AUDIT_2026-06-18.md`) and shipped a
NativeHarness precondition gate that **paused the v4.2 cron**. The autonomous
chain will not run again until at least one bug-bounty target reaches
`status=ready` in `data/security_results/loop/native_harness_status.json`.

The native precondition is the only ambient difference from v4.2.0. Every
gating, trust-boundary, RSI, lab-notebook, and skill-lockdown rule still
applies. The synthetic param-grid engine is **legacy** but kept running for
the 438-test regression baseline — do not delete or rewrite it without
preserving tests.

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — the eight structural defects and the nine
   audit-driven corrections (C1–C9). Read the entire file. Memorise:
   - D1 scope is fake (28 curated of 249 scope_registry programs).
   - D2 zero real harnesses beyond Wormhole.
   - D3 economic_impact_usd is currently a synthetic numeric.
   - D4 concrete_candidates.jsonl is populated only for Wormhole.
   - D5 saturated_slugs self-perpetuates.
   - D6 hypothesis generator is abstract-by-construction.
   - D7 cron front-loads compute on programs with no harness.
   - D8 fork_reproduced aggregate hides the absence of live forks.

2. `SPEC.md` — headsection only (Version, Status, §0). Confirm `5.0.0-draft`.

3. `AUDIT.md` — §"v5 Pivot" block at the bottom. The two P0/P1 tables
   describe what is missing.

4. `CHANGELOG.md` — `[5.0.0-draft]` entry. Note the 444/5 baseline.

5. `AGENTS.md` — Day Shift / Night Shift quick-start block. Take the
   `cd /home/kt/projects/rtp/night-shift-security && .venv/bin/python ...`
   commands as given; do not add new venvs or system packages.

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean working tree except `goal-reference.md`, `solodit-api-ref.md` (user-owned; ignore) |
| Pytest baseline | `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` | **444 passed, 5 skipped** |
| Native module | `src/night_shift_security/native/__init__.py` | shipped |
| Native tests | `tests/test_native_harness.py` | 6 passed |
| Manifest path | `data/security_results/loop/native_harness_status.json` | gitignored |
| Cron entrypoint | `hermes/scripts/nss-hipif-chain.sh` | `NSS_HIPIF_PAUSE_FOR_NATIVE=1` is the default |
| Day Shift plan | `data/security_results/day_shift/current.md` | v5 session plan |
| Pivot commit | `018ee06` | pushed |

Run `git status --porcelain` at session open. Anything beyond `goal-reference.md`
and `solodit-api-ref.md` untracked is unexpected.

---

## 4. The goal of YOUR session

Ship **C1** from the audit: build the first working **NativeHarness** for the
first target, **Uniswap v4** (Cantina $15.5M pot). Acceptance criteria
(verbatim from `SYSTEM_AUDIT_2026-06-18.md`):

> Build `src/night_shift_security/native/harness.py` + first impl
> `native/uniswap_v4.py`: ABI loader, selector decoding, account resolution,
> tx-stub builder. Used for quantum: PoolManager + hook surface scaffolded.

Concretely, that means **all** of the following are true at session end:

1. `sources/uniswap_v4/repo` exists with `v4-core/` checked out.
2. `semantic map --slug uniswap_v4 --repo sources/uniswap_v4/repo --kind amm`
   produces `data/security_results/semantic/uniswap_v4/code_map.json`,
   `entrypoints.json`, `value_flows.json`, `candidate_seeds.jsonl`. The
   `--kind amm` should match the available kinds (`semantic map --help` to
   confirm).
3. `data/security_results/knowledge/concrete_candidates.jsonl` has at least
   **50 new lines** for `target_id=uniswap_v4` referencing actual v4-core
   Solidity symbols (`PoolManager.modifyLiquidity`, `PoolManager.swap`,
   `PoolManager.donate`, `IHooks.beforeSwap`, etc.) and their selectors.
4. `src/night_shift_security/native/uniswap_v4.py` exposes at minimum:
   - a `load_abi(repo_path)` that returns the PoolManager ABI JSON.
   - a `selectors()` helper returning the canonical 4-byte selectors for
     `modifyLiquidity`, `swap`, `donate`, `settle`, `take`, `mint`, `burn`,
     `transfer`, plus the `BalanceDelta`/`Currency` library selectors.
   - a `resolve_pool(pool_key, rpc_url)` that **forks mainnet at a recent
     block and resolves `PoolManager.getSlot0(...)`** to confirm a real
     USDC/WETH or USDC/USDT pool address (post-Aug-2024 deployment).
5. `foundry/test/UniswapV4PoolManager.t.sol` exists, compiles under `forge
   build`, and contains at least one test that **calls the live PoolManager
   on a fork** (not a mock). It does not need a measurable delta yet.
6. `data/security_results/knowledge/concrete_candidates.jsonl` plugins
   are written by your harness code (not just generated by `semantic map`).
7. `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` still
   reports **444 passed, 5 skipped** at the start AND end of session. Any
   drop = revert and re-plan.
8. `native mark --slug uniswap_v4 --status harness_built` after step 4.
   Do **not** mark `ready` yet — that requires a measured delta on a live
   fork, which is C2.
9. A new lab notebook entry is written under
   `data/security_results/lab_notebook/2026-06-19-uniswap-v4-harness.md`.

---

## 5. What you can defer to subsequent sessions

- **C2 — MeasuredImpactOracle** (1 day): the `value_flows.json` you
  produce from `semantic map` doesn't yet compute pre/post balance diffs
  on a real fork. That is C2. The audit recommends the wrapper lives at
  `src/night_shift_security/impact/measured_oracle.py`. Skip this for this
  session.
- **C3 — `pick_next_target` precondition** (0.5 day): wires `C1`'s
  manifest into the existing bounty loop. Skip.
- **C7 — `fork_reproduced` label split** (0.5 day): not relevant until
  C1 has measured fork deltas. Skip.
- Moving synthetic substrate under `legacy/synthetic/`. **Do not do this
  yet.** Existing 438-test baseline still relies on the current imports;
  any rename breaks tests silently.

---

## 6. Detailed playbook for C1

### Step 6.1 — Read the existing scaffold that already worked (Wormhole)

Do NOT recreate primitives that already exist. Use what shipped.

```bash
# Read the one working harness page-by-page.
ls sources/wormhole/repo       # see how Wormhole handled the clone
ls hermes/scripts/nss-write-wormhole-triage-proposals.py
cat src/night_shift_security/semantic/solidity.py | head -80
cat src/night_shift_security/semantic/code_map.py
ls data/security_results/semantic/wormhole   # output layout to copy
```

The point: stand on **`semantic map`** (which already handles Solidity
parsing), not a new parser. Uniswap v4 is Solidity + hooks; the same
`semantic/solidity.py` should work.

### Step 6.2 — Clone Uniswap v4 (one canonical source)

```bash
mkdir -p sources/uniswap_v4
git clone https://github.com/Uniswap/v4-core.git sources/uniswap_v4/repo
git -C sources/uniswap_v4/repo log --oneline -1   # capture commit
```

If you do not have outbound network access in this sandbox, **stop and
post a lab note explaining the blocker**. Do not pivot to a fabricated ABI.

### Step 6.3 — Run semantic recon

```bash
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug uniswap_v4 \
  --repo sources/uniswap_v4/repo \
  --kind amm
ls data/security_results/semantic/uniswap_v4
```

If `--kind amm` is rejected, drop `--kind` and let it default.

Verify each artefact exists:

```
code_map.json
entrypoints.json
value_flows.json
candidate_seeds.jsonl
```

### Step 6.4 — Promote at least 50 candidates into `concrete_candidates.jsonl`

Read `src/night_shift_security/semantic/candidates.py` to find the schema
entry-point, then write a one-shot script that pushes the top-50 from
`candidate_seeds.jsonl` through `upsert_concrete_candidate(...)` with
`candidate_schema_version=4` and `target_pinned=true`. Inspect what fields
the existing store expects (`grep -n 'candidate_schema_version' src/`)
before writing the loop, otherwise your writes will be silently dropped.

If the semantic layer does not currently write
`concrete_candidates.jsonl` directly, add a thin promotion script under
`hermes/scripts/nss-promote-uniswap-v4-candidates.py` and call it once
inline. Document the script path in the lab note.

### Step 6.5 — Build the harness module

Create `src/night_shift_security/native/uniswap_v4.py`:

```python
"""Uniswap v4 NativeHarness — PoolManager + hook surface (Cantina \$15.5M).

First-generation NativeHarness per the 2026-06-18 directed audit. Reads
the deployed PoolManager from v4-core, exposes canonical 4-byte
selectors, and resolves a USDC/WETH pool via mainnet fork RPC.

Audit correction references: C1 (this file), C2 (measured oracle —
future), C5 (full registry sweep — future).
"""
```

Required surface:

- `load_abi(repo_path) -> list[dict]` — reads
  `sources/uniswap_v4/repo/deployments` or `out/PoolManager.sol/PoolManager.json`
  if forge has been run. Fallback to the curated ABI fragment inline.
- `selectors() -> dict[str, str]` — names → 4-byte `0x…` selectors for
  `modifyLiquidity`, `swap`, `donate`, `settle`, `take`, `mint`, `burn`,
  `initialize`, `updateLPFee`, `transfer`, `setHooks`, plus
  `IHooks.beforeSwap` (`0x1152af87` if you can verify it).
- `resolve_pool(pool_key: dict, rpc_url: str, block: int) -> dict` —
  forks at the given block, calls `eth_call` against PoolManager
  `getSlot0(PoolKey)`. Returns `{"pool_id": "0x…", "sqrt_price_x96": "…",
  "liquidity": "…", "block": …}`. Use `urllib` if `web3` is not
  installed; otherwise use `web3.py` if already in `pyproject.toml`.
  Do **not** install new packages.
- `HARNESS_TARGET` constant — drives `native/__init__.py` registration.
- Module `__all__` listing every public symbol.

Add a test under `tests/test_native_uniswap_v4.py`:

- `selectors()` must return the canonical 4-byte values for
  `modifyLiquidity` and `swap`. Hard-code the expected selectors for
  isolation. If you cannot retrieve them offline, derive them with
  `keccak(text="modifyLiquidity((bytes32,address,uint24,int24,address))")[:4]`
  via `eth_utils` if installed, or a `keccak` helper under
  `src/night_shift_security/crypto/`. Add a small JSON fixture under
  `tests/fixtures/uniswap_v4/` for ABI parity if you ship sample calls.
- `resolve_pool` is network-dependent; skip the network call in tests
  via `pytest.importorskip` against `ETHEREUM_RPC_URL`.

Ensure these tests pass **with the existing 444 baseline**.

### Step 6.6 — Foundry test scaffold (slow path; can defer if no `forge`)

```bash
foundry --version       # confirm forge is on PATH; otherwise skip
```

If `forge` is available:

```bash
mkdir -p foundry/test
cat > foundry/test/UniswapV4PoolManager.t.sol <<'SOL'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

interface IPoolManager {
    function getSlot0(bytes32 poolId) external view returns (uint160, int24);
    // Filled in by harness code generation; basic scaffolding only.
}

contract UniswapV4PoolManagerFork is Test {
    address constant POOL_MANAGER = 0x0000000000000000000000000000000000000000; // TODO
    function testForkMainnetPoolManagerDeployed() public {
        // forge-std vm.rpcUrl / vm.createFork pattern.
    }
}
SOL
```

Even an empty barrier test counts as C1 scaffolding.

If `forge` is NOT available, add a stub note in the lab entry and use
`tests/test_native_uniswap_v4.py` + `urllib`-backed RPC introspection
as the equivalent. **Do not invent mock answers.**

### Step 6.7 — Mark harness_built

```bash
.venv/bin/python -m night_shift_security.cli.main native mark \
  --slug uniswap_v4 \
  --name "Uniswap v4" \
  --platform cantina \
  --chain ethereum \
  --contract-address <resolved PoolManager address> \
  --source-commit $(git -C sources/uniswap_v4/repo rev-parse HEAD) \
  --status harness_built \
  --notes "ABI loaded; selectors resolved; pool resolution via RPC; forge stub drafted; concrete_candidates.jsonl +<N>"
```

Do **not** flip to `ready` until you have a measured delta.

### Step 6.8 — Lab notebook + commit

Write `data/security_results/lab_notebook/2026-06-19-uniswap-v4-harness.md`
with sections:

- **What shipped** (paths + counts)
- **Failures** (any RPC outage, missing `forge`, package blockers)
- **Measured deltas** (none expected this session — C2)
- **Next session** (C2 + measured delta on a live fork)

```bash
git add -A
git commit -m "SPEC 5.0.0 first NativeHarness: uniswap_v4 PoolManager + hooks"
git push origin main
```

---

## 7. Anti-patterns to avoid

These were defeats during v4.2.0; do not repeat them.

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Generating synthetic `param_grid` hypotheses without an ABI | This is what failed last cycle. SPEC §F1. |
| Synthesising "USDC pool" with random address | No measured delta. Crawls back into triage-only. |
| Reusing the legacy `parameter_spaces.py` for v4 | It has no entrypoint/selector/contract binding. |
| Adding new dependencies without `pyproject.toml` change | Adds risk; web3.py is allowed only if already present. |
| Marking `ready` prematurely | Audit C8 gates the cron; flipping early re-enables the broken loop. |
| Forgetting pytest baseline | Drop below 444 → flag the regression and stop. |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except `goal-reference.md`,
      `solodit-api-ref.md`
- [ ] `git log --oneline -3` shows `018ee06`
- [ ] `cat SPEC.md | head -10` shows `5.0.0-draft`
- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` → 444/5
- [ ] `cat data/security_results/loop/native_harness_status.json` shows
      `uniswap_v4 {status: mapped}`

### Closing (10 min)

- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` → ≥444/5
- [ ] `native status` shows `uniswap_v4 {status: harness_built}` (or higher)
- [ ] `forge build` clean (or stub note in lab entry)
- [ ] Lab notebook entry written and dated
- [ ] `git status --porcelain` clean except user-owned untracked files
- [ ] Push to `origin main`

---

## 9. If you hit a blocker

- **No outbound network**: cannot clone v4-core, cannot reach mainnet RPC.
  → Stop C1, write lab note titled
  `2026-06-19-uniswap-v4-blocked-network.md` describing the constraint,
  propose plan B (offline fixture), commit, exit. Do not invent data.

- **`forge` missing on PATH**: skip Foundry stub; rely on
  `tests/test_native_uniswap_v4.py` for selector/parity checks. Document
  in lab note.

- **`state.json` already marks `uniswap_v4` saturated**: don't override.
  Run `bounty_loop`'s `_maybe_mark_saturated` with care. The
  `saturated_slugs` rule does not apply to v5 native-harness targets
  (yet) — saturation is the v4 saturation predicate. The v5 manifest is
  the new source of truth.

- **You can't resolve a PoolManager address from the RPC**:
  check `https://docs.uniswap.org/contracts/v4/reference/deployments/ethereum`.
  If the deployment table is unreachable, fall back to the canonical
  Uniswap v4 deployment addresses from canonical
  `UniswapDeployments` contracts (the source itself ships them).
  Document the chosen address in the lab note.

---

## 10. Final word

Stay narrow. Build C1 only. Do not touch C2/C3/C7/C8. The audit identified
eight failures and the minimum-viable-v5 ships as soon as one harness
measures one real on-chain delta. Get there before broadening.

If the session ends without a measured delta, that's fine — document the
state of the build cleanly and let the next session finish C2 + `ready`.
A clean, well-documented harness_built beats a hand-waved `ready` that
lies to the cron and resets the loop.

Commit message suggestion if everything works:

```
SPEC 5.0.0 first NativeHarness: uniswap_v4 PoolManager + hooks
```
