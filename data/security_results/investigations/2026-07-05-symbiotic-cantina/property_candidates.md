# Symbiotic Property Candidates for ultrafuzz-discovery

**Target**: Primary Target Subsystem
**Source**: Derived from codegraph-x-ray invariant analysis and manual contract review
**Usage**: Import into ultrafuzz-discovery canonical property fan-in table

---

## Property Table

| ID | Bug Class | Property Description | Kill Criteria | Source Refs | Priority |
|----|-----------|---------------------|---------------|-------------|----------|
| P-001 | Accounting | After any sequence of deposits and withdrawals, vault share price (totalAssets / totalSupply) does not decrease below initial value | totalAssets * 1e18 < totalSupply * initialSharePrice after operations | VaultV2: totalAssets(), _deposit(), _withdraw() | CRITICAL |
| P-002 | Accounting | totalAssets = freeAssets + sum(adapter.totalAssets()) at all times, including after slashing events | abs(freeAssets + delegatorTotalAssets - _totalAssets) > 0 | VaultV2: totalAssets(), getAccrueInterest(); UniversalDelegator: totalAssets() | CRITICAL |
| P-003 | Accounting | User cannot withdraw more assets than they deposited + accrued interest, net of fees | withdrawable balance after user ops > expected maximum | VaultV2: _withdraw(), convertToAssets(), maxWithdraw() | CRITICAL |
| P-004 | State Desync | After forceDeallocate + sweepPending, adapter absolute limit is not below current adapter totalAssets | absoluteLimitOf[adapter] < IAdapter(adapter).totalAssets() | UniversalDelegator: forceDeallocate() L183-186, _sweepPending() | HIGH |
| P-005 | State Desync | When sweepPending > 0, no new allocations can occur | Any allocate() call succeeds while WithdrawalQueue has pending assets | UniversalDelegator: allocate() G-5, VaultV2: G-3 | HIGH |
| P-006 | Access Control | An adapter without ALLOCATE_ROLE cannot call allocate() successfully | Non-ALLOCATE_ROLE caller gets allocated > 0 | UniversalDelegator: onlyRole(ALLOCATE_ROLE) modifiers | HIGH |
| P-007 | Economic | Management fee cannot exceed MAX_MANAGEMENT_FEE per second | managementFee > MAX_MANAGEMENT_FEE after setManagementFee call | VaultV2: setManagementFee() L253-254 | MEDIUM |
| P-008 | Slashing | Slash amount never exceeds operator's slashable stake at capture time | slashedAmount > slashableStake after any slash call | BaseSlasher: _slashableStake(); Slasher: slash() L33-34 | CRITICAL |
| P-009 | Slashing | VetoSlasher veto can only succeed before vetoDeadline | vetoSlash() succeeds when block.timestamp >= vetoDeadline | VetoSlasher: vetoSlash() L144-145 | CRITICAL |
| P-010 | Slashing | Same slash cannot be executed twice (completed flag) | executeSlash() succeeds on already-completed request | VetoSlasher: executeSlash() L121-122 | CRITICAL |
| P-011 | State Desync | After deallocate, vault freeAssets increases by the deallocated amount | vault balance change != deallocated amount after deallocate()->push() | UniversalDelegator: _deallocate() L272-273; VaultV2: push() | HIGH |
| P-012 | Accounting | Fee shares minted on accrual never exceed the economic upper bound | managementFeeShares + performanceFeeShares + protocolFeeShares > max theoretical | VaultV2: getAccrueInterest() L72-94 | MEDIUM |
| P-013 | Reentrancy | No reentrant call path exists from adapter.deallocate() back into vault state | Adapter.deallocate() callback allows vault state manipulation | UniversalDelegator: _deallocate() calls IAdapter(adapter).deallocate() | HIGH |
| P-014 | State Desync | After swapAdapters, ordered adapter route is consistent (no duplicates, all present) | Swap introduces duplicate or loses an adapter | UniversalDelegator: swapAdapters() L114-128 | MEDIUM |
| P-015 | Rewards | Rewards claimer cannot claim more than their proportional share | Claimed amount > activeSharesOfAt * amount / totalActiveShares | VaultSnapshotRewards: claimVaultSnapshotRewards() L212-218 | CRITICAL |
| P-016 | Rewards | Cumulative Merkle rewards cannot be claimed twice for the same leaf | Second claim on same leaf succeeds with non-zero claimableAmount | CumulativeMerkleRewards: claimCumulativeMerkleRewards() L191-194 | CRITICAL |
| P-017 | State Desync | Auto-allocate adapter set has no duplicates and all are added adapters | Duplicate or non-added adapter in autoAllocateAdapters | UniversalDelegator: setAutoAllocateAdapters() L131-146 | MEDIUM |
| P-018 | Economic | Protocol fee taken on rewards distribution does not exceed configured rate | Protocol fee rate > configured protocolFee for given reward type | VaultSnapshotRewards: distributionToTotalAmount(); CumulativeMerkleRewards: distributionToTotalAmount() | MEDIUM |
| P-019 | State Desync | Withdrawal queue + sweep: after fill, pendingAssets decreases or stays same | pendingAssets increases after WithdrawalQueue.fill() | UniversalDelegator: _sweepPending() → WithdrawalQueue.fill() | HIGH |
| P-020 | Slashing | Cumulative slash only increases over time for a given operator+subnetwork | cumulativeSlash(subnetwork, operator) decreases | BaseSlasher: _updateCumulativeSlash() L111; only pushes increasing values | HIGH |
| P-021 | Accounting | transfer/transferFrom cannot create shares out of thin air | balanceOf sum across all accounts != totalSupply after any transfer | VaultV2: _update() L197-220 uses checkpoints for both | CRITICAL |
| P-022 | State Desync | Adapter limitOf returns consistent value between share and absolute limits | limitOf(adapter) != min(absolute, share-based) for any vault state | UniversalDelegator: limitOf() L63-64; depends on VaultV2.totalAssets() | MEDIUM |
| P-023 | Economic | VetoSlasher resolver set with delay ≥ 3 epochs allows timely veto | Resolver changes take effect before veto can execute | VetoSlasher: setResolver() L155-166; resolverSetEpochsDelay >= 3 | MEDIUM |
| P-024 | Slashing | Slash request with expired captureTimestamp (outside epochDuration) cannot be executed | executeSlash() succeeds when now - captureTimestamp > epochDuration | VetoSlasher: executeSlash() L116-117 | CRITICAL |
| P-025 | Economic | NetworkRestakeDelegator: operator stake cannot exceed vault active stake or network limit | operator stake > min(activeStake, networkLimit) | NetworkRestakeDelegator: _stakeAt() uses mulDiv with min | HIGH |

## Sequence-Level Properties (Multi-step)

| ID | Scenario | Steps | Expected Invariant | Priority |
|----|----------|-------|-------------------|----------|
| SQ-001 | Deposit → Partial Slash → Withdraw | 1. User deposits assets 2. Network slashes operator 3. User withdraws | User receives >= entitled amount post-slash (no unfair slashing) | CRITICAL |
| SQ-002 | Deposit → Allocate → ForceDeallocate → SweepPending → Withdraw | 1. Deposit 2. Allocate to adapter 3. ForceDeallocate (partial) 4. SweepPending 5. Withdraw | Full withdrawal possible eventually; no stuck funds | HIGH |
| SQ-003 | Concurrent Deposit + Slash + Redeem | Multiple users: User A deposits, User B deposits, slash occurs, both try to redeem | Both users get fair share of remaining assets | CRITICAL |
| SQ-004 | VetoSlasher: RequestSlash → Resolver Set → ExecuteSlash | 1. Request slash 2. Set resolver with delay 3. Try executeSlash during veto period | Correct veto/execute decision based on resolver at capture time vs now | HIGH |
| SQ-005 | Multi-adapter allocate with limits | 1. Set adapters with limits 2. Allocate to fill some 3. Reduce limits 4. DeallocateAll | No adapter exceeds its limit after limit reduction | HIGH |
| SQ-006 | Rewards distribution after slashing | 1. Deposit 2. Slash occurs 3. Snapshot rewards distributed | Rewards use correct post-slash share count | MEDIUM |
| SQ-007 | Deposit with whitelist bypass | Non-whitelisted user tries to deposit via various paths (direct, permit, multicall) | Only whitelisted users can deposit when whitelist enabled | MEDIUM |
| SQ-008 | Fee accrual race | Rapid successive deposits/withdrawals at epoch boundaries | Fee accrual is accurate and totalSupply monotonic | MEDIUM |
| SQ-009 | CumulativeMerkleRewards: reorged claim | Claim after distribution with old lastCumulativeDistribution timestamp | Old root cannot be reused; timestamp monotonicity enforced | HIGH |
| SQ-010 | Adapter decreaseLimits below current allocation | Adapter reduces its own limits below current totalAssets | Limits cannot cause accounting mismatch (assets still recoverable) | HIGH |
