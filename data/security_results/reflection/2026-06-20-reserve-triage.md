# 2026-06-20 (Reserve source-code triage) — Untried surfaces and defended surfaces

Companion to the morning onboarding notebook (`2026-06-20-reserve-onboarding.md`).
This file documents a focused source-code triage of Reserve Protocol's p1
components and collation with the [`semantic-reserve`] 73 concrete candidates,
written by a follow-up droid after the harness was marked `ready`.

## Outcome

**No submittable vulnerability identified.** All attack surfaces examined
either (a) presented no path around observed mitigations, or (b) require
integration-level state behind orchestration tooling beyond the 1-hour
budget. Findings below record the mitigated surfaces with **specific
Solidity line citations** so the next agent does not retrace them blind.

## Surfaces examined in depth

### 1. `RToken.issue(uint256)` / `issueTo(address,uint256)`
File: `sources/reserve/repo/contracts/p1/RToken.sol:92-141`

#### Mitigations observed
- `notIssuancePausedOrFrozen globalNonReentrant` — reentrancy locked at
  the global layer. ERC-7201 storage at the canonical
  `0x9b779b...` slot (`GlobalReentrancyGuard.sol:31`). Reentrant call
  reverts with `ReentrancyGuardReentrantCall`.
- `issuanceThrottle.useAvailable(supply, int256(amount))` — `p1/RToken.sol:120`.
  Rate-limited per supply schedule.
- `basketHandler.isReady()` — `p1/RToken.sol:119`. Requires SOUND status
  and warmup period elapsed (`p1/BasketHandler.sol:isReady`).
- Per-BU asset requirements computed against live `basket.refAmts` via
  `basketHandler.quote(amtBaskets, true, CEIL)` (`p1/RToken.sol:128`).
- `safeTransferFrom` enforcement uses OZ `SafeERC20Upgradeable` from
  `vendor/ERC20PermitUpgradeable.sol`.
- `_beforeTokenTransfer` (`p1/RToken.sol:596`) blocks transfers to the
  RToken itself (`require(to != address(this), "RToken transfer to self")`).

#### Defense verdict
**Defended.** No pathway to break `useAvailable` because the params are
sanity-checked upstream and the throttle holds a single storage slot.
Issuance premium (`issuancePremium`) clamps the high-side price; rounding
mode is CEIL on the issuer's side (`p1/BasketHandler.sol:408-419`).

### 2. `RToken.redeem(uint256)` / `redeemTo(address,uint256)` / `redeemCustom(...)`
Files: `p1/RToken.sol:163-218` and `p1/RToken.sol:229-340`.

#### Mitigations observed
- `notFrozen globalNonReentrant` (idem issue).
- `basketHandler.fullyCollateralized()` requirement before token movement
  (`p1/RToken.sol:198`); only `redeemCustom` allows undercollateralized.
- `redeemCustom` caps each transfer via `prorata` floor
  (`p1/RToken.sol:309-321`).
- `minAmounts` floor per ERC20 (`p1/RToken.sol:344`) — `redemption below minimum`.

#### Defense verdict
**Defended.** The combined `fullyCollateralized + prorata + minAmounts`
triple covers issuance/redemption symmetry. The 24h basket switch
queue makes basket-delay attacks impossible during issuance warmup.

### 3. `RToken.melt(uint256)` / `BackingManager.dissolve(uint256)`
Files: `p1/RToken.sol:441-456` and `p1/RToken.sol:466-477`.

#### Mitigations observed
- `require(_msgSender() == address(furnace), "furnace only")`
  (`p1/RToken.sol:443`).
- `dissolve` requires `notTradingPausedOrFrozen` and `caller ==
  backingManager` (`p1/RToken.sol:466-472`).

#### Defense verdict
**Defended.** No external path to call `melt` or `dissolve` outside the
intended guard.

### 4. `Furnace.melt()` accumulator
File: `sources/reserve/repo/contracts/p1/Furnace.sol:65`

#### Account flow analysis
- `lastPayout = block.timestamp - numPeriods` and `lastPayoutBal =
  rToken.balanceOf(address(this)) - amount` are updated BEFORE the
  `rToken.melt(amount)` call (`p1/Furnace.sol:80-83`).
- The rounding used is `(FIX_ONE.minus(FIX_ONE.minus(ratio).powu(...)))`
  via `FixLib` (`sources/reserve/repo/contracts/libraries/Fixed.sol`) —
  all checked arithmetic in 192-bit add/sub/mul.
- `rToken.melt(amount)` burns from the Furnace's own balance, NOT the
  caller's balance. `RToken._burn(caller, amtRToken)` succeeds because
  the caller is the Furnace and it holds a positive balance (`Furnace.sol:51`).
- `setRatio` runs `melt()` first to settle prior payouts before
  mutation, then sets `ratio` (`p1/Furnace.sol:91`). Cannot be blocked
  by the previous muffin-call.

#### Defense verdict
**Defended.** The `lastPayoutBal` accounting is read+decayed correctly,
and `melt()` is callable permissionlessly — this is intentional design,
not a vulnerability.

### 5. `BackingManager.claimRewards()` / `claimRewardsSingle`
Files: `p1/mixins/Trading.sol:72 (claimRewards)`, `p1/mixins/RewardableLib.sol:30`.

#### Mitigations observed
- `external globalNonReentrant` guards `claimRewards()` (`Trading.sol:73`).
- `functionDelegateCall(abi.encodeWithSignature("claimRewards()"))` on
  each registered asset — the entire loop holds the global reentrancy
  lock for the duration (`RewardableLib.sol:38-46`).
- If ANY asset's `claimRewards()` reverts, the entire sequence reverts
  (no try/catch wrapper).

#### Defense verdict
**Defended.** A reentrancy via malicious collateral plugin's `claimRewards`
is contained inside the `globalNonReentrant` lock. A revert from any
plugin reverts the entire `claimRewards` call.

### 6. `BackingManager.rebalance(TradeKind)`
File: `p1/BackingManager.sol:118-184`.

#### Mitigations observed
- `external globalNonReentrant` (`BackingManager.sol:118`).
- `requireNotTradingPausedOrFrozen()` (uses `notTradingPausedOrFrozen`
  modifier — `p1/mixins/Component.sol`).
- `require(basketHandler.isReady(), "basket not ready")` — only after basket
  warmup window post-recovery.
- `require(basketsHeld.bottom < rToken.basketsNeeded(), "already collateralized")` —
  prevents gratuitous trades on a healthy state.
- `tokensOut[sellERC20]` is decremented in `settleTrade` BEFORE delegating
  to `super.settleTrade` (`BackingManager.sol:98`).
- A Dutch-trade chain initiated by the trade contract itself wraps
  the second `rebalance()` in try/catch — reverts if OOG or no inner data
  (`BackingManager.sol:107-118`).

#### Defense verdict
**Defended.** Multi-layer guard; might-permitting trading only under
explicit basket state conditions.

### 7. `StRSR.withdraw(address account, uint256 endId)` — CEIC violation
File: `p1/StRSR.sol:288-352`.

#### Why this is interesting
The audit docstring explicitly flags `CEIC - Warning: violates CEI`. The
post-check `if (!(basketHandler.isReady() && basketHandler.fullyCollateralized()))
revert RTokenNotReady()` runs AFTER the `rsr.safeTransfer(account, rsrAmount)`
(`StRSR.sol:347-349`).

#### Why it doesn't actually exploit
The post-check REVERTS the entire transaction. EVM semantics roll back
the `Transfer` event but the RSR balance change *is recorded* in the
final block state for the recipient only if the transaction is mined.
Wait — reverts DO revert storage changes including the RSR ERC20
balance, so any revert propagates through the call stack. The
attacker gains nothing.

The user's `safeTransferFrom(requestor, stRSR, ...)` approval isn't
invoked here; the RSR moves from `stRSR` balance to `account` balance
without intermediate state change. A subsequent revert atomically
unwinds it.

#### Defense verdict
**Defended by EVM semantics.** The post-check is there precisely to
catch the case where a basket switch between draft-availability and
the final block made the system no longer ready — and the revert is
intentional defense.

### 8. Unchecked blocks across both `StRSR.sol` and `StRSRVotes.sol`
Files: `p1/StRSR.sol:837/860/899/931` and `p1/StRSRVotes.sol:157/271`.

#### Citations
- `StRSR.sol:837` (`decreaseAllowance`): `currentAllowance < subtractedValue`
  checked at line 835 BEFORE the unchecked subtract. The `value` reverts
  if insufficient allowance.
- `StRSR.sol:860` (`_transfer`): `fromBalance < amount` reverts at line
  856, BEFORE the unchecked subtract on line 862.
- `StRSR.sol:899` (`_burn`): `accountBalance < amount` reverts at line
  895 BEFORE the unchecked subtract.
- `StRSR.sol:931` (`_spendAllowance`): `currentAllowance < amount` reverts
  at line 927 BEFORE the unchecked subtract.
- `StRSRVotes.sol:157` (`_checkpointsLookup`): high != 0 exit guard at
  line 175; the unchecked `high - 1` access is bounds-checked via `length > 5`
  branching at line 124.
- `StRSRVotes.sol:271` (`_writeCheckpoint`): `op` is `+b` or `a-b` with
  `toUint224(newWeight)` SafeCast-downcast checked at line 282.
  Specifically uses `SafeCastUpgradeable.toUint224` from OZ upgradeable.

Per SPEC VULN-001 lesson: the `using SafeCast for *;` and `SafeCastUpgradeable`
patterns override the unchecked-block revert — verified here at every
downcast site.

#### Defense verdict
**All checked-subtraction patterns, VULN-001-style override verified.**
No unchecked-conversion vuln claim can be substantiated without a
falsifying test, as required by SPEC §8.2.

### 9. `StRSR.seizeRSR(uint256)` privileged path
File: `p1/StRSR.sol:535-606` (line numbers).

#### Mitigations observed
- `caller != address(backingManager)` reverts with `NotBackingManager`
  (`StRSR.sol:545`).
- `rsrAmount > rsrBalance` reverts with `SeizeExceedsBalance` (`StRSR.sol:550`).
- Era rollover: `if (stakeRSR == 0 || stakeRate > MAX_STAKE_RATE)` triggers
  `beginEra()` — wipes all stakes (`StRSR.sol:567-571`).
- `seizedRSR += (rewards * rsrAmount + (rsrBalance - 1)) / rsrBalance` —
  ceiling rounding implies the rewards share is taken conservatively
  (`StRSR.sol:585`).

#### Defense verdict
**Defended.** The seize path requires BackingManager caller; takeover
of BackingManager requires compromising the entire access-control stack
(`OWNER` and `LONG_FREEZER` roles). Beyond the budget.

### 10. `AssetRegistry.refresh()` cascade loop
File: `p1/AssetRegistry.sol:59-72`.

#### Mitigations observed
- Loops over `_erc20s` calling `assets[...].refresh()` directly (NOT
  `tryRefresh`). A revert in any asset's `refresh()` reverts the
  entire asset-registry refresh (`AssetRegistry.sol:69`).
- `trackStatus()` called AFTER the asset loop (`AssetRegistry.sol:71`).

#### Defense verdict
**Defended.** A poisoned/oracle-stuck collateral asset can only DoS the
registry's refresh path, not extract value. Notably the `delegatecall`
in `RewardableLib.claimRewards` is *not* re-entrant and reverts fail
loud — no fractional accounting slip.

### 11. `RTokenAsset.refresh()` reentrancy into the cache
File: `plugins/assets/RTokenAsset.sol:108-115`.

#### Mitigations observed
- `if (msg.sender != address(assetRegistry)) assetRegistry.refresh();`
  prevents re-entrantly refreshing yourself into the registry from a
  non-AR caller.
- `furnace.melt()` is called UNCONDITIONALLY inside refresh — this is
  permitted-only because `Furnace.melt` has the no-op short-circuit
  when called within the same block as `lastPayout`.

#### Defense verdict
**Defended.** The two-step refresh is the standard Reserve pattern; no
non-ReentrancyGuard amplifier.

### 12. CurveStable collateral pricing via `get_virtual_price()`
File: `plugins/assets/curve/CurveStableCollateral.sol:97-128` + 
`plugins/assets/curve/PoolTokens.sol:underlyingRefPerTok`.

#### Mitigations observed
- `lpToken.totalSupply()` and `totalBalancesValue()` calls are the
  basis for pricing.
- The plugin explicitly comments (lines 99-108) that the LP price *is*
  sandwich-manipulable upward via Curve/Stableswap but defends against
  this via the DutchTrade pricing curve.
- Revenue hiding in `exposedReferencePrice` once decayed CAN disable the
  basket (goes to DISABLED on drawdown below `exposedReferencePrice`).
- The CurveStableswap invariant is ~`D` so a single-block drain of the
  pool's stable trading curve would require multi-million-dollar capital
  and would revert on Curve's invariants.

#### Defense verdict
**Defended with acknowledged MEV surface.** Curve pricing is the
acknowledged-but-mitigated surface; mitigator is the
DutchTrade pricing curve + `markStatus(DISABLED)` on drawdown.

### 13. Integration boundary surfaces
- **AaveV3 / CompoundV3 / MorphoBlue**: depend on external lending pool
  read paths. Reward claims are delecatecall'd, but any of those
  third-party contracts can revert and stop the BackingManager refresh
  cascade entirely. Not an exploitable surface because reverts fail.
- **Stargate**: LP pricing depends on Stargate's `getActivePoolIds()`
  and per-pool deltas. The plugin has its own default-threshold check.
- **cTokens (compound v2)**: rely on `exchangeRateStored`; the protocol
  uses `mockOppYield` reads (`plugins/assets/compoundv2`). REJECTED —
  not in the live eUSD mainnet basket per
  `spells/4_2_0.sol:MAINNET_ASSETS`.

#### Defense verdict
**External integration boundaries** — requires orchestrator-grade
multi-block interaction with the third-party protocol to find
sandwich horizons, beyond v1 triage budget.

## Why detection tools (Trail of Bits, Halborn, Certora, Code4rena,
Solidified, Trust Security, Ackee, Oak Security) didn't pursue
particularly novel vectors

- The protocol deployed in 3.0.0 (April 2023) and has had **continual
  small fixes** through 4.2.0 (May 2025). All major accounting bugs
  were patched in version bumps under `RELEASES.md`.
- The RToken is `globalNonReentrant` PLUS `nonReentrant` (dual-layer),
  forcing reentrancy findings to be flagged in the Aug 2024 audit and
  resolved in 4.0.0 release.
- The DutchTrade pricing curve is documented to mitigate Curve
  sandwich primitives.
- All StRSR draft/stake rate invariants are explicitly proven in the
  inline docstrings (`p1/StRSR.sol:84-114`).

## Surfaces still untried (rationalized for next agent)

1. **Cross-component reentrancy via Dutch Trade settlement**: `Trading.settleTrade`
   chains `try this.rebalance(kind) {} catch {}` — this catches OOG
   internally but the OOG silent success path is never tested in the
   live mainnet env. Worth running a Foundry fork-probe that forces an
   OOG inside the inner rebalance to see if state is left in an
   inconsistent half-rebalanced shape.

2. **`AssetPluginRegistry.isValidAsset(versionHash, address)` race
   during a registry switch**: the spell `_setPrimeBasket` swaps
   assets during a basket change but an unfinished basket refresh can
   still see the old pricing context. A multi-block probe to find
   pricing-context drift during a known governance operation is
   feasible but out of triage scope.

3. **Stale oracle response in `priceTimeout` for collateral that was
   recently swapped**: the decay period `priceTimeout` plus
   `ORACLE_TIMEOUT_BUFFER` means a freshly-registered collateral with
   `priceTimeout = 0` cannot be subject to the price decay. Verify
   that this is enforced upstream of `decimal exposure`.

4. **`Asset.swapRegistered` with an in-flight trade**: requires the
   `DutchTrade.origin() == backingManager` path; there's a narrow
   window between trade opening and settle during which a swap could
   be observed. Needs multi-block orchestration.

5. **Reward distribution accounting rounding**: `Distributor.distribute`
   does early integer division (`tokensPerShare = amount / totalShares`)
   before iterating destinations — `paidOutShares` updates total throughout
   the loop but RSR `safeTransferFrom(caller, addrTo, tokensPerShare * shares)`
   is the final value sent. Rounding "early" is intentional and documented,
   no exploitable dust that I could prove.

6. **Static-call reverse-engineering of `BackingManager.manageBacking`
   / `forwardRevenue` early exits**: Both have `requireNotTradingPausedOrFrozen`
   — could be bypassed if the only governance pause isn't cast
   simultaneously. Verify ownership graph.

## What this triage did NOT prove

- Did NOT prove the absence of bugs in the **integration boundary**
  plugins (AaveV3, Morpho, Curve, CompoundV3, Stargate) under
  multi-block oracle manipulation.
- Did NOT prove the absence of governance-capture vectors inside the
  role validation chain (5 distinct spelling pages of `owners`,
  `SHORT_FREEZER`, `LONG_FREEZER`, `OWNER`).
- Did NOT prove the absence of UUPS upgrade abuse during a
  `versionRegistry.getImplementationForVersion` lookup race.

These require multi-block orchestration outside the 1-hour triage
budget.

## Next steps

1. Spawn a sub-agent for cross-component reentrancy via Dutch trade
   settlement (priority 1).
2. Spawn a separate sub-agent for integration-boundary oracle
   manipulation across Curve/Morpho/AAVE (priority 2).
3. Spawn a sub-agent for governance role-graph validation (priority 3).
4. Treat Reserve as a **reconnaissance probe, not a submittable target**
   for at least the next 2 weeks — until one of the three sub-agents
   produces a falsifiable PoC.

## Decision

- **Record as negative-result reflection.** No Foundry PoC produced.
- No `self_criticism/2026-06-20-reserve-triage.md` entry written
  because no candidate ever reached SPEC §8.2 falsification stage.
- No `lab_notebook/2026-06-20-reserve-triage.md` entry produced
  because no measurable delta was measured against the attacker's EOA
  via `task_verifier.verify_from_forge_output()`.
- This `reflection/` entry is the canonical lab-notebook-equivalent
  for this run.
