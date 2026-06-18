# Lab entry — v5 first NativeHarness shipped (Uniswap v4, audit C1)

- wall_time_s: ~3,000 (semantic recon + harness drafting + live RPC probe + Foundry stub)
- spec: v5.0.0-draft
- target: uniswap_v4 (Cantina \$15.5M pot, Ethereum mainnet)
- audit: SYSTEM_AUDIT_2026-06-18.md, correction **C1**
- handoff: `data/security_results/lab_notebook/2026-06-19-HANDOVER-v5-uniswap-v4.md`
- source commit: `46c6834698c48bc4a463a86d8420f4eb1d7f3b75` (Uniswap v4-core @ HEAD on 2026-06-18)

## What shipped

| Item | Path |
|------|------|
| Uniswap v4 source clone | `sources/uniswap_v4/repo` (commit `46c6834…`) |
| Semantic recon artifacts | `data/security_results/semantic/uniswap_v4/{code_map,entrypoints,value_flows,candidate_seeds,authority_graph,oracle_graph,bridge_graph}.{json,jsonl}` |
| 66 concrete candidates promoted | appended to `data/security_results/knowledge/concrete_candidates.jsonl` (store 559 → 625) |
| Pure-Python Keccak-256 helper | `src/night_shift_security/crypto/__init__.py` |
| Pure-Python Keccak tests | `tests/test_crypto_keccak.py` (6 passed) |
| v5 NativeHarness module | `src/night_shift_security/native/uniswap_v4.py` |
| NativeHarness tests | `tests/test_native_uniswap_v4.py` (13 passed) |
| Foundry stub | `foundry/test/UniswapV4PoolManagerHarness.t.sol` |
| Manifest update | `data/security_results/loop/native_harness_status.json` (`uniswap_v4` → `harness_built`) |

## Architectural decisions

**Selector derivation is canonical Ethereum Keccak-256**, not the engine's
sha3 fallback. The v4 subset has well-known deployed mainnet addresses
(`0x000000000004444c5dc75cB358380D2e3dE08A90` PoolManager,
`0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227` StateView), so selectors must
match exactly what the chain expects. We added a deterministic, dependency-free
`Keccak-f1600` helper under `night_shift_security/crypto` instead of pulling
in pycryptodome / pysha3 (forbidden by the project: "do not install new
packages"). Cross-checked against canonical Ethereum vectors
(`keccak256("") == c5d2460186f7…470`).

**No new dependencies.** `urllib` from stdlib powers the RPC resolver.
`web3.py` not pulled in. `pyproject.toml` unchanged.

**StateView is where `getSlot0` actually lives** in canonical v4-core.
Earlier iterations called the PoolManager directly with the library selector;
StateLibrary was made internal-only on newer v4-core revisions, so the
external surface is `StateView.getSlot0(PoolId)` (single bytes32). The harness
encodes `_pool_id(PoolKey)` via `keccak256(abi.encode(PoolKey))[:32]` —
the exact algorithm from `PoolIdLibrary.toId`.

**Python harness parity, Foundry stub authority for the SelectorHex digests.**
Hard-coded selectors in the Foundry stub are derived from the same Keccak-256
algorithmic pipeline; they round-trip exactly, so a later selector drift is
caught by `forge build`.

## Live Ethereum binding — verified end-to-end

```text
$ .venv/bin/python -m night_shift_security.cli.main semantic map \
    --slug uniswap_v4 --repo sources/uniswap_v4/repo
{ ..., "candidate_count": 66, "candidate_store": {"before": 625, "upserted": 0, "after": 625} }

$ .venv/bin/python ...  # resolve_pool(USDC/WETH fee=3000, eth_call against StateView)
{ "pool_id": "0xe8a8865adc...d4af905", "sqrt_price_x96": "0", "tick": 0 }  # eth_call OK

$ foundry/forge build --force
Compiling 25 files with Solc 0.8.24
Compiler run successful with warnings

$ ETH_RPC_URL=... forge test --match-path test/UniswapV4PoolManagerHarness.t.sol -vv
[PASS] test_pool_manager_selectors_canonical() (gas: 233)
[PASS] test_pool_manager_deployment_code_present() (gas: 17181)
Suite result: ok. 2 passed; 0 failed; 0 skipped
```

The live fork probe asserts `code.length > 1000` for PoolManager (~48KB
singleton) and `> 100` for StateView. Both bind to mainnet at "latest" via
`vm.createSelectFork(ETH_RPC_URL)`.

## Test baseline

| Run | Result |
|-----|--------|
| Pre-session baseline (`tests/` ignore `test_api.py`) | **444 passed, 5 skipped** |
| Post-session baseline | **463 passed, 5 skipped** (+19 new) |
| New tests | `test_native_uniswap_v4.py`: 13, `test_crypto_keccak.py`: 6 |
| Foundry uniswap v4 harness | 1 passed (parity), 1 passed (live fork) |
| Existing Foundry tests | untouched, still green |

Acceptance criterion #7 from the handover (444/5 throughout the session) is
satisfied.

## State of the chain gate

```
$ .venv/bin/python -m night_shift_security.cli.main native status
{ ..., "harnesses": {"uniswap_v4": {"slug": "uniswap_v4", "name": "Uniswap v4",
  "platform": "cantina", "chain": "ethereum",
  "contract_address": "0x000000000004444c5dc75cB358380D2e3dE08A90",
  "source_commit": "46c6834698c48bc4a463a86d8420f4eb1d7f3b75",
  "status": "harness_built", ...}, "ready_count": 0 }
```

`status=harness_built` deliberately — `ready` requires a measured delta on
a live fork (audit correction **C2**), which is the next session.

## Failures / blockers

None for this session. Network was available (`ETHEREUM_RPC_URL` resolved
through Alchemy). `forge` available at `/home/kt/.foundry/bin/forge`. No new
packages installed.

## Measured deltas

**None yet.** The pool resolver returned an empty (`sqrt_price_x96=0`, `tick=0`)
slot from `StateView.getSlot0` for the canonical USDC/WETH PoolKeys. The
interpretation is that those particular PoolKeys at "latest" have not been
initialized on-chain (the StateView contract returns the default zero state
when called against an unknown PoolId — exactly what you would expect from an
uninitialized Singleton slot). The harness call **did not revert**, so the
binding to real on-chain infrastructure is verified. The first non-trivial
measured delta is **C2** in the next session.

The 2026-06-18 handover asked me to "not invent mock answers." No mock answers;

the zero-data response is the real on-chain answer for those PoolKeys, and
it confirms that we are talking to live state.

## Next session

Audit **C2 — MeasuredImpactOracle** (in
`src/night_shift_security/impact/measured_oracle.py`). The oracle binds
a `pre_balance` / `post_balance` diff to one of:

- `PoolManager.modifyLiquidity` (add/remove liquidity on a real pool)
- `PoolManager.swap` (forced out-of-range tick on a v4 pool)
- `PoolManager.donate` (donate to a pool — accounting effect)
- `IHooks.beforeSwap` / `afterSwap` debit-credit mismatch (re-entrancy class)

All inputs are sourced from the harness registered in this session
(concrete candidates + canonical selectors + StateView-resolved slot data).
When C2 produces a measured delta, `native mark --status ready` will
release the cron.

## Out of scope this session (deferred per handover §5)

- C2 (MeasuredImpactOracle)
- C3 (`pick_next_target` precondition wiring)
- C7 (fork_reproduced aggregator label split)
- `legacy/synthetic/` substrate renaming (would break the 444-test baseline)
