# Strategy: VetoSlasher Resolver Timing & State Edge Cases

**Priority**: HIGH
**Focus**: VetoSlasher resolver logic, veto window, epoch boundaries

## Attack Surface

VetoSlasher employs a complex state machine where:
1. Slash requests have a veto window (`vetoDuration`)
2. Resolver state is checkpointed with an epoch delay (`resolverSetEpochsDelay >= 3`)
3. `executeSlash` checks resolver at both `captureTimestamp` and `block.timestamp - 1`
4. `vetoSlash` checks resolver at `captureTimestamp` only
5. Multiple slash requests can be pending concurrently

## Hypothesis

The multi-timestamp resolver checks and delayed resolver activation create edge cases where:
- Slash requests can be executed despite valid veto (resolver timing confusion)
- Resolver changes during veto period allow unauthorized vetos
- Stale or conflicting resolver states lead to incorrect slash/veto outcomes

## Key Invariants to Test

### X-7 Check: Resolver set takes effect at delayed epoch
- `resolverAt(subnetwork, newTimestamp)` returns new resolver ONLY after `currentEpochStart + resolverSetEpochsDelay * epochDuration`
- Before that, old resolver is still effective

### X-8 Check: Veto requires resolver at captureTimestamp
- `vetoSlash`: msg.sender must be the resolver at `request.captureTimestamp`
- Resolver changes after captureTimestamp cannot veto

### ExecuteSlash resolver check
- `executeSlash`: checks resolver exists at both `captureTimestamp` AND `block.timestamp - 1`
- If resolver exists at both AND veto deadline hasn't passed → revert VetoPeriodNotEnded
- If resolver at `captureTimestamp` is zero (no resolver set) → slashing can proceed immediately

## Edge Cases

1. **Resolver set to address(0)**: `setResolver(subnetwork, 0)` should reset resolver. But the check at L162 `if (resolver_ == address(0)) { revert AlreadySet(); }` prevents setting zero when no prior resolver exists. But setting to zero when one exists... let me check: the code checks `if (resolver_ != address(uint160(_resolver[subnetwork].latest())))` — so setting to zero when a non-zero resolver exists creates a delayed-zero checkpoint.

2. **Multiple resolver changes**: If resolver changes multiple times, the checkpoint history grows. `resolverAt` uses `upperLookupRecent` which finds the most recent checkpoint ≤ timestamp.

3. **Resolved set during veto window**: A new resolver set during an active veto window cannot veto (not resolver at captureTimestamp), but the old resolver can still veto until the deadline.

4. **Epoch boundary captureTimestamps**: If `captureTimestamp` is near the epoch boundary, the resolver at that time may be different from current resolver.

## Sequence Templates

### Template: Resolver Change During Veto Window
```solidity
// 1. Set initial resolver
vetoSlasher.setResolver(subnetwork, resolverA, hints);

// 2. Request slash
uint256 index = vetoSlasher.requestSlash(subnetwork, operator, amount, captureTimestamp, hints);

// 3. Set new resolver (takes effect after delay)
vetoSlasher.setResolver(subnetwork, resolverB, hints);

// 4. Try veto from resolverB (should fail - not resolver at captureTimestamp)
vm.prank(resolverB);
vetoSlasher.vetoSlash(index, hints);
// Expected: revert NotResolver

// 5. Try veto from resolverA (should succeed if before deadline)
vm.prank(resolverA);
vetoSlasher.vetoSlash(index, hints);
// Expected: success
```

### Template: No Resolver → Instant Slash
```solidity
// 1. No resolver set for subnetwork
// 2. Request slash
uint256 index = vetoSlasher.requestSlash(subnetwork, operator, amount, captureTimestamp, hints);
// 3. Execute slash immediately (no resolver check, veto cannot happen)
vetoSlasher.executeSlash(index, hints);
// Expected: success (no resolver to veto)
```

### Template: Resolver Set + Veto After Deadline
```solidity
// 1. Set resolver
vetoSlasher.setResolver(subnetwork, resolver, hints);
// 2. Request slash
uint256 index = vetoSlasher.requestSlash(subnetwork, operator, amount, captureTimestamp, hints);
// 3. Warp past veto deadline
vm.warp(block.timestamp + vetoDuration + 1);
// 4. Try veto (should fail - past deadline)
vm.prank(resolver);
vetoSlasher.vetoSlash(index, hints);
// Expected: revert VetoPeriodEnded

// 5. Execute slash (should succeed)
vetoSlasher.executeSlash(index, hints);
// Expected: success
```

### Template: Multiple Pending Slash Requests
```solidity
// 1. Set resolver
// 2. Create multiple slash requests at different capture timestamps
// 3. Veto some, execute others
// 4. Verify cumulative slash tracking is correct
```
