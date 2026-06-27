# LayerZero Sidecar Status — v6.27.0-session30

Status: **open** (2026-06-27)

## Phase 1 outcome

| Item | Status |
|------|--------|
| EndpointV2 hard-first scope | engine-level honest-zero (codec reachability) |
| SendUln302 sync | clean |
| ReceiveUln302 sync | clean |
| Source pin | `LayerZero-v2 @ audit tag (0990059…3fb4c3)` |
| `forge build` | exit 0 |
| `forge test --match-path test/LayerZero*.sol` | 10 PASS / 3 SKIP (fork-mode w/o RPC) |
| `pytest tests/test_native_layerzero.py` | 17 PASS / 0 FAIL |
| `submit_ready` | 0 |

## Sidecar discipline

- Investigation workspace gitignored per AGENTS.md.
- This status doc is the sole cross-session pointer.
- `day_shift/current.md` and `day_shift/next.md` remain unchanged (carry-forward from the Lombard session).
- No push of foundry harnesses or pytest tests other than this status doc + SPEC + CHANGELOG.

## Decision gate (Phase 2)

- **Phase 2A** (OFT + V1 + Aptos) opens only if Phase 2A contingent engine-level signal is reported (i.e., a forged DVN confirmation-overwrite attack demonstrates reachable code paths via a future property-table round).
- **Rotate-to-next-target** decision is the default if no Phase 2A signal emerges within the next 1-2 sessions; the empirical-FNR ceiling remains bounded (4 datapoints, all honest-zero).

## Operator TODOs

1. Refresh `sources/layerzero/bytecode_manifest.json` runtime sha256 fields when `ETHEREUM_RPC_URL` is present (any external env).
2. Optional: install `LayerZero-v2` as a forge library expansion (`forge install LayerZero-Labs/LayerZero-v2 --root foundry/lib/layerzero-v2`).
3. Run forge test on a real fork before publishing any candidate (fork-mode skipped locally without RPC).
4. Confirm the 6 source-pinned selectors against deployed bytecodes via `forge inspect` at Etherscan.

## Files referenced

- `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/` — full investigation pack
- `sources/layerzero/source_manifest.json`, `bytecode_manifest.json`, `repo/`
- `src/night_shift_security/native/layerzero.py` + `tests/test_native_layerzero.py`
- `foundry/test/LayerZeroEndpointHarness.t.sol` + `foundry/test/LayerZeroULN302LifecycleFalsifier.t.sol`
- SPEC.md (v6.27.0-layerzero-endpoint-uln302-sidecar-session30) + CHANGELOG.md (v6.27 entry)
