# Lab entry — 2026-06-27 — v6.27 LayerZero V2 Endpoint+ULN302 Hard-First Sidecar (session 30)

## Why this exists

Target the **Immunefi LayerZero omnichain messaging bounty** ($15M critical max, $2M V2 cap) under a hard-first discipline per the user-approved ExitSpecMode plan. EndpointV2 + SendUln302 + ReceiveUln302 only in Phase 1; OFT/Solana/V1/Aptos gated until engine-level signals.

## What was built

| Path | Role |
|------|------|
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/` | **NEW** sidecar investigation root (gitignored) |
| `sources/layerzero/source_manifest.json` | Source commit pins + per-contract sha256 |
| `sources/layerzero/bytecode_manifest.json` | Empty-pin placeholder for live-RPC bytecode fetching |
| `sources/layerzero/repo/` | Sparse clone of `LayerZero-Labs/LayerZero-v2 @ audit tag (0990059…3fb4c3)` |
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/property_fanin.md` | Canonical PROP-PKT-001..007 table |
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/strategies/*.md` | 3 strategy fan-out |
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/runs.jsonl` | 3 attempts logged |
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/summary.json` | Phase-1 close status |
| `data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/adjudication/H*.json` | 3 per-discovery adjudication files |
| `src/night_shift_security/native/layerzero.py` | Python harness + packet-codec helpers |
| `tests/test_native_layerzero.py` | 17 pytest checks |
| `foundry/test/LayerZeroEndpointHarness.t.sol` | 5 fork-mode tests (3 skipped without ETHEREUM_RPC_URL) |
| `foundry/test/LayerZeroULN302LifecycleFalsifier.t.sol` | 8 determinstic falsifier tests |

## Engine reachability this round

**Deterministic engine reach.** Across three (3) clean runs:

1. `forge test --match-path test/LayerZero*.sol` — exit 0, 10 passed, 0 failed, 3 skipped (fork-mode fork-tests skipped without ETHEREUM_RPC_URL).
2. `PYTHONPATH=src python3 -m pytest tests/test_native_layerzero.py` — 17 passed, 0 failed.
3. `forge test --root foundry -v` (LayerZero*-only) — same clean run.

**Engine status says:** `engine_reach_status = "deterministic_codec_pure_pure_layer_reached"`. `submit_ready` remains **0** (Phase gate: no measured DELTA_WEI/IMPACT_USD>0; no fork-mode mainnet confirmation).

## Same vs different vs prior sessions

| Datapoint | Outcome |
|-----------|---------|
| Ethena (v6.1) | honest-zero, uint64-truncation probe reached EVM bytecode |
| Marginfi v2 (v6.2) | honest-zero, sentinel-default discovery gap (canonical PDA unknown) |
| Kamino multi-attempt (v6.3) | honest-zero, 3 disjoint frames falsified |
| 3F Grunt Cantina (v6.5–v6.20 H1..H12) | honest-zero |
| Zest V2 (v6.21) | LOW finding (liq-penalty-max bug), honest-zero on the rest |
| Midas sidecar (v6.25) | sidecar engine-reach H2 directional signal |
| Lombard (v6.24/26) | honest-zero across consortium, mailbox, bridge, corridor, lbtc |
| **LayerZero V2 hard-first (this session, v6.27)** | **engine-level honest-zero (codec-only)** |

**Audit-saturation framing remains bounded (NOT asserted).** Per SPEC v6.x §3.2. Phase-1 close is recommended: rotate to a fresh, less-overlapping target rather than push hard-first saturation claim.

## Mandatory Falsification Protocol

Honored:

1. Falsifier pass (`testPacketHeaderLengthIs81`, `testZeroDvnConfigIsForbiddenByInvariant`, `testNondCollidingOappsNeverShareNonceBucket`): all green, no false-positive drift.
2. Engine-reach confirmed at codec layer; production reachability requires LayerZero-v2 forge-library install (deferred).
3. Audit-saturation framing: NOT asserted (bounded only).

## Hard cutoffs honored

- `day_shift/current.md` and `day_shift/next.md` **NOT touched**. Sidecar status lives in `day_shift/layerzero_sidecar.md`.
- No `forge install` of the LayerZero-v2 monorepo into `foundry/lib/layerzero-v2` (the repo is npm yarn workspace; forge install would require remapping). Codec + keccak-based falsifiers cover Phase-1 reachability.
- 3 fork-mode tests skipped without `ETHEREUM_RPC_URL`; document the deferral rather than broadcasting.

## Engine output

- `forge build --root foundry` → exit 0
- `forge test --root foundry --match-path test/LayerZero*.sol` → exit 0, 10 passed / 3 skipped
- `pytest tests/test_native_layerzero.py` → 17 passed / 0 failed

## Next session

- Sequence: Either (a) close sidecar (~`day_shift/layerzero_sidecar.md#closing-2026-06-27`) + rotate to next fresh target, OR (b) install `LayerZero-v2` forge library + push Phase 2A OFT/V1 contingent.
- Rarely: a Phase 2A expansion is warranted only when (i) the forged DVN confirmation-downgrade attack class surfaces an engine-level signal in a future property-table round, AND (ii) the OApp-easy-path class is widened beyond configuration dependency.

## Skill notes

- `operator-recon` ✓ (sparse clone + manifest pinned).
- `ultrafuzz-discovery` ✓ (property fan-in + strategy fan-out + falsifier runs + adjudication).
- `operator-exploit` deferred (no PoC yet, no engine-level signal).
- `submission-reporting` deferred (no submittable finding).
