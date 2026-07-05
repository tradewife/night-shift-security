# Symbiotic Invariant Catalog

**Target**: Primary Target Subsystem (VaultV2 + UniversalDelegator + Slasher/Resolver + Rewards V2)
**Evidence Requirement**: Every invariant backed by concrete source code reference.

---

## G-N: Enforced Guards

### G-1: Vault deposit limit check
- **Invariant**: `maxDeposit()` returns 0 when whitelist enabled and caller not whitelisted, or deposit limit enforced and totalAssets >= limit.
- **Evidence**: VaultV2.sol L108-111
- **Enforcement**: Runtime check in `maxDeposit()` via ERC4626 `deposit()` flow.

### G-2: Only delegator can pull/push vault assets
- **Invariant**: `pull()` and `push()` revert when `msg.sender != delegator`.
- **Evidence**: VaultV2.sol L140-141, L151-152

### G-3: Withdrawal queue sweep gate
- **Invariant**: `withdraw()` and `redeem()` revert when `sweepPending() > 0` unless called by withdrawal queue.
- **Evidence**: VaultV2.sol L173-178

### G-4: Allocate/deallocate role gating
- **Invariant**: `allocate()`, `deallocate()`, `allocateAll()`, `deallocateAll()` require respective ALLOCATE_ROLE/DEALLOCATE_ROLE.
- **Evidence**: UniversalDelegator.sol function definitions with `onlyRole(ALLOCATE_ROLE)` / `onlyRole(DEALLOCATE_ROLE)`

### G-5: Sweep pending blocks allocation
- **Invariant**: `allocate()`, `allocateAll()`, `allocateExact()` return 0 when `_sweepPending() > 0`.
- **Evidence**: UniversalDelegator.sol L114-116, L119-120, L125-126

### G-6: Adapter must be whitelisted and not already added
- **Invariant**: `addAdapter()` reverts if adapter not in AdapterRegistry whitelist or already added.
- **Evidence**: UniversalDelegator.sol L76-79

### G-7: Adapter removal requires zero totalAssets
- **Invariant**: `removeAdapter()` reverts if adapter has non-zero totalAssets.
- **Evidence**: UniversalDelegator.sol L96-97

### G-8: Slasher capture timestamp bounds
- **Invariant**: Slasher `slash()` reverts if captureTimestamp is outside [now - epochDuration, now).
- **Evidence**: Slasher.sol L30-32; BaseSlasher.sol L83-86

---

## I-N: Single-Component Invariants

### I-1: Vault totalAssets = freeAssets + delegator.totalAssets()
- **Invariant**: Total assets is the sum of vault's own asset balance and all managed adapter assets
- **Evidence**: VaultV2.sol `totalAssets()` → `getAccrueInterest()` → `freeAssets() + UniversalDelegator(delegator).totalAssets()`
- **Flux**: This is the base for all fee calculations and share pricing

### I-2: Fee shares are minted on accrual before totalSupply checkpoint
- **Invariant**: `accrueInterest()` mints management, performance, and protocol fee shares before updating `lastUpdate`.
- **Evidence**: VaultV2.sol `accrueInterest()` L129-139

### I-3: Share price increases monotonically with interest (excluding slashing)
- **Invariant**: `convertToAssets(shares)` increases over time as interest accrues, absent slashing events.
- **Evidence**: VaultV2.sol `getAccrueInterest()` adds interest to `_totalAssets` before fee computation

### I-4: totalSupply checkpoint includes fee shares
- **Invariant**: `totalSupply()` returns `_totalSupply.latest() + managementFeeShares + performanceFeeShares + protocolFeeShares` from the last accrual.
- **Evidence**: VaultV2.sol L57-59

### I-5: Balance checkpoints track transfers via _update
- **Invariant**: `_update()` pushes sender/receiver balance checkpoints and adjusts totalSupply checkpoint.
- **Evidence**: VaultV2.sol `_update()` L197-220

### I-6: Adapter limit calculation uses min of absolute and share-based limits
- **Invariant**: `limitOf(adapter)` = `min(absoluteLimitOf[adapter], totalVaultAssets * shareLimitOf[adapter] / MAX_SHARE)`
- **Evidence**: UniversalDelegator.sol L63-64

### I-7: MAX_SHARE = 1e18 implies 100% share cap
- **Invariant**: Share limit can never exceed 100% of vault assets. `MAX_SHARE = 1e18`.
- **Evidence**: IUniversalDelegator.sol constant MAX_SHARE

### I-8: ForceDeallocate reduces adapter absolute limit
- **Invariant**: After `forceDeallocate()`, adapter's absolute limit ≤ previous limit minus deallocated/pending assets.
- **Evidence**: UniversalDelegator.sol L183-186

### I-9: Adaptable uses adapter type delegator explicitly
- **Invariant**: `decreaseLimits()` is `nonReentrant` and called by the adapter via msg.sender.
- **Evidence**: UniversalDelegator.sol L189 (nonReentrant modifier, msg.sender usage)

### I-10: VetoSlasher vetoDuration < epochDuration
- **Invariant**: On initialization, `vetoDuration` must be < `epochDuration`.
- **Evidence**: VetoSlasher.sol L187 (`if (params.vetoDuration >= epochDuration) revert InvalidVetoDuration()`)

### I-11: VetoSlasher resolverSetEpochsDelay >= 3
- **Invariant**: On initialization, `resolverSetEpochsDelay` must be >= 3.
- **Evidence**: VetoSlasher.sol L190 (`if (params.resolverSetEpochsDelay < 3) revert InvalidResolverSetEpochsDelay()`)

### I-12: Slash request veto deadline = now + vetoDuration
- **Invariant**: `requestSlash()` sets `vetoDeadline = block.timestamp + vetoDuration`.
- **Evidence**: VetoSlasher.sol L84

### I-13: executeSlash checks resolver at two timestamps
- **Invariant**: `executeSlash()` checks resolver at both request.captureTimestamp and block.timestamp-1. If resolver exists at both and veto deadline hasn't passed, revert VetoPeriodNotEnded.
- **Evidence**: VetoSlasher.sol L108-114

### I-14: Slashable stake decreases with cumulative slashes
- **Invariant**: `slashableStake = stakeAmount - min(cumulativeSlashTotal - cumulativeSlashAt(captureTimestamp), stakeAmount)`. Slashable amount decreases as cumulative slash increases.
- **Evidence**: BaseSlasher.sol L87-92

---

## X-N: Cross-Component Invariants

### X-1: Vault → Delegator → Adapter asset flow consistency
- **Invariant**: Total assets allocated to adapters = sum of `IAdapter(adapter).totalAssets()` for all configured adapters. Vault's `freeAssets` + this sum = total vault assets.
- **Evidence**: VaultV2 `_totalAssets` tracks asset movement; UniversalDelegator `totalAssets()` iterates adapters

### X-2: Withdrawal queue pending + vault free assets ≥ withdrawal requests
- **Invariant**: After `sweepPending()`, any remaining pending assets in WithdrawalQueue must have corresponding requestDeallocate on adapters tracked in `adaptersWithPending[]`.
- **Evidence**: UniversalDelegator `_sweepPending()` L222-257

### X-3: Slashing reduces vault share value proportionally
- **Invariant**: `Vault.onSlash()` reduces `_totalAssets` by slashed amount, reducing share value for all depositors proportionally.
- **Evidence**: BaseSlasher `_vaultOnSlash()` calls `IVault(vault).onSlash(amount, captureTimestamp)`; Vault decreases totalAssets by slashed amount

### X-4: Delegator onSlash hook must not exceed gas limit
- **Invariant**: Hook execution is bounded by `HOOK_GAS_LIMIT = 250_000` with `HOOK_RESERVE = 20_000`.
- **Evidence**: BaseDelegator.sol `onSlash()` L108-115

### X-5: Burner hook gated by isBurnerHook flag
- **Invariant**: `_burnerOnSlash()` only executes when `isBurnerHook` is true and burner address is non-zero.
- **Evidence**: BaseSlasher.sol L121-132

### X-6: Sweep-pending blocks both allocation and instant withdrawal
- **Invariant**: When `sweepPending() > 0`, both allocate paths (return 0) and instant withdraw/redeem (revert) are blocked, forcing queue-based withdrawal.
- **Evidence**: UniversalDelegator allocate functions (G-5) + VaultV2 G-3

### X-7: Resolver set at delayed epoch
- **Invariant**: Resolver changes take effect at `currentEpochStart + resolverSetEpochsDelay * epochDuration`.
- **Evidence**: VetoSlasher.sol `setResolver()` L155-166

### X-8: Slash request veto by same resolver at capture timestamp
- **Invariant**: Only the resolver active at the `captureTimestamp` can veto the slash request, and only before `vetoDeadline`.
- **Evidence**: VetoSlasher.sol `vetoSlash()` L134-150

### X-9: Rewards V2 snapshot distribution based on active shares at timestamp
- **Invariant**: Distribution amount per claimer = `activeSharesOfAt(claimer, timestamp) * distributionAmount / activeSharesCache[vault][timestamp]`. Shares snapshot is immutable for that timestamp.
- **Evidence**: VaultSnapshotRewards.sol `claimVaultSnapshotRewards()` L212-218

---

## E-N: Economic Invariants

### E-1: Max management fee ≤ 5%/year
- **Invariant**: `MAX_MANAGEMENT_FEE = 5e16 / 365 days` ≈ 5% annualized. `setManagementFee()` reverts if fee exceeds this.
- **Evidence**: IVaultV2.sol constant; VaultV2.sol `setManagementFee()` L253-254

### E-2: Max performance fee ≤ 20%
- **Invariant**: `MAX_PERFORMANCE_FEE = 2e17` (20%). `setPerformanceFee()` reverts if fee exceeds this.
- **Evidence**: IVaultV2.sol constant; VaultV2.sol `setPerformanceFee()` L264

### E-3: Protocol fees cached at each accrual window
- **Invariant**: Protocol fee config is fetched from `PROTOCOL_FEE_REGISTRY` on each `accrueInterest()` call and cached for the next window.
- **Evidence**: VaultV2.sol `_updateProtocolFee()` L296-302; called at end of `accrueInterest()` L137

### E-4: Adapter share allocation max 100% of vault
- **Invariant**: Each adapter's share limit ≤ MAX_SHARE (100%), enforced in `setLimits()`.
- **Evidence**: UniversalDelegator.sol `_setLimits()` L103-104

### E-5: Slash amounts capped by slashable stake
- **Invariant**: Slash amount is `min(requestedAmount, slashableStake)`. Slashable stake accounts for prior cumulative slashes.
- **Evidence**: Slasher.sol L33-34; BaseSlasher.sol `_slashableStake()`

### E-6: Operator stake delegation proportional to network shares
- **Invariant**: In NetworkRestakeDelegator, operator's stake = `operatorShares / totalShares * min(activeStake, networkLimit)`. Stake at a past timestamp uses checkpointed values.
- **Evidence**: NetworkRestakeDelegator.sol `_stakeAt()` L102-113
