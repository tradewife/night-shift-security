# H-IDX-001 — GlobalIndex / nullifier differential probe (round 2)

**Date:** 2026-07-03  
**Command:** `cd sources/agglayer-contracts/repo && forge test --match-contract AgglayerGlobalIndexProbe`

## Result

- **5/5 passed** (512 fuzz runs across two fuzz tests @ 256 each)
- `testFuzz_mainnetGlobalIndex_roundTrip`
- `testFuzz_rollupGlobalIndex_roundTrip`
- `test_revert_invalidGlobalIndex_highBitsSet`
- `test_mainnetZkEvmLegacyNullifierEncoding`
- `test_rollupNullifierEncoding_notConfusedWithMainnetLegacy`

## Harness notes

- Probe in target clone: `sources/agglayer-contracts/repo/test/forge/fuzz/AgglayerGlobalIndexProbe.t.sol`
- `AgglayerBridgeHarness.testInit` enables proxy-backed nullifier bitmap tests (Foundry-only)

## Adjudication (preliminary)

- **H-IDX-001** decode round-trip and mainnet vs rollup nullifier separation: no defect in probe scope
- Rust nullifier tree vs Solidity bitmap differential still open (PROP-AGG-002)
