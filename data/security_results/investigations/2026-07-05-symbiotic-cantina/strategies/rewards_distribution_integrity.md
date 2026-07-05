# Strategy: Rewards V2 Distribution Integrity

**Priority**: HIGH
**Focus**: VaultSnapshotRewards, CumulativeMerkleRewards, curator/operator fees

## Attack Surface

Rewards V2 has two mechanisms:
1. **VaultSnapshotRewards**: Snapshot-based proportional distribution. Rewards are distributed proportional to `activeSharesOfAt(claimer, timestamp)`. Protocol fee is deducted from the total.
2. **CumulativeMerkleRewards**: Off-chain Merkle tree construction with dual signatures (protocol + rewarder). Claims use `msg.sender` embedded in leaf.

## Hypothesis

1. **VaultSnapshotRewards**: The gap between distribution timestamp and claim time allows allocation changes that affect share calculations. Fee calculation rounding may lead to value extraction.
2. **CumulativeMerkleRewards**: Dual signature model has trust assumptions. Merkle root reuse prevention and timestamp monotonicity may have edge cases.

## Key Invariants

### Snapshot Rewards
- Distribution uses `activeSharesOfAt(claimer, timestamp)` from vault checkpoints
- Protocol fee = `totalAmount * protocolFee / MAX_FEE`
- Curator fee + operator fee deducted from distribution before depositor share
- `reward.timestamp` must be < `block.timestamp`
- `activeSharesCache[vault][timestamp]` is cached after first lookup

### Cumulative Merkle Rewards
- `cumulativeDistribution.timestamp` must be > `lastCumulativeDistribution(network).timestamp`
- Merkle root must not be already set
- Dual signatures (protocol + rewarder) on EIP-712 typed data
- Claim verifies `MerkleProof.verifyCalldata(proof, root, keccak256(abi.encode(msg.sender, chainId, leaf)))`
- `claimableAmount = leaf.amount - claimed[network][token][msg.sender][rewardeeType]`

## Sequence Templates

### Template: Snapshot + Allocation Change
```solidity
// 1. User A deposits large amount
vault.deposit(largeAmount, userA);
// 2. User B deposits small amount
vault.deposit(smallAmount, userB);
// 3. Snapshot timestamp T recorded
// 4. Rewards distributed for timestamp T
rewards.distributeVaultSnapshotRewards(subnetwork, token, vault, amount, T, hints);
// 5. User A withdraws all (but still has shares at timestamp T)
vault.withdraw(userA)...
// 6. User A claims rewards for timestamp T (should get proportional share)
rewards.claimVaultSnapshotRewards(recipient, network, token, vault, ...);
// Attack: what if user manipulates allocation before claiming?
```

### Template: Cumulative Merkle Root Reuse
```solidity
// 1. First distribution
rewards.distributeCumulativeMerkleRewards(network, distribution, totalAmounts, sigs);
// 2. Try to use same root again
rewards.distributeCumulativeMerkleRewards(network, distribution, totalAmounts, sigs);
// Expected: revert RootAlreadySet
// Attack: what if timestamp is manipulated to pass monotonicity check?
```

### Template: Cumulative Merkle Claim Reorg
```solidity
// 1. Deposit and set up distribution
// 2. Claim rewards
// 3. Attempt to claim same leaf again
// Expected: claimableAmount = 0 → revert NoCumulativeRewardsToClaim
```

### Template: Protocol Fee Rounding
```solidity
// 1. Distribute specific amounts with protocol fee enabled
// 2. Verify distributionToTotalAmount vs totalToDistributionAmount are inverse
// 3. Check rounding doesn't favor protocol over depositors or vice versa
```
