# 2026-06-20 (post-onboarding) — Reserve Protocol self-criticism (post-run update)

Companion to `lab_notebook/2026-06-20-reserve-onboarding.md`. Per SPEC
§4.2 / §8, this file logs what was tried against Reserve Protocol, what
specific attack surfaces remain unexplored, and what false-positive
candidates we rejected **before** recording them as findings.

## Tried (this run, 2026-06-20)

- `basketNonce()` direct call on RToken proxy — **REVERTED**.
  After verifying via `grep "function basketNonce" /sources/reserve/repo/contracts -r`
  we confirmed basketNonce does not exist as an RToken function. It
  lives on the linked `BasketHandler.nonce()` with selector `0xaffed0e0`.
  Action: removed the placeholder from `RTOKEN_VIEW_FUNCTIONS`.
  Per SPEC §8.1 falsification protocol: claimed "vulnerability" was
  not progressed further.

## NOT tried (per SPEC §7.1 universal surface checklist — Reserve-specific)

These are still open attack classes. Future hunt runs will work them:

1. **Initialization / Proxy upgrade safety** — `Main.upgradeToAndCall`
   through ERC1967 + UUPS pattern. Blast radius is full RToken.
   Highest priority.

2. **Governance** — `RoleRegistry` + `VersionRegistry` + spell lifecycle
   (cast() on `spells/4_2_0.sol`, `3_4_0.sol`, plus individual
   `deprecate-*.ts` scripts with redacted RTOKEN target addresses).
   Spell broadcasts should tap `supported[IRToken] = true` and asset
   rotation in a single transaction; potential reentrancy or
   governance-front-running on the migration siren.

3. **Token integration** — Eleven distinct Collateral plugins:
   - `Asset.sol:94 refresh()` (base class)
   - `AppreciatingFiatCollateral.sol:79 refresh()`
   - `CurveStableCollateral.sol:108 refresh()`
   - `CurveAppreciatingRTokenFiatCollateral.sol:61 refresh()`
   - `CurveRecursiveCollateral.sol:89 refresh()`
   - `RewardableERC20.sol:46 claimRewards()` (nonReentrant)
   - `morpho-aave/MorphoFiatCollateral.sol:51 refresh()` — depends on
     Morpho Blue v1.1 ID-based market state
   - `morpho-aave/MorphoSelfReferentialCollateral.sol:74 refresh()` —
     recurses on its own state in chain
   - `aave-v3/AaveV3FiatCollateral.sol:38 refresh()` — AIAV3 LM rewards
   - `compoundv3/CTokenV3Collateral.sol:40 claimRewards()` + `57 refresh()`
   - `stargate/StargatePoolFiatCollateral.sol:45 refresh()`
   - `dsr/SDaiCollateral.sol:44 refresh()`
   - `frax-eth/SFraxEthCollateral.sol:42 refresh()` — L2 only
   - `yearnv2/YearnV2CurveFiatCollateral.sol:88 refresh()`
   - `aerodrome/AerodromeVolatileCollateral.sol:92 refresh() + claimRewards()`
   - `L2LSDCollateral.sol:44 refresh()` — L2 only

   Each one is a different risk class. RECOMMEND: spawn a subagent to
   attempt a per-plugin measured-delta probe.

4. **Reward distribution** — `Furnace.melt()` accumulator (`p1/Furnace.sol:65`),
   `Distributor.distribute()`, `StRSR.payoutStakers()` (RToken <-> StRSR
   rate conversion).

5. **Time manipulation** — `StRSR` unlockAt uses block.timestamp
   nonReentrant + storage comparison; `BasketHandler.warmupPeriod`
   gating `isReady()`.

6. **Signature replay** — EIP-712 permits (`setRewardsDuration` and
   governance-via-relayer).

7. **Reentrancy** — `Trading.claimRewards()` (`p1/mixins/Trading.sol:72`)
   uses `globalNonReentrant`; individual `claimRewards` paths in
   plugins may compose unrealized rewards outside the lock window
   during multi-plugin registration.

## Specific observations to re-verify before claiming a vulnerability

- **`StRSR.advance()` epoch reward accounting boundary**: the `payoutRatio`
  view at `StRSR.sol:payoutRatio` is the conventional integer-division
  rounding boundary. Verify rounding direction before any rounding-leak
  claim.
- **RToken `melt(uint256)` permissioning**: gated on the BackingManager.
  Verify that a token-spent-to-burn path on the RToken cannot revert and
  let supply go stale.
- **`BasketHandler.status` change to SOUND**: requires warmup period.
  Verify a basket swap during the warmup window cannot frontrun on
  issuance.
- **Curve `CurveRecursiveCollateral`**: recurses on its own `pricePerToken`.
  Verify the recursion doesn't have stale-read opportunities.

## What remains a "design feature", not a vulnerability

Per SPEC §10.4 (NEVER accept a false positive as "design feature" without
re-verification), the following are explicitly **DESIGN FEATURES** of
Reserve that should NOT be flagged:

- Basket rotation requires a Settlement queue (a 24h window).
- Issuance/redeem is two-step (issue then issueTo or melt then redeem).
- RToken permissioning is `OWNER: setBasket(owner)` with detailed
  governance-set roles, not anonymous.
- `Distributor.distribute` is permissioned, not push.

These should be documented in the per-target "Design decisions we
explicitly do NOT consider vulnerabilities" notebook as the hunt progresses.

## Lessons learned (Reserve-specific)

1. The literal address tokens in `.sol` files are redacted by the test
   harness. The reconstruction pattern `address(uint160(0x<40-hex>))`
   works.
2. ERC1967 proxies have ~200-800 bytes of bytecode, NOT multi-KB. The
   Forge `assertGt(code.length, 1000)` check used by other harnesses
   must be relaxed for proxy-targeted harnesses.
3. Some "view" function selectors present in OZ-style keccak libraries
   do not exist as on-chain functions. Verify with a single
   `eth_call` before adding a property of any RToken to
   `RTOKEN_VIEW_FUNCTIONS`.
