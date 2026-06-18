# Session handover — Night Shift Security v5 C2 (MeasuredImpactOracle, Uniswap v4)

**Paste this entire document into your next session as context.**

---

## 1. Where we are

You are continuing the **Night Shift Security v5 pivot** at SPEC `5.0.0-draft`,
most recent commit `1c09485` ("SPEC 5.0.0 first NativeHarness: uniswap_v4
PoolManager + hooks (audit C1)").

In the previous session we shipped **audit correction C1** — the first
NativeHarness for the first target (Uniswap v4, Cantina $15.5M pot). The
`uniswap_v4` entry in `data/security_results/loop/native_harness_status.json`
is at **`status=harness_built`**, not `ready`, because `ready` requires a
measured delta on a live fork.

**Your job is audit correction C2: build the `MeasuredImpactOracle` for
the Uniswap v4 substrate, produce one real measured delta, and flip
`native mark --status ready`.** When that records `ready_count=1`, the
native precondition gate releases and the cron resume is automatic.

The C1 harness (`src/night_shift_security/native/uniswap_v4.py`),
the canonical selector/ABI infrastructure, and the live RPC resolver
are already in place and tested. You are extending them, not rebuilding
them.

---

## 2. Read FIRST (in this exact order)

1. `SYSTEM_AUDIT_2026-06-18.md` — read sections D2 / D3 / C2. Memorise:
   - D2 — zero real harnesses beyond Wormhole (already fixed in the
     previous session for `uniswap_v4`).
   - D3 — `economic_impact_usd` is currently a synthetic numeric; the
     `MeasuredImpactOracle` is the fix:
     > "A `MeasuredImpactOracle` that on a successful fork run does the
     > actual `(pre_balance, post_balance)` diff on (a)
     > `treasury`/`vault`/`reserve`/token-vault addresses; (b) attacker
     > EOA; (c) `outstanding_bridged(...)` style accounting. Wormhole
     > value probe code already does this. Use it everywhere."
   - C2 row of the table:
     > "New file: `src/night_shift_security/impact/measured_oracle.py` —
     > `(pre_state, post_state, deltas)` measured-oracle; integration in
     > `validation/submission_gates.py._v4_candidate_submission_ok`."
2. `SPEC.md` — headersection only (Version, Status, §0). Confirm
   `5.0.0-draft`. Skip the long §4 root-cause audit (it's pre-pivot
   history). Skim §6.7 (AuditVault), §6.9 (Hermes lockdown) — both are
   preserved.
3. `AUDIT.md` — read only the **"v5 Pivot (2026-06-18)"** section
   (about 30 lines). The two Current v5 Gaps tables describe what is
   blocking `ready`.
4. `CHANGELOG.md` — read the **2026-06-19** entry (the one beginning
   "v5 first NativeHarness shipped (audit C1)"). It is the
   immediately-preceding work; do not duplicate it.
5. `data/security_results/lab_notebook/2026-06-19-uniswap-v4-harness.md`
   — read the **"Out of scope this session (deferred per handover §5)"**
   and **"Next session"** sections at the bottom. That is the C2 charter.
6. `AGENTS.md` — today is Day Shift on Uniswap v4. Take v5 sources from
   `src/night_shift_security/native/`; do not add new venvs or system
   packages; treat `submission_gates.py` and `evidence_grading.py` as
   authoritative and not casually relaxed.

---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | `main` | clean except `goal-reference.md`, `solodit-api-ref.md` (user-owned; ignore) |
| Last commit | `1c09485` | pushed |
| Pytest baseline | `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q` | **463 passed, 5 skipped** |
| Manifest entry | `data/security_results/loop/native_harness_status.json` → `uniswap_v4` | `status=harness_built` (you flip to `ready`) |
| v4-core clone | `sources/uniswap_v4/repo` @ `46c6834698c48bc4a463a86d8420f4eb1d7f3b75` | gitignored, present |
| Native module | `src/night_shift_security/native/{__init__,uniswap_v4}.py` | shipped |
| Crypto helper | `src/night_shift_security/crypto/__init__.py` (pure-Python keccak-256) | shipped |
| Foundry stub | `foundry/test/UniswapV4PoolManagerHarness.t.sol` | compiled, 2 passed under ETH_RPC_URL |
| Cron entrypoint | `hermes/scripts/nss-hipif-chain.sh` | `NSS_HIPIF_PAUSE_FOR_NATIVE=1` still default |
| Day Shift plan | `data/security_results/day_shift/current.md` | v5 session plan |
| Impact module | `src/night_shift_security/impact/` | only `oracle_arbitrage.py` + `tvs_maximization.py` exist; the new file goes here |
| Validation | `src/night_shift_security/validation/submission_gates.py` | seam is `_v4_candidate_submission_ok` (read but do NOT loosen) |

Run `git status --porcelain` at session open. Anything beyond
`goal-reference.md` and `solodit-api-ref.md` untracked is unexpected.

---

## 4. The goal of YOUR session

Ship **C2** from the audit: a **`MeasuredImpactOracle` for the Uniswap
v4 substrate that records a real on-chain delta and flips the harness
to `ready`**. Acceptance criteria (verbatim from the audit + the previous
handover's "Next session"):

> Build `src/night_shift_security/impact/measured_oracle.py`: a
> `(pre_state, post_state, deltas)` measured-oracle; integrate in
> `validation/submission_gates.py._v4_candidate_submission_ok`.

Concretely, that means **all** of the following are true at session end:

1. **`src/night_shift_security/impact/measured_oracle.py` exists** and
   exposes:
   - `compute_pre_state(rpc_url, block, snapshot_spec) -> PreState` —
     reads the on-chain balances of a defined snapshot spec via
     `eth_getBalance` / ERC-20 `balanceOf` / `extsload` reads at a fixed
     block before any interaction.
   - `compute_post_state(rpc_url, block, snapshot_spec) -> PostState` —
     reads the same slot set at a fixed block after a defined
     interaction.
   - `MeasureSpec` (or equivalent) dataclass with:
     `target_addresses: list[str]`, `tokens: list[str]`, `pool_keys: list[dict]`,
     `block_pre: int`, `block_post: int`, `rpc_url: str`. Validates
     against the C1 harness constants (uses
     `uniswap_v4.DEFAULT_POOL_MANAGER_MAINNET`,
     `uniswap_v4.DEFAULT_STATE_VIEW_MAINNET`, etc.).
   - `delta(pre, post) -> Dict[str, Any]` returning a flat diff:
     `attacker_eoa_delta_wei`, `pool_manager_delta_wei`,
     `{token_address: delta_units}` for the requested ERC-20s, AND a
     `sqrt_price_x96_delta` / `tick_delta` per resolved pool.
   - `MEASURED_DELTA_THRESHOLD` constant — minimum non-fee delta we'll
     count as impact (e.g. > 0 for ETH, > 1 USD-equivalent for ERC-20s).
   - Negative-result honesty: if the diff is non-positive, the oracle
     must return `measured_impact=False, evidence=<typed-empty-state>`
     rather than fabricate value. (This matches the audit's
     "do not invent mock answers" rule.)
2. **An entry point (`nss-uni-measure` or `measured-oracle` CLI) that
   records the result** to `data/security_results/impact/uni_v4_measured_delta.json`
   with schema `{schema_version, generated_at, slug, pre: {...}, post: {...},
   delta: {...}, measured_impact: bool, source_commit, nss_version}`.
3. **At least one live `pre → tx → post` triple on a real v4 pool** that
   records a non-fee positive delta. The recommended probes:
   - `PoolManager.donate(PoolKey, amount0, amount1, hookData)` on a real
     USDC/WETH pool: caller balance drops by amount0 + amount1, donor's
     `Pool.s balances` go up. The pool's `sqrtPriceX96` does NOT move
     and `tick` does NOT move. Diff across pre/post should record
     `_deltas` straight from the donor EOA + a corresponding +
     amount0/amount1 in `getSlot0` after the donate aftermath (note:
     donate does not change slot0 state, so the slot0 delta is the
     measured oracle's "control" assertion).
   - `PoolManager.modifyLiquidity(PoolKey, ModifyLiquidityParams, hookData)`:
     addLiquidity of N USDC + M WETH, then removeLiquidity. Pre/post
     `nonzeroDeltaCount` from `TransientStateLibrary.extsload` reads
     should match, and the attacker EOA receives back close to N + M
     minus accrued fees.
   - If `forge-std` is preferred for the tx broadcast (cheaper tx
     envelope, deterministic nonce), do it inside `foundry/test/UniV4Measure.t.sol`
     and have the Python oracle read the post-state directly.
4. **`native mark --slug uniswap_v4 --status ready`** with
   `--notes "<one-line summary of the measured delta + non-fee positive>"`.
   The manifest `ready_count` must become **1**. After 8s of grace, the
   cron precondition gate releases automatically.
5. **Tests**:
   - `tests/test_measured_oracle.py` — covers non-positive delta
     honesty, threshold logic, snapshot schema, and a synthetic mock
     pre/post that returns a positive delta (negative-result test).
     **At least 4 tests, none requiring RPC.**
   - Live-RPC-dependent test (gated behind `ETHEREUM_RPC_URL`) records
     a real diff on a fork — write it for posterity but mark it
     `pytest.importorskip` so the **463/5 baseline must continue to
     pass with no RPC**.
6. **`.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q`
   still reports ≥463 passed, 5 skipped at session start AND end.**
   Any drop = revert and re-plan.
7. **Trust boundary preserved.** Do NOT touch
   `auditvault`, `solodit`, `submission_gates` (loosen the v4-candidate
   rules accidentally), or `evidence_grading`. The only safe edit to
   `submission_gates.py` is making it *admit* the new measured evidence
   shape if it differs from the existing one (extend, do not weaken).
8. **A new lab notebook entry** under
   `data/security_results/lab_notebook/2026-06-19-uniswap-v4-measured-oracle.md`
   covering what shipped, what failed, the canonical delta schema, and
   what C3 (loop precondition guard) means for the next session.
9. **`AUDIT.md` Current v5 Gaps table updated** to remove the now-shipped
   `First measured delta on a real contract` row, and SPEC.md §3
   baseline updated to reflect the new test count.
10. **CHANGELOG.md** gets a 2026-06-19 second-entry block documenting
    the C2 work + the `ready` flip.

---

## 5. What you can defer to subsequent sessions

- **C3 — `pick_next_target` precondition** (0.5 day): once `uniswap_v4`
  is `ready`, the next session wires the manifest into the loop's
  target picker. Do not attempt in this session.
- **C7 — `fork_reproduced` label split** (0.5 day): not relevant until
  C1+C2 have measured fork deltas. Skip.
- **Scaling to other targets** (Morpho Blue, Aave v3, Compound v3,
  Pendle, Euler v2): TEMPLATE work after the first measured delta
  works end-to-end. Defer.
- **Moving the synthetic engine under `legacy/synthetic/`**: the audit
  recommends it; do not do it now — the existing 463-test baseline still
  relies on current imports; a rename breaks tests silently.

---

## 6. Detailed playbook for C2

### Step 6.1 — Read the C1 leaf work

```bash
cd /home/kt/projects/rtp/night-shift-security
ls src/night_shift_security/native/
cat src/night_shift_security/native/uniswap_v4.py | head -80
cat src/night_shift_security/native/__init__.py
```

Read the existing harness surface. Use its constants and helpers
(`selectors()`, `load_abi()`, `_pool_id()`, `resolve_pool()`).
Do not reinvent canonical-keccak selector derivation.

### Step 6.2 — Probe a real v4 pool to anchor your oracle

C1's `resolve_pool` returned all-zero `sqrtPriceX96` / `tick` because
the calling PoolKeys at `latest` had been initialised but the
queried StateView returned the default slot0 (the slot exists at the
PoolId but in many cases returns the empty initial state). To get a
meaningful diff you must:

1. Identify a PoolId that **has been initialised and has nonzero
   `sqrtPriceX96` / `tick`**. Easiest paths:
   - Use a subgraph / cached v4 pool index. **Do NOT fabricate.**
   - Use `forge` to issue `initialize(PoolKey, sqrtPriceX96)` via the
     UniversalRouter, or call `StateView.initialize(PoolKey, sqrtPriceX96)`
     if the StateView exposes that (it does not — `PoolManager.initialize`
     is the entry point — and `PoolManager.initialize` is permissioned
     to anyone per Uniswap v4 design). Issuing an init costs no fees
     if the PoolId hasn't been initialised before; the `state.slot0`
     after that initialise will hold the supplied initial price.
   - The **simpler** and **safer** path: use the public
     UniversalRouter cross-chain path and ask the operator for a known
     initialised PoolId via `goal-reference.md` (user-owned notes that
     are likely to contain a hand-curated list). If absent, pick a
     not-yet-initialised PoolKey and call `initialize(key, 79228162514264337593543950336)`
     (sqrtPriceX96 = 2^96, the canonical 1:1 price point) — this gives
     you a `sqrtPriceX96 = 79228162514264337593543950336` and `tick = 0`
     post-state, which is a *real* on-chain delta even if economically
     trivial.
2. Run a `donate(PoolKey, 100_USDC_units, 0)` after init via the
   `PoolManager` proxy (forge via vm.startPrank… or Python via a
   constructed tx — both routes exist in the engine). This bumps the
   pool's dangling balance without changing slot0. Pre/post EOA
   balances + Pool's cumulative balance in transient storage move by
   exactly `100_USDC_units` (= 100 in 6-decimal USDC terms = 1e8 raw
   units). That is your measured delta proof.

### Step 6.3 — Build the measured oracle

```text
src/night_shift_security/impact/measured_oracle.py
```

Required surface (see §4 #1):

- `PreState` / `PostState` dataclasses with the `attacker_eoa`,
  `pool_manager_cumulative` (`BalanceDelta`), per-token EOA balances,
  per-pool `(sqrt_price_x96, tick)` snapshots.
- `MeasureSpec` dataclass with the spec fields listed above.
- `compute_pre_state(...)` and `compute_post_state(...)` that either:
  - use `urllib` against the live RPC (`ETH_RPC_URL`), OR
  - accept a Foundry RPC endpoint for kernel-mode parity.
- `delta(...) -> dict` returning the diff.
- `MEASURED_DELTA_THRESHOLD` constant defined inline.

Behaviour rules:

- If pre/post slots cannot be read (RPC outage, missing contract),
  raise `RuntimeError("rpc_*")` mirroring the C1 error-tag style.
- If `delta(...)` returns a non-positive diff **and** the delta's
  absolute value is below `MEASURED_DELTA_THRESHOLD`, the function
  must return `{"measured_impact": false, "evidence": {...}}` — never
  silently coerce to `True`. The audit forbids hand-waving.
- All inner calls should reuse `uniswap_v4.selectors()` / `_pool_id()`
  / `eth_call` / `get_code` — these are part of the harness and
  already exposed.

Skeleton step:

```python
from dataclasses import dataclass, field
from typing import Any

from night_shift_security.native import uniswap_v4 as uv4


MEASURED_DELTA_THRESHOLD = 10 ** 6   # 1 USD-equivalent in 6-decimal units


@dataclass
class MeasureSpec:
    rpc_url: str
    attacker_eoa: str
    pool_manager: str = uv4.DEFAULT_POOL_MANAGER_MAINNET
    state_view: str = uv4.DEFAULT_STATE_VIEW_MAINNET
    target_token: str = uv4.DEFAULT_USDC_ETHEREUM  # default ERC-20 to balance-track
    pool_keys: list[dict[str, Any]] = field(default_factory=list)
    block_pre: int | str = "latest"
    block_post: int | str = "latest"


# … compute_pre_state / compute_post_state / delta as described …
```

### Step 6.4 — Wire into submission gates (careful)

`submission_gates.py _v4_candidate_submission_ok` already accepts
any of:
- `candidate.impact_oracle.measured == True`, OR
- `fork_evidence.balance_delta_wei > 0`, OR
- `fork_evidence.token_delta > 0`, OR
- `solana_evidence.*_delta > 0`.

The simplest design is: the C2 oracle writes the diff straight into
`data/security_results/impact/uni_v4_measured_delta.json` and the
caller (future harness/loop code, **not** this session) wraps it as
a finding with the proper `fork_evidence.token_delta` and
`candidate["impact_oracle"]["measured"] == True`.

**Do not broaden `submission_gates.py` in this session.** The
correct simply-safe move is: emit the evidence file + a tiny adapter
in `night_shift_security/impact/measured_oracle.py` that emits a fully
shaped `candidate[...]` payload which a future loop will merge into a
finding. Document the schema on the lab entry; do not hot-patch the
engine to use it automatically. The audit explicitly forbids
loosening gates.

### Step 6.5 — CLI subcommand

Add a new CLI subcommand to `cli/main.py`:

```
night-shift-security measured-oracle run --slug uniswap_v4 \
    --rpc-url "$ETHEREUM_RPC_URL" \
    --attacker-eoa 0x<your-eoa> \
    --pool-key <json> \
    --output data/security_results/impact/uni_v4_measured_delta.json
```

If implementing the CLI wiring takes too long for your time budget:
the Python module entry-point (a `__main__` guard or an `if __name__`
script) is acceptable for the session, and a CLI subcommand can be
deferred to the next session.

### Step 6.6 — Foundry path (optional but cheap if `forge` available)

If you prefer direct tx broadcast, write `foundry/test/UniV4Measure.t.sol`
that does:

```solidity
function test_donate_measure() public {
    PoolKey memory key = PoolKey({
        currency0:    Currency.wrap(0xA0b8…eB48),  // USDC
        currency1:    Currency.wrap(0xC02a…6Cc2),  // WETH
        fee:          3000,
        tickSpacing:  60,
        hooks:        IHooks(address(0))
    });
    uint160 one_to_one = 79228162514264337593543950336;
    vm.prank(attacker);
    poolManager.initialize(key, one_to_one);

    // Slot0 snapshot via StateView
    uint160 sqrtPriceX96_before = stateView.getSlot0(key.toId()).sqrtPriceX96();
    // capture attacker USDC balance from a known ERC-20

    vm.prank(attacker);
    poolManager.donate(key, 100_000_000 /* 100 USDC in 1e6 units */, 0, "");

    uint160 sqrtPriceX96_after = stateView.getSlot0(key.toId()).sqrtPriceX96();
    uint256 usdc_after = usdc.balanceOf(attacker);

    assertEq(sqrtPriceX96_after, sqrtPriceX96_before, "donate must not move slot0");
    assertLt(usdc_after, usdc_before, "donate must decrease attacker USDC");
    assertEq(usdc_before - usdc_after, 100_000_000, "decrease == donation amount");

    // emit evidence JSON to disk for the Python oracle to consume
    // or directly write the measurement into an output JSON file
}
```

`forge test` running this against a `vm.createSelectFork(ETH_RPC_URL)`
records a real measurement. Catch the JSON via `vm.writeFile` or have
the test simply pass and let the Python oracle read the on-chain
diff directly afterwards.

### Step 6.7 — `native mark --status ready`

```bash
.venv/bin/python -m night_shift_security.cli.main native mark \
  --slug uniswap_v4 \
  --name "Uniswap v4" \
  --platform cantina \
  --chain ethereum \
  --contract-address 0x000000000004444c5dc75cB358380D2e3dE08A90 \
  --source-commit 46c6834698c48bc4a463a86d8420f4eb1d7f3b75 \
  --status ready \
  --notes "Measured delta: PoolManager.donate(PoolKey USDC/WETH fee=3000, 100 USDC) moved 100_000_000 USDC units from attacker EOA with zero slot0 drift; evidence=data/security_results/impact/uni_v4_measured_delta.json"
```

Confirm via `native status`:

```
{ "harnesses": { "uniswap_v4": {"status": "ready", ...}}, "ready_count": 1 }
```

### Step 6.8 — Verify cron will resume

```bash
# In a clean subshell:
NSS_HIPIF_PAUSE_FOR_NATIVE=1 bash hermes/scripts/nss-hipif-chain.sh
```

Expect:

```
NSS_HIPIF_PAUSE_FOR_NATIVE=1 but native harness ready_count=1. Proceeding...
```

If you cannot confirm because of network / missing scripts, do NOT
edit `nss-hipif-chain.sh`. Document the precondition behaviour in the
lab entry.

### Step 6.9 — Lab notebook + commit + push

Write `data/security_results/lab_notebook/2026-06-19-uniswap-v4-measured-oracle.md`
with sections:

- **What shipped** (files + counts)
- **Measured delta** (exact numbers)
- **Negative-result safety guarantees** (how the oracle refuses
  non-positive diffs)
- **Cron resume** (whether you confirmed `ready_count=1` and the
  precondition release)
- **Next session** (C3 — `pick_next_target` precondition wiring)

Update AUDIT.md / SPEC.md / CHANGELOG.md as in §4 above.

```bash
git add -A   # all clean files; the user-owned untracked files stay untracked
git commit -m "SPEC 5.0.0 first measured delta: uniswap_v4 MeasuredImpactOracle (audit C2)"
git push origin main
```

---

## 7. Anti-patterns to avoid

These were defeats during C1 + the audit; do not repeat them.

| Anti-pattern | Why it kills the goal |
|--------------|-----------------------|
| Reporting `measured_impact=True` for a non-positive diff | The audit gates stop admitting zero-delta. C2 is the gate that fixes this; do not regress it. |
| Synthesising tx history / balances via random numerics | Counts as fabrication; the audit forbids it. Always read live state. |
| Loosening `submission_gates._v4_candidate_submission_ok` to admit weaker evidence | The audit explicitly says "do not relax gates." Extend the evidence shape, do not weaken the rules. |
| Installing `web3.py` / `eth_abi` / `eth_utils` / `pycryptodome` | Project rules say no new packages. The C1 helper already does canon keccak in pure Python; reuse `uniswap_v4.eth_call` / `uniswap_v4.get_code`. |
| Talking about a "PoolManager USDC/WETH pool that exists" when the PoolId returns zero | That is what gives an all-zero slot0 readout. Initialise the pool first or pick a known-live PoolId (operator note in `goal-reference.md` if available). |
| Skipping the no-RPC test baseline | Drop below 463 → flag the regression and stop. |
| Marking `ready` without a real on-chain delta | Audit C8 gates the cron; flipping early re-enables the broken legacy chain. |
| Forgetting to flip the SPEC.md baseline line | Drift between SPEC.md and lab notebook will block future auditors. |

---

## 8. Checklists

### Opening (5 min)

- [ ] `git status --porcelain` clean except `goal-reference.md`,
      `solodit-api-ref.md`
- [ ] `git log --oneline -3` shows `1c09485`
- [ ] `cat SPEC.md | head -10` shows `5.0.0-draft`
- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q`
      → 463/5
- [ ] `cat data/security_results/loop/native_harness_status.json`
      shows `uniswap_v4 {status: harness_built}`, `ready_count=0`
- [ ] `ls sources/uniswap_v4/repo/src/PoolManager.sol` exists

### Closing (10 min)

- [ ] `.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q`
      → ≥463/5
- [ ] `native status` shows `uniswap_v4 {status: ready}`,
      `ready_count=1`
- [ ] `data/security_results/impact/uni_v4_measured_delta.json` exists,
      parses, has `measured_impact=True`, and contains a positive token
      delta with an explicit attestation that it's not fee-only.
- [ ] Lab notebook entry `2026-06-19-uniswap-v4-measured-oracle.md`
      written and dated.
- [ ] AUDIT.md / SPEC.md / CHANGELOG.md reflect the C2 work and the
      `ready` flip.
- [ ] `git status --porcelain` clean except user-owned untracked files.
- [ ] Push to `origin main`.

---

## 9. If you hit a blocker

- **No RPC** → `ETHEREUM_RPC_URL` empty / unreachable. The oracle
  cannot prove a delta. Option A: stop, write
  `2026-06-19-uniswap-v4-measured-blocked-network.md` describing the
  constraint. Option B (only if user confirms operator feedback): use a
  public RPC endpoint external to the repository's `.env` — but DO
  NOT bake a key into any committed file. Document whatever you do.
- **PoolManager `initialize` reverts** → either the caller lacks the
  approved allowance for the pool key (the pool was initialised
  previously by another account) or the PoolKey ordering is wrong.
  Use a never-initialised PoolKey (currency0 < currency1, fee in
  [100, 500, 3000, 10000], tickSpacing must match a standard fee).
- **`Forge` broadcast fails in the sandbox** → fall back to the Python
  oracle + a manual `donate` constructed transaction. The python path
  always works if you're willing to manage nonce + gas yourself; if you
  can't, document why and leave the broadcast to the operator.
- **`ready_count` doesn't reach 1** → check `native status` for
  whether `ready_count` updates from the belt-and-suspenders logic in
  `native/__init__.py:upsert_harness`, which only increments when
  `entry.status == "ready"`. The doc string in `native/__init__.py`
  has the logic.
- **Engine rejects the new evidence shape**: again — do not edit
  `submission_gates.py` to relax it. Either shape your new evidence to
  match one of the existing 4 patterns, or document in the lab entry
  that a future session must extend the gate. The audit specifically
  says gates stay authoritative.

---

## 10. Files this session is expected to touch

```
src/night_shift_security/impact/measured_oracle.py        (new)
src/night_shift_security/cli/main.py                      (small CLI add)
data/security_results/impact/uni_v4_measured_delta.json   (new)
tests/test_measured_oracle.py                             (new)
foundry/test/UniV4Measure.t.sol                           (new, optional)
data/security_results/lab_notebook/2026-06-19-uniswap-v4-measured-oracle.md (new)
AUDIT.md                                                  (small edit)
SPEC.md                                                   (small edit — baseline line)
CHANGELOG.md                                              (small edit — 2026-06-19 second entry)
```

---

## 11. Final word

Stay narrow. Ship C2 only. Do not touch C3 / C7 / C8 / C9 here. The
audit identified eight failures and the minimum-viable-v5 reaches the
cron-resume line as soon as one harness measures one real on-chain
delta. Get there before broadening.

If the session ends without a measured delta, that's fine — document
the state of the build cleanly and let the next session finish C2.
A clean, well-documented oracle beats a hand-waved `ready` that lies to
the cron and resets the loop.

Commit message suggestion if everything works:

```
SPEC 5.0.0 first measured delta: uniswap_v4 MeasuredImpactOracle (audit C2)
```
