# 2026-06-20 — Reserve Protocol p1 source-code triage (round 2)

**Author:** triage droid (post-onboarding handoff)
**Session:** focused source-code analysis of all reachable Reserve
components reachable via eUSD Main, attempting to identify
sub-bounty-budget submittable vulnerabilities per SPEC §10.4.
**Outcome:** **No submittable vulnerability identified** within the
1-hour analysis budget. All examined surfaces are defended with
proper reentrancy locks, access control, or EVM-semantics rollback
on post-checks.

---

## Surfaces examined (in priority order)

| # | Surface | File:Line | Mitigation | Verdict |
|---|---------|-----------|------------|---------|
| 1 | `RToken.issue` | `p1/RToken.sol:92-141` | `globalNonReentrant + useAvailable + isReady + warmup + quote()` | defended |
| 2 | `RToken.redeem/redeemTo/redeemCustom` | `p1/RToken.sol:163-340` | `globalNonReentrant + fullyCollateralized + prorata + minAmounts` | defended |
| 3 | `RToken.melt/dissolve` | `p1/RToken.sol:441-477` | `furnace only` + `notTradingPausedOrFrozen` | defended |
| 4 | `Furnace.melt` accumulator | `p1/Furnace.sol:65` | arithmetic checked + `setRatio` settles prior math first | defended |
| 5 | `BackingManager.claimRewards[Single]` | `p1/mixins/Trading.sol:72-86` | `globalNonReentrant` held over full asset iteration | defended |
| 6 | `BackingManager.rebalance(TradeKind)` | `p1/BackingManager.sol:118-184` | `globalNonReentrant + requireNotTradingPausedOrFrozen + isReady + basketsHeld check` | defended |
| 7 | `StRSR.withdraw` CEIC | `p1/StRSR.sol:288-352` | EVM revert semantics roll back the pre-check RSR transfer | defended |
| 8 | `unchecked` blocks in StRSR | `p1/StRSR.sol:837/860/899/931`, `p1/StRSRVotes.sol:157/271` | all are checked-subtraction patterns + SafeCast override | defended |
| 9 | `StRSR.seizeRSR` | `p1/StRSR.sol:535-606` | `caller == backingManager` + `rsrAmount <= rsrBalance` + era rollover | defended |
| 10 | `AssetRegistry.refresh` cascade | `p1/AssetRegistry.sol:59-72` | raw refresh (NOT tryRefresh) — Doable DoS, no exploit | defended |
| 11 | `RTokenAsset.refresh` | `plugins/assets/RTokenAsset.sol:108-115` | `furnace.melt()` step + cross-call refresh guarded | defended |
| 12 | Curve collateral pricing | `plugins/assets/curve/CurveStableCollateral.sol:97-128` | DutchTrade pricing curve + DISABLE on drawdown | defended (acknowledged MEV) |
| 13 | External integration plugins | AaveV3 / MorphoAave / Stargate | revert fail-loud via `nonReentrant` parent | defended |

## Why none of these qualify

Per SPEC §10.4 hard rules:
- Every checked surface has a documented mitigation at line citation.
- No `unchecked` block is reachable from a non-checked subtraction.
- The DutchTrade inner-rebalance OOG catch (`BackingManager.sol:107-118`)
  is `try/catch {}` which silences `errData.length == 0` (reverts
  OOG), so OOG actually does revert (good).
- The `CEIC` warning on `StRSR.withdraw` is comment-flagged by the
  audit team because the post-check would only REVERT (no
  reentrancy amplifier via token transfer).

## What was NOT tried (out of budget / requires multi-block oracle)

1. Cross-component reentrancy via Dutch-trade inner-rebalance.
2. Curve / Morpho / AAVE oracle-manipulation under multi-block coordination.
3. Asset swapping race during in-flight trades.
4. Governance role-graph bypass: 5 distinct role names (`OWNER`,
   `SHORT_FREEZER`, `LONG_FREEZER`, `PAUSER`, plus
   `TIMELOCK_ADMIN_ROLE / PROPOSER_ROLE / EXECUTOR_ROLE / CANCELLER_ROLE`).
5. UUPS upgrade race during `versionRegistry.getImplementationForVersion`.

These require Foundry-fork tests with multi-block orchestration,
beyond the 1-hour triage budget. Sub-agents should be spawned for
each before another droid re-explores the same surfaces.

## Surfaces still untried (rationalized for next agent)

1. **Cross-component reentrancy via Dutch trade settlement** — high priority.
   `BackingManager.settleTrade` chains a try/catch `rebalance` (→
   `Trading.sol:107-118`). The try/catch has an explicit
   `if (errData.length == 0) revert();` that reverts on OOG. Confirmed
   not silent-success, but the *transaction-level* OOG pattern is
   fragile — a multi-block probe that forces OOG between two settles
   could leave `tokensOut[sell]` in stale state. Verifies with a
   `gas-stipend` test.

2. **AssetPluginRegistry.isValidAsset(versionHash, address) race during a
   registry switch** — medium priority. Requires orchestrating a
   registry switch + a basket refresh in the same block window.

3. **Stale oracle response in `priceTimeout`** — low priority. The
   decay envelope has a `maxOracleTimeout + ORACLE_TIMEOUT_BUFFER`
   dual buffer; verify the dual-buffer is non-zero for ALL registered
   collateral on eUSD mainnet.

4. **reward distribution early-rounding dust** — `Distributor.distribute`
   deliberately uses early division. The `paidOutShares != totalShares`
   dust goes to DAO fee recipient if configured, otherwise stays in
   the RevenueTrader. Does NOT inflate the user-side accounting.

## Self-documentation

- This `lab_notebook/2026-06-20-reserve-triage.md`
- Companion `reflection/2026-06-20-reserve-triage.md`
- No `self_criticism` entry produced because no candidate ever
  reached SPEC §8.2 falsification stage.

## NEXT STEPS

1. Spawn sub-agent for Dutch-trade OOG-reentrancy probe (priority 1).
2. Spawn sub-agent for integration-boundary oracle manipulation
   across Curve/Morpho/AAVE (priority 2).
3. Spawn sub-agent for governance role-graph validation (priority 3).
4. **Until then**: treat Reserve as a reconnaissance probe,
   NOT a submittable target.
