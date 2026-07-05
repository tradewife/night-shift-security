# Codegraph X-Ray Summary: Symbiotic Cantina Bounty

**Date**: 2026-07-05
**Target**: Symbiotic Shared Security Protocol (Core & Rewards V2)
**Bounty**: Cantina $500k Max (Critical)

## Primary Target Subsystem

**Chosen**: VaultV2 + UniversalDelegator + Adapter allocation/deallocation/sweeping state machines intersecting with Slasher/Resolver veto logic and Rewards V2 distribution/curator flows.

**Rationale**: This subsystem represents the highest density of interacting trust boundaries, unusual V2 design choices, and economic invariants:

1. **VaultV2** (src/contracts/vault/VaultV2.sol): Central accounting hub - manages deposits, withdrawals, fees (management/performance/protocol), share price tracking via Checkpoints, and delegates asset management to UniversalDelegator via pull/push
2. **UniversalDelegator** (src/contracts/delegator/UniversalDelegator.sol): Multi-adapter allocation engine - ordered adapter routing, absolute + share limits, auto-allocate, pending deallocation state machine, sweepPending orchestration
3. **Slasher/VetoSlasher** (src/contracts/slasher/): Network-initiated slashing with resolver-based veto, capture timestamp bounds, cumulative slash tracking, burner hooks
4. **Rewards V2** (rewards-v2/src/contracts/): Dual reward mechanisms - vault snapshot (proportional to active shares) + cumulative Merkle (off-chain construction, dual signatures, protocol fees)

## Codegraph Findings

- **4,771 nodes, 15,818 edges** indexed from symbioticfi/core
- **High-centrality clusters**: VaultV2, UniversalDelegator, BaseSlasher, BaseDelegator as primary hubs
- **Complex call chains**:
  - `VaultV2._deposit()` → `accrueInterest()` → `UniversalDelegator.onDeposit()` → `_sweepPending()` → `WithdrawalQueue.fill()` → `_allocateAll()`
  - `VaultV2._withdraw()` → `UniversalDelegator.onWithdraw()` → `_deallocateAll()` → adapter.deallocate()
  - `Slasher.slash()` → `_slashableStake()` → delegator.stakeAt() → `_delegatorOnSlash()` → `_vaultOnSlash()` → `_burnerOnSlash()`
  - `VetoSlasher.executeSlash()` → resolver checks at two timestamps → slashableStake → slash execution
  - `UniversalDelegator.sweepPending()` → multi-adapter deallocate → WithdrawalQueue.fill() → requestDeallocate for remaining

## Key Architecture Observations

1. **Reentrancy protection**: VaultV2 uses OpenZeppelin's ReentrancyGuardTransient via ERC4626Upgradeable; UniversalDelegator uses nonReentrant modifier. Some internal functions (like `_sweepPending`, `_allocateAll`, `_deallocateAll`) are called without reentrancy protection by guarded public functions.

2. **Sweep-pending gate**: Multiple allocation functions check `_sweepPending() > 0` and return 0 early if pending. This is a critical state gate that controls when allocations can proceed.

3. **Checkpoint-based accounting**: Total supply and balances use OpenZeppelin Checkpoints.Trace256 for historical lookups needed by slashing and rewards. Fee shares are minted but not checkpointed until the next transfer.

4. **Fee-on-transfer unsupported**: VaultV2 explicitly disallows fee-on-transfer, rebasing, and nonstandard assets.

5. **Resolver veto timing**: VetoSlasher has complex time window logic - vetoDuration must be < epochDuration, resolverSetEpochsDelay must be >= 3 epochs, and executeSlash checks resolver at both captureTimestamp and current-1.

6. **Merkle rewards trust**: CumulativeMerkleRewards requires dual signatures (protocol + rewarder) for distribution creation, with cross-chain EIP-712 typed data. Claim uses msg.sender in the leaf.

## Derived Invariant Counts

| Category | Count | Description |
|----------|-------|-------------|
| G-N (Guards) | 8 | Per-call access control and bounds checks |
| I-N (Single-component) | 14 | Internal accounting invariants |
| X-N (Cross-component) | 9 | Multi-contract invariants |
| E-N (Economic) | 6 | Economic invariants and value relationships |
| **Total** | **37** | |
| **Dropped** | 5 | Lacked concrete code/grep evidence |

## Recommended Focus for ultrafuzz-discovery

1. **Allocation/slashing concurrent sequences**: Deposit → partial slash → withdraw, testing share value integrity
2. **SweepPending + forceDeallocate interactions**: Pending state manipulation during concurrent operations
3. **VetoSlasher resolver timing edge cases**: Epoch boundaries, resolver changes during veto window
4. **Adapter limit enforcement**: Share vs absolute limit interactions with forceDeallocate
5. **Rewards distribution timing**: Snapshot vs allocation changes, Merkle claim ordering
