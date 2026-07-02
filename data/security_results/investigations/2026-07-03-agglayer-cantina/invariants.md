# Agglayer Verified Invariant Catalog

## Enforced Guards

### G-1: Pessimistic verification is trusted-aggregator only

- Source: `contracts/AgglayerManager.sol:1300`
- Evidence: `verifyPessimisticTrustedAggregator` is `external onlyRole(_TRUSTED_AGGREGATOR_ROLE) nonReentrant`.
- Attack pressure: role compromise is out of scope unless reachable through gateway/timelock/upgrades, but malformed proofs from an authorized aggregator remain in scope.

### G-2: State-transition chains cannot use pessimistic verifier path

- Source: `contracts/AgglayerManager.sol:1310-1313`
- Evidence: `VerifierType.StateTransition` reverts.
- Attack pressure: test verifier-type transitions through `updateRollup` and migration.

### G-3: Pessimistic verifier type must have empty `aggchainData`

- Source: `contracts/AgglayerManager.sol:1316-1321`
- Evidence: `VerifierType.Pessimistic && aggchainData.length != 0` reverts.
- Attack pressure: ALGateway encoding path differs and should be differential-tested against pure PP path.

### G-4: GER updates are restricted to bridge or rollup manager

- Source: `contracts/AgglayerGER.sol:87-102`
- Evidence: only `bridgeAddress` updates `lastMainnetExitRoot`; only `rollupManager` updates `lastRollupExitRoot`.
- Attack pressure: duplicate root behavior and timing metadata still need invariant tests.

### G-5: Claims must target the local network

- Source: `contracts/AgglayerBridge.sol:551-553`, `709-711`
- Evidence: `claimAsset` and `claimMessage` revert unless `destinationNetwork == networkID`.

## Single-Component Invariants

### I-1: Pessimistic public inputs must bind previous and new roots

- Source: `pessimistic-proof-core/src/proof.rs:155-169`, `237-294`
- Invariant: verifier public values must bind `prev_local_exit_root`, `prev_pessimistic_root`, `l1_info_root`, `origin_network`, `aggchain_hash`, `new_local_exit_root`, and `new_pessimistic_root`.
- Evidence gate: compare Rust `PessimisticProofOutput::bincode_codec()` layout against Solidity `_getInputPessimisticBytes`.

### I-2: Imported exits cannot be replayed

- Source: `pessimistic-proof-core/src/local_state/mod.rs:70-101`
- Invariant: every imported bridge exit must prove inclusion under `l1_info_root`, then update the local nullifier tree for the `global_index`.
- Evidence gate: mutation test duplicate `global_index` across a multi-batch header and expect nullifier verification failure.

### I-3: Outgoing foreign-asset bridge exits cannot exceed local balance

- Source: `pessimistic-proof-core/src/local_state/mod.rs:145-160`
- Invariant: for non-native token exits, `new_balance = old_balance - amount` and underflow reverts.
- Evidence gate: existing `e2e_local_pp_overflow_attempt` plus adversarial fee-token/remapped-token variants.

### I-4: Incoming foreign-asset imported exits increase local balance

- Source: `pessimistic-proof-core/src/local_state/mod.rs:102-117`
- Invariant: imported exits to the origin network add amount to the token balance unless token origin equals current network.
- Evidence gate: differential proof with imported native vs foreign token exits.

### I-5: Empty local exit root is zero-mapped only at public-input boundary

- Source: `pessimistic-proof-core/src/proof.rs:279-294`
- Invariant: Rust internal empty LER hash is mapped to `0x00..00` only in public outputs, not in state mutation logic.
- Evidence gate: prove first bridge vs no-bridge transition and compare Solidity migration check behavior.

### I-6: Claim replay prevention happens before external message execution

- Source: `contracts/AgglayerBridge.sol:788`, `697-771`
- Invariant: `claimMessage` must set the nullifier before calling `destinationAddress`.
- Evidence gate: reentrant receiver attempts `claimMessage` and `claimAsset` during callback; same leaf must stay unclaimable.

## Cross-Component Invariants

### X-1: Solidity verifier input must equal Rust public values

- Sources: `AgglayerManager._getInputPessimisticBytes`, `pessimistic-proof-core/src/proof.rs`
- Invariant: Solidity input encoding must commit to the same fields, order, zero-root mapping, origin network, and aggchain hash as Rust/SP1.
- Evidence gate: generate test vector with Rust `ppgen`, decode Solidity calldata, and assert field-by-field equality.

### X-2: Manager root consolidation must make bridge claims possible only for proven LERs

- Sources: `AgglayerManager.verifyPessimisticTrustedAggregator`, `AgglayerManager.getRollupExitRoot`, `AgglayerGER.updateExitRoot`, `AgglayerBridge._verifyLeaf`
- Invariant: an L2 local exit root should become claimable on L1 only after a verified pessimistic transition updates manager state and GER history.
- Evidence gate: fork/local sequence with claim before verification, after verification, duplicate GER update, and stale `l1InfoTreeLeafCount`.

### X-3: Migration bootstrap must not allow LER rollback or replay

- Source: `AgglayerManager.sol:1329-1346`
- Invariant: during migration, `newLocalExitRoot == rollup.lastLocalExitRoot`, then internal previous LER is zeroed for proof input and migration flag is cleared exactly once.
- Evidence gate: test migration with non-empty existing LER, zero LER, repeated migration call, and proof whose public previous LER differs from expected.

### X-4: Gateway route versioning must not verify a proof under the wrong PP key

- Sources: `AgglayerManager.sol:1365-1376`, `AgglayerGateway.sol` route-management functions.
- Invariant: ALGateway route selector and verifier selector embedded in `proof` must map to the intended PP verification key and rollup verifier type.
- Evidence gate: stale/frozen/default route tests with mismatched public inputs.

## Economic Invariants

### E-1: A dishonest chain cannot withdraw more foreign assets than its local balance

- Sources: Rust local balance tree update and Solidity bridge claim path.
- Invariant: cumulative foreign-token exits settled by a chain must be bounded by imported deposits plus prior local balance.
- Evidence gate: executable stateful proof generation plus L1 settlement/claim simulation.

### E-2: Bridge custody plus wrapped supply must match settled leaves minus claims

- Sources: `AgglayerBridge.bridgeAsset`, `claimAsset`, `_bridgeWrappedAsset`, `_claimWrappedAsset`.
- Invariant: for a token origin network, bridge escrow or wrapped token supply deltas must equal the canonical settled leaf deltas after nullifiers.
- Evidence gate: fee-on-transfer token, non-standard wrapped token, WETH/gas-token branches.

## Dropped or Deferred Candidates

- Timelock delay bypass: important but secondary until core settlement equivalence has executable coverage.
- Frontend/service sync bugs: out of scope unless they cause accepted invalid settlement or claimability changes.
- Pure gas griefing: likely out of scope and not pursued.
