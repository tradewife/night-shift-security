# LayerZero Sidecar Status — v6.28.0-session31

Status: **open** (2026-06-27)

## Phase 1 outcome

| Item | Status |
|------|--------|
| EndpointV2 hard-first scope | engine-level honest-zero (codegraph-hardened sequence reachability) |
| SendUln302 sync | clean |
| ReceiveUln302 sync | clean |
| Source pin | `LayerZero-v2 @ audit tag (0990059…3fb4c3)` |
| `codegraph init` | completed, but current build indexed only 5 non-Solidity files |
| `forge build` | exit 0 |
| `forge test --match-path test/LayerZero*.sol` + OFTAdapterReentrancy | 17 PASS / 0 SKIP (incl. Direction C dead-DVN fork + Direction M CEI flag) |
| `pytest tests/test_native_layerzero.py` | 17 PASS / 0 FAIL |
| Local-only upstream hardening tests | 4 PASS / 0 FAIL |
| `submit_ready` | 0 |

## Sidecar discipline

- Investigation workspace gitignored per AGENTS.md.
- This status doc is the sole cross-session pointer.
- `day_shift/current.md` and `day_shift/next.md` remain unchanged (carry-forward from the Lombard session).
- No push of local-only upstream LayerZero source-clone tests; only this status doc + SPEC + CHANGELOG carry forward.

## Direction C — dead-DVN / isSupportedEid contradiction

- **Direction C fork PoC** (`foundry/test/LayerZeroEndpointIsSupportedEidAudit.t.sol`, local-only): confirms `isSupportedEid == true` for 5 EIDs while the default ULN config contains `0x...dEaD` as a required DVN for 2 of them (30155/Tac, 30301/Read chan). Quote path reverts for 4/5 EIDs. Impact: default-config liveness/availability issue, not a direct fund-theft vector. `submit_ready` remains 0.

## Direction M — OFTAdapter `_credit` CEI violation

- **Direction M PoC** (`foundry/test/OFTAdapterReentrancy.t.sol`, local-only): mirror demonstrating the OFTAdapter._credit() state-before-transfer pattern that allows reentrancy via non-standard (ERC777-like) underlying ERC20 tokens. Confirms the temporary inflation of `availableToSend` during the callback window. Practical impact on default ERC20 deployments is bounded (the symmetric balance update reconciles), but the pattern is a valid defensive flag for any OFTAdapter wrapping a non-standard token. **submit_ready** remains 0.

- See lab notebook `2026-06-27-v6-28-layerzero-codegraph-hardening-session31.md` Direction C and M sections for full tables and assessments.

## Decision gate (Phase 2)

- **Phase 2A** (OFT + V1 + Aptos) opens only if a stronger signal emerges than the v6.28 codegraph-hardened lifecycle checks (for example, a real stale-lib grace leak, quorum ghosting, or DVN overwrite path that survives fork replay).
- **Rotate-to-next-target** decision is the default if no Phase 2A signal emerges within the next 1-2 sessions; the empirical-FNR ceiling remains bounded (4 datapoints, all honest-zero).

## Operator TODOs

1. Refresh `sources/layerzero/bytecode_manifest.json` runtime sha256 fields when `ETHEREUM_RPC_URL` is present.
2. Decide whether to normalize the local clone for better Solidity-aware `codegraph` coverage, or keep the manual structural-map fallback.
3. Replay the 4 new local-only upstream hardening tests on a real fork before publishing any candidate.
4. Confirm the 6 source-pinned selectors against deployed bytecodes via `forge inspect` or equivalent.

## Files referenced

- `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/` — full investigation pack
- `data/security_results/investigations/2026-06-27-v6-28-layerzero-codegraph-hardening/` — codegraph hardening pack
- `sources/layerzero/source_manifest.json`, `bytecode_manifest.json`, `repo/`
- `src/night_shift_security/native/layerzero.py` + `tests/test_native_layerzero.py`
- `foundry/test/LayerZeroEndpointHarness.t.sol` + `foundry/test/LayerZeroULN302LifecycleFalsifier.t.sol` + `foundry/test/LayerZeroEndpointIsSupportedEidAudit.t.sol` + `foundry/test/OFTAdapterReentrancy.t.sol`
- `sources/layerzero/repo/protocol/test/EndpointV2CodegraphHardening.t.sol`
- `sources/layerzero/repo/messagelib/test/ReceiveUln302CodegraphHardening.t.sol`
- SPEC.md (v6.28.0-layerzero-endpoint-uln302-codegraph-hardening-session31) + CHANGELOG.md (v6.28 entry)
