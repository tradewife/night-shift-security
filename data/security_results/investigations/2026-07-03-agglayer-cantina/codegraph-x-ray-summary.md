# Codegraph X-Ray Summary

## Primary Target Subsystem

Pessimistic proof settlement path:

1. Rust proof state transition: `pessimistic-proof-core/src/local_state/mod.rs`
2. Rust public values: `pessimistic-proof-core/src/proof.rs`
3. L1 verification and root consolidation: `contracts/AgglayerManager.sol`
4. Bridge deposit/claim/nullifier mechanics: `contracts/AgglayerBridge.sol`
5. Global exit root and L1 info root history: `contracts/AgglayerGER.sol`

This is the highest-blast-radius subsystem because a mismatch between Rust public values, verifier input encoding, rollup root consolidation, and bridge claim roots could produce cross-chain over-withdrawal or invalid settlement acceptance.

## Codegraph Runs

- `codegraph init sources/agglayer-contracts/repo`
- `codegraph init sources/agglayer/repo`
- `codegraph explore -p sources/agglayer-contracts/repo verifyPessimisticTrustedAggregator AgglayerBridge AgglayerGER --max-files 12`
- `codegraph impact -p sources/agglayer-contracts/repo verifyPessimisticTrustedAggregator`
- `codegraph callees -p sources/agglayer-contracts/repo verifyPessimisticTrustedAggregator`
- `codegraph callers -p sources/agglayer-contracts/repo updateExitRoot`
- `codegraph explore -p sources/agglayer/repo generate_pessimistic_proof apply_batch_header ConstrainedValues --max-files 12`
- `codegraph impact -p sources/agglayer/repo generate_pessimistic_proof`

Raw outputs are stored under `codegraph/`.

## Verified High-Signal Anchors

- `AgglayerManager.verifyPessimisticTrustedAggregator`, lines 1300-1409: role-gated proof verification, migration special case, public input assembly, verifier/gateway dispatch, `lastLocalExitRoot` and `lastPessimisticRoot` update, GER update.
- `AgglayerManager._getInputPessimisticBytes`, lines 1655 onward: encoding boundary between Rust public values and Solidity verifier inputs.
- `AgglayerManager.getRollupExitRoot`, lines 1505 onward: aggregated rollup root used by `AgglayerGER`.
- `AgglayerBridge.bridgeAsset`, lines 290-390: deposit leaf creation and asset custody/burn semantics.
- `AgglayerBridge.claimAsset`, lines 537-692: claim proof, nullifier update, transfer/mint branch selection.
- `AgglayerBridge.claimMessage`, lines 697-771: intentionally non-reentrant external call path after nullifier update.
- `AgglayerBridge._verifyLeafAndSetNullifier`, `_verifyLeaf`, `_setAndCheckClaimed`, lines 788, 898, 990: claim inclusion and replay-prevention core.
- `AgglayerGER.updateExitRoot`, lines 87-135: only bridge or manager can update roots, and duplicate global roots do not append new L1 info leaves.
- `pessimistic-proof-core/src/local_state/mod.rs`, lines 61-176: imported exits add balance, outgoing bridge exits subtract balance, nullifier tree updates prevent replay.
- `pessimistic-proof-core/src/proof.rs`, lines 155-294: public values include prev/new local exit roots, prev/new pessimistic roots, L1 info root, origin network, and aggchain hash.

## Initial Interpretation

The likely bug density is not in a single access-control check. It is in equivalence between four ledgers:

1. Rust `NetworkState` balance/nullifier/exit roots.
2. SP1 public values and verifier input encoding.
3. Solidity `RollupData.lastLocalExitRoot` and `lastPessimisticRoot`.
4. Bridge claim roots and nullifier bitmap.

The first executable campaign should force these ledgers out of sync with migration mode, duplicate GER roots, empty-root zero mapping, fee-on-transfer/remapped tokens, and bridge-message value branches.
