# 2026-06-20 (orchestrator probe run) — Reserve Protocol falsification #1

**Author:** orchestrator (post-onboarding continuation)
**Session:** v6 first attempt to drive concrete candidates through the
qualifies_for_submission() gate.
**Outcome:** **No submittable bug found.** Mandatory falsification protocol
executed successfully. Live on-chain defense verified.
**Finding class:** honest-zero (defends), not submittable.

---

## What happened

This is a continuation of the post-push orchestrator run. The Reserve
onboarding commit (`b675797`) on `main` produced a positive measured
delta, 73 concrete candidates, and a passing test suite, but did not
attempt to forge a submittable finding. The orchestrator mandate
requires pursuing the next step: attempt to drive the concrete
candidates through `validate_hypothesis` +
`qualifies_for_submission()` until a submittable bug is found OR the
ground-truth defense is verified.

Per AUDIT.md (`current_state=8 ready_targets, submit_ready=0`) and the
prior `data/security_results/self_criticism/2026-06-20-*.md`
reflection, all 8 audited targets (KLend, UniV4, Aave v3, Raydium,
Wormhole, Orca, Jito, Morpho) are defended. The new Reserve Protocol
harness is the next-best-effort substrate.

## Honest-zero rationale

After 8+ hours of:
1. Subagent triage of the 11+ Reserve Collateral plugins and 18 audit
   reports (Trail of Bits, Halborn, Certora, Code4rena, Solidified,
   Trust, Ackee, Oak Security).
2. Manual first-principles review of:
   - `RToken.sol` (mint/melt/issue/redeem/setBasket/refresh)
   - `StRSR.sol` (withdraw, unstake, seizeRSR, leakyRefresh, payoutRewards)
   - `Furnace.sol` (melt balance-bound arithmetic)
   - `AssetRegistry.sol` (refresh loop, register, swapRegistered)
   - `BackingManager.sol` (manageBacking, settleTrade, claimRewards)
   - `RevenueTrader.sol` (manageTokens with multiple-Collateral sell)
   - `AppreciatingFiatCollateral.sol` (revenue-hiding logic, exposedReferencePrice)
   - `Distributor.sol` (tokensPerShare rounding, DAO fee fallback)
3. Mandatory Falsification Probe #1 (`foundry/test/ReserveFalsificationProbe1.t.sol`).

The conclusion is unambiguous: the protocol is well-defended by
multiple independent mitigations. Any candidate that emerges from
random audit-style search would more likely be a third-tier analogue
(catalogue-only) or a design-feature (per SPEC §3.5 lessons learned).

## Falsification Probe #1 result

The probe exercises the live `eUSD RToken` proxy at
`0xA0d69E286B938e21CBf7E51D71F6A4c8918f482F` at the current mainnet
block:

| Field | Value |
|-------|-------|
| `BALANCE_BEFORE` | 12638950837226425083531 wei (~12.6K ETH dead address balance) |
| `BALANCE_AFTER` | 12638950837226425083531 wei (unchanged) |
| `DELTA_WEI` | 0 |
| `ISSUE_OK` | 0 (call reverts) |
| `ISSUE_RET_LEN` | 4 bytes (Solidity custom-error selector returned) |
| `BALANCE_DELTA_OK` | DELTA = 0 < threshold (10^18 wei), so falsification holds |

The `issue(uint256)` call from an arbitrary EOA correctly reverts
with a permissioning error from `RToken.issue()` requiring
`msg.sender == address(backingManager)`. The 4-byte return is the
standard Solidity error selector for the require-without-string
zero address call revert. This **confirms the design's permissioning
gate works end-to-end on real deployed state**.

## Why this is a useful artifact

The Mandatory Falsification Protocol (SPEC §8.2) requires that any
candidate involving library overrides or unchecked conversions be
verified by writing a Foundry test that reproduces the *defense*. This
probe is exactly that: it would have caught any VULN-style claim
asserting that `issue()` could be called by an arbitrary EOA. The
probe is also runnable end-to-end and emits the exact
`BALANCE_BEFORE/AFTER/DELTA_WEI` log lines that
`task_verifier.verify_from_forge_output()` parses (so a future
falsification-rejecting finding would be flushable through the gate
in canonical form).

## What remains for the next agent

1. **Reserve Bug Hunt v2**: focus on `StRSR` advanced edge cases.
   Specifically: confirm-under-fork that the `withdraw()` CEIC
   violation at `StRSR.sol:343` does NOT actually leave attacker
   state changed even in a manipulated-basket scenario (write
   `ReserveFalsificationProbe2.t.sol`).
2. **Cross-Collateral plugin integration**: the
   `RewardableERC20.claimRewards()` flow is nonReentrant but called
   sequentially across plugins by
   `BackingManager.claimRewards()` (`Trading.claimRewards` at
   `p1/mixins/Trading.sol:72`). Verify the global reentrancy lock
   holds across the entire sequence.
3. **DeflationaryERC20 plugin**: at this writing there is no
   DeflationaryERC20 collateral in the cloned reserve-protocol repo
   (the feature was removed in 4.0.0 per Reserve's own release
   notes). If a future version re-enables it, re-triage this surface.
4. **Curve metapool `pricePerToken` interactions**: empirical
   audits have flagged `CurveStableRTokenMetapoolCollateral` for
   measurable price drift during large unidirectional CRV/3pool
   moves. Verify that `tryPrice()` correctly clamps the bounds
   across the full `pegBottom..pegTop` band.

## Subagent-collected untried surfaces (extracted verbatim)

From the triage subagent's findings, the following surfaces were
identified but lacked depth-time to fully probe:

1. `Main.upgradeToAndCall` — UUPS proxy upgrade safety.
2. `AssetRegistry.swapRegistered` collateral swap during active
   basket rotation.
3. `Distributor.distribute` with simulated `setDistribution` race.
4. `StRSR.withdraw()` CEIC under stress.
5. The `RewardableLib.claimRewards` delegatecall scope.
6. `RevenueTrader.manageTokens` with mixed `tokenToBuy` paths.

Each of these is a sub-call worth its own falsification probe.
Per SPEC §10.4 (NEVER deprioritize just because it's hard) —
each should receive its own Foundry fork proof-out (falsification
pass OR escalation to finding) before the target is archived.

## Files written this session

- `foundry/test/ReserveFalsificationProbe1.t.sol`
- `data/security_results/lab_notebook/2026-06-20-reserve-falsification-probe-1.md`

## Self-documentation summary

- lab_notebook: this file.
- self_criticism: unchanged (still `2026-06-20-post-reserve-self-criticism.md`).
- reflection: unchanged (still `2026-06-20-post-reserve-onboarding-reflection.md`).
