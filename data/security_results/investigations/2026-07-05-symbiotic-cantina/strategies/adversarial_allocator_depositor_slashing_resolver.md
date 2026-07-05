# Strategy: Adversarial Allocator-Depositor-Slashing-Resolver

**Priority**: CRITICAL — Primary Target Subsystem core
**Focus**: VaultV2 + UniversalDelegator + VetoSlasher + Rewards V2 interplay

## Attack Surface

The core economic flow of Symbiotic involves:
1. Users deposit assets into VaultV2, receiving shares
2. Vault's UniversalDelegator allocates deposited assets to yield-bearing adapters
3. Operators are slashed by Networks via Slasher/VetoSlasher, reducing vault assets
4. Users withdraw or redeem shares (possibly via withdrawal queue)
5. Rewards are distributed via snapshot or Merkle mechanisms

## Hypothesis

Complex interactions between concurrent allocation, slashing, and withdrawal can create accounting desyncs, unfair asset distribution, or economic manipulation.

## Sequence Templates

### Template 1: Deposit → Allocate → Slash → Withdraw
```solidity
// 1. User deposits
vault.deposit(assets, user);

// 2. Delegator allocates to adapter (via auto-allocate or explicit allocate)
delegator.allocate(adapter, assets);

// 3. Network slashes operator (reducing vault assets)
slasher.slash(subnetwork, operator, slashAmount, captureTimestamp, hints);

// 4. User withdraws
vault.withdraw(assets, user, user);
// Expected: user gets fair share post-slash
// Attack: user may get pre-slash value if timing manipulation
```

### Template 2: Concurrent Depositors + Slash
```solidity
// User A deposits large amount
vault.deposit(largeAmount, userA);

// User B deposits small amount
vault.deposit(smallAmount, userB);

// Slash occurs, reducing totalAssets significantly
slasher.slash(subnetwork, operator, largeSlash, captureTimestamp, hints);

// Both users withdraw
vault.withdraw(userAExpected, userA, userA);
vault.withdraw(userBExpected, userB, userB);
// Attack: one user may get unfairly favorable share price
```

### Template 3: ForceDeallocate + SweepPending + Withdrawal
```solidity
// Deposit and allocate
vault.deposit(assets, user);
delegator.allocate(adapter, assets);

// Force deallocate with pending leftover
delegator.forceDeallocate(adapter, partialAmount);

// Sweep pending (triggered by deposit/withdraw)
vault.deposit(1, user);

// Withdraw
vault.withdraw(assets, user, user);
// Attack: pending state may block withdrawal or cause accounting error
```

### Template 4: VetoSlasher Timing Manipulation
```solidity
// Network requests slash
uint256 index = vetoSlasher.requestSlash(subnetwork, operator, amount, captureTimestamp, hints);

// Change resolver just before veto deadline
vaultConfigurator.setResolver(subnetwork, newResolver);

// New resolver tries to veto (should fail if not resolver at captureTimestamp)
vetoSlasher.vetoSlash(index, hints);
// Attack: resolver change during veto window confuses veto logic
```

### Template 5: Rewards Distribution + Allocation Change
```solidity
// Deposit before snapshot
vault.deposit(assets, user);

// Rewards distributed at timestamp T
rewards.distributeVaultSnapshotRewards(subnetwork, token, vault, amount, T, hints);

// User changes allocation or withdraws
vault.withdraw(assets, user, user);

// User claims rewards from timestamp T
rewards.claimVaultSnapshotRewards(recipient, network, token, vault, ...);
// Attack: user claims rewards on assets they no longer hold
```

## Fresh-Context Variants

For each template above, vary:
- Actor roles (depositor, curator, operator, network, resolver)
- Asset types (standard ERC20, tokens with decimals != 18)
- Fee configurations (management, performance, protocol)
- Adapter count (1 to MAX_ADAPTERS)
- Allocation order (auto-allocate vs explicit)
- Slash amounts (partial, full, zero)
- Capture timestamp (near epoch boundaries)
- Veto timing (before deadline, after deadline, at deadline)
- Concurrent operations (multiple deposits/withdrawals interleaved)

## Kill Criteria

Findings qualify for submission when:
- User can extract more value than entitled (accounting/economic violation)
- Withdrawal is permanently blocked (DoS/state desync)
- Slashing is unfairly distributed (one depositor bears all losses)
- Rewards manipulation (claiming more than entitled)
- Access control bypass (unauthorized allocation/slashing)

## Evidence Requirements

- Minimal PoC with exact call sequence on Anvil fork
- Balance diffs before/after (token and share)
- Event logs showing invariant violation
- Impact quantification (funds at risk)
- Affected contracts and versions
