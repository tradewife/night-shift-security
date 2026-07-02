# Agglayer Cantina — Round 1 Lab Notebook

**Date:** 2026-07-03  
**Target:** Agglayer (Cantina bounty)  
**Investigation:** `data/security_results/investigations/2026-07-03-agglayer-cantina/`

## Same vs prior NSS work

- Fresh target; no prior Agglayer deep-dive in this repo.
- Handoff artifacts from prior turn: setup, invariants, property_candidates, strategies, codegraph outputs.

## What ran (executable)

| Command / suite | Result |
|-----------------|--------|
| `PolygonRollupManager-Pessimistic.test.ts` | 9/9 pass |
| `real-prover-sp1/e2e-verify-proof.test.ts` | 3/3 pass |
| `UpgradeToPP.test.ts` | 4/4 pass |
| `BridgeV2ClaimMessageReentrancy.test.ts` | 3/3 pass |
| `AggLayerGateway.test.ts` | 14/14 pass |
| `AggchainFEP` + `PolygonRollupManagerAL-FEP` | 24/24 pass |
| `forge AgglayerGERFuzz` | 256 fuzz runs pass |
| `cargo test -p pessimistic-proof-core` | 4/4 pass |
| `pessimistic-proof-test-suite` overflow test | blocked (`protoc`) |

## Adjudication

- **Killed (reviewed):** Solidity/Rust public-input encoding parity; migration `InvalidNewLocalExitRoot`; `claimMessage` reentrancy replay; gateway PP route checks.
- **Open (next pressure):** `globalIndex` / nullifier bitmap across mainnet vs rollup encodings; fee-on-transfer leaf amounts; FEP `onVerifyPessimistic` binding of `aggchainData` to proof public values; duplicate GER root vs `l1InfoTreeLeafCount` service assumptions.

## Submission state

- `submit_ready`: **false**
- No `production_defect` promoted.

## Round 2 (continuation)

- **protoc** = `protobuf-compiler` / `protoc` (not “protec”): required by `sp1-prover-types` build script in `sources/agglayer/repo`. Installed **libprotoc 28.3** to `~/.local/bin` (no sudo).
- **H-IDX-001 probe:** `AgglayerGlobalIndexProbe` **5/5** pass after harness fix (`testInit` on `AgglayerBridgeHarness`). Evidence: `investigations/.../evidence/globalindex-probe-result.md`.
- **Build state:** `agglayer-contracts` has `node_modules`, Hardhat `artifacts/`, prior round Hardhat suites green; `cargo pessimistic-proof-core` 4/4; full `e2e_local_pp_overflow_attempt` still pending long compile.

## Reflection

The messy core is less “missing access control” and more **four-ledger equivalence** (Rust state, SP1 public values, manager rollup roots, bridge claim bitmap). Existing upstream tests already cover the highest-risk encoding and migration paths; novel yield likely needs differential harnesses on index encoding and token custody edges not fully stressed in default suites.
