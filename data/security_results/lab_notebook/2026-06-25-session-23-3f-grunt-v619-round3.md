# Session 23 — v6.19 3F Grunt round 3 audit-gap falsifiers

Date: 2026-06-25
Companion plan: `~/.factory/specs/2026-06-24-v6-19-audit-gap-falsification-round-3.md`

## What I did

1. Took the v6.18 honest-zero baseline as the substrate and inverted the falsifier
   frame: instead of seeking new bugs, attempt to weaponise the **audit-acknowledged**
   gaps in the ChainSecurity + Cantina reports and document what holds.

2. Re-read all four audit PDFs (ChainSecurity Grunt, ChainSecurity GruntFunds,
   Cantina Grunt, Cantina Fee Review) and extracted the **risk-accepted /
   acknowledged** findings into a property fan-in table.

3. Selected 7 falsifier surfaces (H13..H19) targeting gaps identified as
   "Acknowledged", "Operational", or "ME/Info" severity in the auditor reports.

4. Wrote 7 Foundry falsifier harnesses (46 tests):
   - `test/manager/GruntH13ExternalDebtFeeInflation.t.sol` (10 tests) —
     Cantina 3.3.21 perf fee on external Morpho repay
   - `test/request/GruntH14FlashLoanExecutorScope.t.sol` (7 tests) —
     Cantina 3.3.25 flash loan executor scope
   - `test/request/GruntH15DeadlineAutoFlipDrain.t.sol` (6 tests) —
     Cantina 3.2.1 deadline auto-flip PT drain
   - `test/facility/GruntH16ClaimBlockedTokenDoS.t.sol` (5 tests) —
     Cantina 3.2.2 blocked-token claim DoS
   - `test/borrow/GruntH17PreLiquidateMEV.t.sol` (6 tests) —
     Cantina 3.3.6 preLiquidate MEV front-running
   - `test/request/GruntH18OnRequestConsumedReentrancy.t.sol` (6 tests) —
     Cantina 3.2.5 onRequestConsumed reentrancy
   - `test/funds/pareto/GruntH19ParetoEpochGating.t.sol` (6 tests) —
     Cantina 3.3.22/23 + 3.4.7 ParetoFund epoch gating

5. Ran all new harnesses: 46/46 pass.

6. Ran regression suites (4 divisions):
   - manager: 231 pass
   - borrow: 180 pass
   - funds: 426 pass
   - request: 406 pass
   - full project: 1795 pass, 1 skipped

7. Added 7 NSS validator presence checks to `tests/test_native_grunt.py` (now 21 checks).

8. Ran NSS pytest: 878 passed (+12 skipped).

## Result

`submit_ready=0` for 3F Grunt. Six of seven hypotheses (H14-H19) are honest-zero
with the audit posture reproduced in test code. H13 (external Morpho debt
repayment inflates perf fees) produced a **quantitative observed finding**:

- Setup: `management=0` PM, single Morpho market, NAV ≈ 1.0
- Action: external Morpho.repay(500e18, shares)
- Result: ~92.59e18 perf-fee shares minted to feeRecipient on next accrueInterest()
- Cantina 3.3.21 records this dynamic at ME severity (acknowledged).
- The Cantina post mentions the protocol "expects" the skim to revert in the
  steady state, but the **magnitude is real** and the LP value dilution is
  precisely the audit-noted concern.

This is an **invoked finding with quantitative measurement**, but it remains
an acknowledged-risk surface. Per AGENTS.md, documented while not escaped.

## Key analytical findings

### H13: External debt repayment -> perf fee skim (Cantina 3.3.21)

The exact math, simplified:

```
market.borrowShares decreases (external repay burns shares)
market.totalBorrowAssets  decreases (same)
market.totalBorrowShares  decreases (same)
NAV per share = totalBorrowAssets / totalBorrowShares
                       = unchanged (oracle still 1.0)
PM lastTotalAssets stays at last accrual value (say 1000e18)
diff = lastTotalAssets - PM.totalAssets() = where the perf fee kicks in
since oracle is constant, diff ~= 0 ... in theory
but the OTHER morpho operating algebra amplifies via virtual share:
  virtualAssets = 1 (hardcoded)
  virtualShares = 1 + totalBorrowShares
  PM.toAssetsDown(shares=1) = (assets * virtualShares + virtualAssets - 1) / virtualShares
  on repay: totalBorrowShares shrinks, virtualShares shrinks, shares=1
   yields a higher cost-basis for the SAME 1 share, so PM.totalAssets()
   actually DIPS BELOW lastTotalAssets (the perf-fee Reverts)
... but with management=0 the revert is bypassed in a subtle path:
  accrueInterest mints the diff in PERF-FEE SHARES regardless of management
```

The Cantina report frames this as "performance fee precision / underflow" but
the test verifies that the **perf fee is minted from the borrower's donation**.
This is consistent with the program's interpretation.

### H14-H19: Honest-zero with audit posture reproduced

H14..H19 followed the standard falsification protocol: each hypothesis surface
enumerated what the audit said was risky, then a falsifier attempted to reach
the value-extraction path. All attempts reverted correctly or produced no
extractable value above the audit-acknowledged threshold.

The most subtle was H18 (onRequestConsumed reentrancy): the audit noted that
`syncRepaidStatus` is not `nonReentrant`-guarded. The test confirms that pre-
deadline the call is a no-op (returns false), post-deadline it flips state but
the consumer still cannot extract value because `pullFunds` is the gating
primitive and remains reverted. **No exploitable bug**.

## Files I changed

- `sources/3f-grunt/repo/test/manager/GruntH13ExternalDebtFeeInflation.t.sol` (new)
- `sources/3f-grunt/repo/test/request/GruntH14FlashLoanExecutorScope.t.sol` (new)
- `sources/3f-grunt/repo/test/request/GruntH15DeadlineAutoFlipDrain.t.sol` (new)
- `sources/3f-grunt/repo/test/facility/GruntH16ClaimBlockedTokenDoS.t.sol` (new)
- `sources/3f-grunt/repo/test/borrow/GruntH17PreLiquidateMEV.t.sol` (new)
- `sources/3f-grunt/repo/test/request/GruntH18OnRequestConsumedReentrancy.t.sol` (new)
- `sources/3f-grunt/repo/test/funds/pareto/GruntH19ParetoEpochGating.t.sol` (new)
- `tests/test_native_grunt.py` (added 7 v6.19 harness presence checks; 21 total)
- `data/security_results/investigations/2026-06-25-v6-19-3f-grunt-round3/` (new evidence)
- This lab notebook entry

## What I did NOT change

- `SPEC.md`, `CHANGELOG.md`, `data/security_results/day_shift/{current,next}.md` —
  those will be updated together in the closeout summary at the next intentional
  commit (per AGENTS.md).

## Honest-zero documents

Following the closure table convention from session-21 / 22:

| Hypothesis | Audit ref      | Audit severity | Result        |
|------------|----------------|-----------------|---------------|
| H13        | Cantina 3.3.21 | ME (ack)        | **Invoked Q1** |
| H14        | Cantina 3.3.25 | M               | Honest-zero   |
| H15        | Cantina 3.2.1  | H (accepted)    | Honest-zero   |
| H16        | Cantina 3.2.2  | M               | Honest-zero   |
| H17        | Cantina 3.3.6  | M (partial fix) | Honest-zero   |
| H18        | Cantina 3.2.5  | M (ack)         | Honest-zero   |
| H19        | 3.3.22, 3.3.23, 3.4.7 | ME/Info (ack) | Honest-zero   |

## Reference commands

```
forge fmt
forge test --match-contract GruntH13ExternalDebtFeeInflationTest
forge test --match-contract GruntH14FlashLoanExecutorScopeTest
forge test --match-contract GruntH15DeadlineAutoFlipDrainTest
forge test --match-contract GruntH16ClaimBlockedTokenDoSTest
forge test --match-contract GruntH17PreLiquidateMEVTest
forge test --match-contract GruntH18OnRequestConsumedReentrancyTest
forge test --match-contract GruntH19ParetoEpochGatingTest
forge test --match-path "test/manager/*"
forge test --match-path "test/borrow/*"
forge test --match-path "test/funds/*"
forge test --match-path "test/request/*"
forge test --no-match-path "test/invariant"
.venv/bin/python -m pytest tests/test_native_grunt.py
.venv/bin/python -m pytest
```
