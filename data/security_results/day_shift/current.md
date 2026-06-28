# Session plan — v6.32 Silo Finance reentrancy validation + submission packaging

**Status: closed** (2026-06-28) — v6.32 Silo Finance v2/v3 reentrancy in defaulting liquidation (session-37).

## Summary

Full validation cycle for PROP-LIQ-SEQ-003-REENTRANCY: reentrancy window in `liquidationCallByDefaulting` where `Actions.repay()` lacks `turnOnReentrancyProtection()` before `beforeAction(REPAY)`. 50k protocol deficit confirmed on mainnet fork. False positive ruled out. Submission package assembled.

### Findings

**PROP-LIQ-SEQ-003-REENTRANCY — Reentrancy window in defaulting liquidation (Critical / Protocol Insolvency)**

Root cause: `Actions.repay()` calls `beforeAction(REPAY)` without enabling reentrancy protection. `liquidationCallByDefaulting` turns the guard off before `_repayDebtByDefaulting()`. A malicious hook reenters `ISilo.repay()` during this window, reducing `totalAssets[Debt]` twice (hook + outer liquidation) while collateral is seized once.

| Test | Status | Evidence |
|------|--------|----------|
| `test_exists` | PASS | Reentrancy window fires |
| `test_deficitExists` | PASS | Deficit = 50,000 tokens = hook repayment |
| `test_maxDeficit` | PASS | 116,645 deficit (33% of 350k debt) |
| `test_fork_exploit_exists` | PASS | 50k deficit on mainnet fork (block 22800000) |
| `test_fork_clean_noExploit` | PASS | No deficit without exploit on fork |
| `test_cleanLiquidation_balanced` | PASS | Protocol balanced when no REPAY hook |
| `test_edge_afterActionFires` | PASS | afterAction(REPAY) also fires without guard |
| `test_edge_lenderDepositsSafe` | PASS | Lender deposits preserved |
| `test_harnessNotArtifact` | PASS | IRM bypass has no effect on exploit |

**Known-issue check:** I-10 (Description audit) identified the window but not the exploit. `nonReentrant` on `PartialLiquidationByDefaulting` does NOT protect `ISilo.repay()`.

### What did NOT move

- **`submit_ready` unchanged**: still 1 (OnRe H1 from v6.13). Silo finding requires human gate.
- **No NSS pipeline changes**: 0 changes.

### Submission artifacts

- Submission report: `data/security_results/investigations/2026-06-28-v6-29-silo-finance-dual-liq/submission_report.md`
- Secret Gist: https://gist.github.com/tradewife/e5ef5d5e36809b30ffa28e491107e8ae
- `false_positive_checks.json`, `validation_summary.json`
- All 10 tests: `SiloDefaultingReentrancyPoC.t.sol` (8) + `SiloForkExploitTest.t.sol` (2)

## Submission gate status

| Gate | Status |
|------|--------|
| OnRe H1 (v6.13) | **submit_ready=1** (unchanged) |
| Silo reentrancy (v6.32) | **submission-ready, requires human gate** |
| Overall `submit_ready` | **1**, unchanged |
