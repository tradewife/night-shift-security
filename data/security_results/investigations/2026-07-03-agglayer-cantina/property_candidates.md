# Agglayer Property Fan-In Candidates

| property_id | surface | invariant | bug class | kill criteria | evidence required |
|---|---|---|---|---|---|
| PROP-AGG-001 | Rust `generate_pessimistic_proof` ↔ Solidity `_getInputPessimisticBytes` | Solidity verifier input exactly matches Rust public values: prev LER, prev PP root, L1 info root, origin network, aggchain hash, new LER, new PP root | Proof encoding mismatch | Field-by-field test vector equality for PP and ALGateway modes | Rust generated vector, Solidity decoded bytes, passing equality assertions |
| PROP-AGG-002 | `NetworkState.apply_batch_header` imported exits | Duplicate imported `global_index` cannot update nullifier tree twice or inflate balances | Replay/nullifier | Duplicate global index always errors before final state commitment | Unit/property test with duplicate imported exit and preserved error |
| PROP-AGG-003 | `NetworkState.apply_batch_header` outgoing exits | Foreign-asset exits cannot underflow local balance | Conservation | Existing and generated overflow attempts all fail with `BalanceUnderflowInBridgeExit` | Rust proptest/fuzz corpus, state deltas |
| PROP-AGG-004 | `verifyPessimisticTrustedAggregator` migration path | Migration bootstrap cannot accept a new LER different from the stored LER and cannot be replayed after flag clear | Migration/state machine | Repeated migration or mismatched LER reverts in local EVM test | Foundry/Hardhat trace, pre/post `isRollupMigrating`, roots |
| PROP-AGG-005 | GER duplicate root path | Duplicate global exit roots cannot create conflicting L1 info leaf counts or stale root acceptance | Temporal/root history | Duplicate `updateExitRoot` leaves `l1InfoRootMap` and `depositCount` consistent across bridge and manager calls | EVM test logs, GER state diffs |
| PROP-AGG-006 | `claimMessage` reentrant external call | Nullifier must be set before receiver callback can reenter claim paths | Reentrancy/replay | Reentrant receiver cannot claim same leaf or paired asset/message leaf | Reentrant mock trace, nullifier bitmap before/after |
| PROP-AGG-007 | Bridge fee/remapped token custody | Leaf amount for fee-on-transfer or remapped wrapped tokens equals actual bridge custody/burn amount, not requested amount | Accounting | For adversarial ERC20, bridge custody plus claims equals leaf amounts | Token balance diffs, BridgeEvent leaf amount |
| PROP-AGG-008 | ALGateway route selection | Proof selector and verifier selector cannot verify against stale, frozen, or wrong route for rollup type | Key/version mismatch | Mismatched route/proof/public values always revert | Gateway route config, revert traces |
| PROP-AGG-009 | L1 info root selection | `l1InfoTreeLeafCount` used by proof must correspond to an existing GER `l1InfoRootMap` entry and stale roots cannot unlock invalid imported exits | Stale root/desync | Invalid or stale root fails proof or claim path | GER map snapshots, proof verification result |
| PROP-AGG-010 | Rollup exit root aggregation | `getRollupExitRoot()` must include exactly current `lastLocalExitRoot` for every registered rollup and no stale/migrating root | Root aggregation | Differential merkle aggregation matches contract output after create, migrate, verify, update | Independent root calculator, EVM state sequence |

## Initial Priority

1. `PROP-AGG-001`, because encoding mismatch can bypass the intended proof semantics.
2. `PROP-AGG-004`, because migration intentionally zeroes `lastLocalExitRoot` during proof input assembly.
3. `PROP-AGG-006`, because `claimMessage` deliberately has no `nonReentrant` guard.
4. `PROP-AGG-003` and `PROP-AGG-007`, because they map directly to the advertised no-over-withdrawal invariant.
