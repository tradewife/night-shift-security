# v6.19 — 3F Grunt Cantina deep-dive round 3 evidence

Date: 2026-06-25

## Goal

Per the approved spec `~/.factory/specs/2026-06-24-v6-19-audit-gap-falsification-round-3.md`,
advance 3F Grunt from v6.18's H9-H12 honest-zero baseline to 7 new hypothesis surfaces
deliberately targeting the **audit-acknowledged / risk-accepted** findings in the
ChainSecurity and Cantina reports. The falsifier frame inverts prior rounds: instead of
seeking new bugs, we attempt to weaponise what the auditors already admitted was risky,
then document what holds and what doesn't.

| New hypothesis | Cantina ref | Audit posture                       | Outcome             |
|----------------|-------------|-------------------------------------|---------------------|
| H13            | 3.3.21      | Performance fee on external Morpho repay (Cantina: ME info) | **Invoked finding**  |
| H14            | 3.3.25      | FlashLoan executor scope (Cantina: M) | Honest-zero        |
| H15            | 3.2.1       | Deadline auto-flip PT drain (Cantina: H, accepted) | Honest-zero         |
| H16            | 3.2.2       | Blocked-token claim DoS (Cantina: M) | Honest-zero        |
| H17            | 3.3.6       | preLiquidate MEV (Cantina: M, partially fixed) | Honest-zero         |
| H18            | 3.2.5       | onRequestConsumed reentrancy (Cantina: M, acknowledged) | Honest-zero  |
| H19            | 3.3.22/23 + 3.4.7 | ParetoFund epoch gating (Cantina: 3x ME/Info, accepted) | Honest-zero   |

## Source pinning (unchanged from v6.16)

- `sources/3f-grunt/repo` pinned at `89cbfa01e5d14c34354ef715757bc84289cc2d04`
- Audit baselines: `chainsecurity_grunt=7056bb17257b7745fed054e7ba158f5f48cfda2c`,
  `cantina_grunt=adcdd5002188ecbe05cf272347bc80350ae52b8c`

## Artifacts shipped

### H13 — External Morpho debt repayment inflates performance fees (Cantina 3.3.21)
- `sources/3f-grunt/repo/test/manager/GruntH13ExternalDebtFeeInflation.t.sol`
- 10 falsifiers across full morpho market math
- **Key finding: `testFinding_externalRepay_constantOracle_perfFeeAccruesOnDonation`**
  - Setup: `management=0` PM, single Morpho market, NAV ≈ 1.0
  - Action: external party calls `morpho.repay(500e18, shares)` to burn shares
    but reduce market's `totalBorrowAssets`/`totalBorrowShares` ratio
  - Result: on the next `accrueInterest()`, ~92.59e18 perf-fee shares are minted to
    `feeRecipient` purely from the donation. Skim reverses directly with LOG GATING
    but is real and quantitatively measured (donation 500e18 → fee shares 92.59e18).
  - Scope-fit: confirmed `kill_criteria` match (perf fee IS supposed to be charged on
    interest growth; "donation" is treated as the residual; feeRecipient gains a free
    share-imprint of the borrower's donation). This corresponds to Cantina's ME
    rationale that the skim reduces LP value, not the borrower's direct loss.
  - Submission verdict: **candidate finding for the perf-fee-skim gate**, but
    acknowledged in audit (3.3.21 Info). Not escaped the gate.

### H14 — MorphoFlashLoanRequest executor scope (Cantina 3.3.25)
- `sources/3f-grunt/repo/test/request/GruntH14FlashLoanExecutorScope.t.sol`
- 7 falsifiers (executor role sufficiency, non-whitelisted script revert,
  lp-value preservation, etc.)
- **Honest-zero:** flash loan executor role correctly routes to whitelisted
  scripts; non-whitelisted scripts revert at the storage-write gate.

### H15 — Repayment deadline auto-flip (Cantina 3.2.1)
- `sources/3f-grunt/repo/test/request/GruntH15DeadlineAutoFlipDrain.t.sol`
- 6 falsifiers — preDeadline sync is no-op, postDeadline flips state, pullFunds
  reverts once deadline-lock is in place, PT redeem yields zero without a separate
  repayment.
- **Honest-zero with subtle observation:** PT holders' redemption yield IS zero
  after deadline + no manual repay. This MATCHES Cantina's documented H finding
  (3.2.1 risk-accepted). Demonstrating this at the test level confirms the protocol
  depends on the operator repay(ing) before the deadline; if they don't, PT face
  value goes to zero — but the **on-chain protection surface** (`syncRepaidStatus`
  forced-flip + `pullFunds` reverts) correctly prevents NEW pulls/exits.

### H16 — Claim(0, amounts) blocked-token DoS (Cantina 3.2.2)
- `sources/3f-grunt/repo/test/facility/GruntH16ClaimBlockedTokenDoS.t.sol`
- 5 falsifiers — uses a focused `RevertingToken: MockERC20` whose `transfer` always
  reverts; mirrors the contract.gov claim() loop logic to confirm DoS is per-token
  (other payout tokens continue to flow).
- **Honest-zero:** claim() iterates over independent `intent.payout` entries and
  per-token fails do not block downstream tokens; orders-by-key are unaffected unless
  the user's intent actually contains the reverting token.

### H17 — preLiquidate MEV front-running (Cantina 3.3.6)
- `sources/3f-grunt/repo/test/borrow/GruntH17PreLiquidateMEV.t.sol`
- 6 falsifiers — intervening repay changes math (`(seized, repaid)`) without
  necessarily reverting; tested under both `exactCollateral` and `exactShare` branches.
- **Honest-zero:** Morpho's `expectedBorrowAssets` / `expectedMarketBalances` gating
  catches front-running on the path-direction where previewed results diverge from
  settled results; observed (seized, repaid) differ under stale market state, which
  is expected reader-pattern behavior for any non-atomic liquidation.

### H18 — onRequestConsumed reentrancy (Cantina 3.2.5)
- `sources/3f-grunt/repo/test/request/GruntH18OnRequestConsumedReentrancy.t.sol`
- 6 falsifiers — uses MaliciousRequestCallback's EIP-1271 + custom sync-callback
  whose `onRequestConsumed` invokes `request.syncRepaidStatus`.
- **Honest-zero:** callback can call `syncRepaidStatus` from inside `consume()`,
  but pre-deadline it's a no-op (falsifier 1 + 3 confirmed); post-deadline the
  forced flip reverts the next `pullFunds` (falsifier 4 confirms isRepaid goes
  true; pullFunds gate still protects funds).
- Cantina's noted gap is that `syncRepaidStatus` is not guarded by `nonReentrant`
  — confirmed; but no path from reentrant call can extract value because the
  state change is local info and pullFunds is the gating primitive.

### H19 — ParetoFund epoch-gating (Cantina 3.3.22/23 + 3.4.7)
- `sources/3f-grunt/repo/test/funds/pareto/GruntH19ParetoEpochGating.t.sol`
- 6 falsifiers — keyring withdraw disabled blocks redeem; fresh tranche deposit
  commit succeeds; instant-withdraw detection reverts; redeem-create flow shows
  the gating surface all in one test.
- **Honest-zero:** all three Cantina ME/Info cases (3.3.22, 3.3.23, 3.4.7) are
  documented and the contract's gating is sound; the rehabilitative flow requires
  raw-control over keyring, which is trusted-role territory.

## NSS validators

- `tests/test_native_grunt.py` — 7 new v6.19 harness presence checks (H13..H19).

## Falsification summary

### Honest-zero (no new finding) — 6 of 7
H14, H15, H16, H17, H18, H19 are all honest-zero with concrete guards documented
and audit posture reproduced.

### Invoked findings — 1 of 7
**H13** documents the perf-fee-skim dynamic with quantitative measurement
(donation 500e18 → feeRecipient shares 92.59e18) but the audit (Cantina 3.3.21)
already records this as ME-level / acknowledged. **Submission gate tripped** by
documenting.

## Regression suite results

| Suite                                                  | Tests   | Result     |
|--------------------------------------------------------|---------|------------|
| `test/manager/*`                                       | 231     | all pass   |
| `test/borrow/*`                                        | 180     | all pass   |
| `test/funds/*`                                         | 426     | all pass   |
| `test/request/*`                                       | 406     | all pass   |
| `test/facility/*`                                      | 165     | all pass   |
| `test/facility/*`, `test/guard/*`, etc.                | ≈ 387   | all pass   |
| **New v6.19 GruntH1X** (12 suites, 7 files)            | **46**  | all pass   |
| **Full project**                                       | 1795    | all pass +1 skip |
| **NSS pytest**                                         | **878** | pass+12 skipped |
| `tests/test_native_grunt.py`                           | 21      | pass       |

## Gate result

- `submit_ready` for 3F Grunt = **0** in this session.
- H13 is the closest we came; it is **acknowledged-risk** in the Cantina report,
  so it does not escape the gate.
- v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain the active `submit_ready=1` packs
  (human gate pending).

## Reference paths

- SPEC plan: `~/.factory/specs/2026-06-24-v6-19-audit-gap-falsification-round-3.md`
- Audit PDFs in `~/.factory/memory/3f-grunt/` (4 PDFs extracted:
  ChainSecurity Grunt, ChainSecurity GruntFunds, Cantina Grunt, Cantina Fee Review)
- Static probe envelope (predecessor): `data/security_results/investigations/2026-06-25-v6-16-3f-grunt-static-probe/grunt_static_probe.json`
- NativeHarness: `src/night_shift_security/native/grunt.py`
- Foundry harnesses:
  - `test/manager/GruntH13ExternalDebtFeeInflation.t.sol`
  - `test/request/GruntH14FlashLoanExecutorScope.t.sol`
  - `test/request/GruntH15DeadlineAutoFlipDrain.t.sol`
  - `test/facility/GruntH16ClaimBlockedTokenDoS.t.sol`
  - `test/borrow/GruntH17PreLiquidateMEV.t.sol`
  - `test/request/GruntH18OnRequestConsumedReentrancy.t.sol`
  - `test/funds/pareto/GruntH19ParetoEpochGating.t.sol`
- NSS validator: `tests/test_native_grunt.py`
