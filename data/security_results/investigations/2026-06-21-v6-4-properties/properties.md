# v6.4 Property Enumeration — Marginfi v2 (HEAD 4d57e2c)

**Date:** 2026-06-21
**Session:** v6.4.0-proposal-session8
**Source:** `sources/marginfi/repo/` (org renamed mrgnlabs→0dotxyz)
**Existing fuzz coverage:** `programs/marginfi/fuzz/fuzz_targets/lend.rs` covers Deposit, Borrow, UpdateOracle, Repay, Withdraw, Liquidate. Does NOT cover: FlashLoan, HandleBankruptcy, standalone AccrueInterest, LendingAccountClose.

## Invariant 1: Flash-fee purity (FlashLoan)

**Property:** The fee-free invariant of flash loans — no value leaks into or out of the system during a flash loan cycle.

**Source basis:** `flashloan.rs` — `start_flashloan` sets `ACCOUNT_IN_FLASHLOAN` flag; `end_flashloan` unsets flag THEN runs `check_account_init_health`. Rate limiter is bypassed during flash loan (by design). Health check is skipped DURING flash loan (by design), but enforced at END.

**Untested compositions:**
- Flash loan + liquidation (use borrowed funds to liquidate another account)
- Flash loan + handle_bankruptcy (call bankruptcy on another account during flash loan)
- Flash loan + self-liquidation (make self unhealthy, self-liquidate, profit from bonus)
- Flash loan across multiple banks (borrow A, deposit B, manipulate health)

**Existing test coverage:** `tests/user_actions/flash_loan.rs` covers 10 scenarios: basic success (1op, 3op), bad health, non-whitelisted, missing end, invalid sysvar, wrong order, wrong account, already-in-flashloan, transfer-during-flashloan. Does NOT cover flash+liquidate or flash+bankruptcy.

## Invariant 2: Conservation of value (Bankruptcy)

**Property:** After `handle_bankruptcy`, the bank's accounting is consistent: `total_asset_value + bad_debt_settled == old_total_asset_value + insurance_covered`.

**Source basis:** `handle_bankruptcy.rs` — order of operations:
1. `accrue_interest` (update share values)
2. Calculate `bad_debt = get_liability_amount(liability_shares)`
3. `covered_by_insurance = min(bad_debt, insurance_vault_balance)`
4. `socialized_loss = max(bad_debt - covered_by_insurance, 0)`
5. Transfer `covered_by_insurance` tokens from insurance vault → liquidity vault
6. `socialize_loss(socialized_loss)` — reduces `asset_share_value`
7. `repay(bad_debt)` — reduces liability shares (NO token transfer)

**Potential gap:** After steps 5-7, the liquidity vault has `old_balance + covered_by_insurance` tokens, but the accounting asset value is `old_total_value - socialized_loss`. The difference is `covered_by_insurance + socialized_loss = bad_debt`. This `bad_debt` excess sits in the vault as orphaned value. Need to verify if this is intentional buffer or a leak.

## Invariant 3: Oracle freshness during bankruptcy

**Property:** `handle_bankruptcy` uses `fetch_unbiased_price_for_bank` with `ok()` (returns `None` on error), meaning stale or unavailable prices silently fall back to cached prices.

**Source basis:** `handle_bankruptcy.rs` line 65: `let cached_price = fetch_unbiased_price_for_bank(...).ok()`. The `check_account_bankrupt` function (called earlier) uses the health cache which may contain stale prices. If the oracle is stale, the bankruptcy could be triggered at incorrect prices.

**Potential gap:** `MAX_PRICE_AGE_SEC` is enforced in `fetch_unbiased_price_for_bank`, but the `.ok()` converts errors to `None`, meaning ANY error (including staleness) results in using the cached price instead of failing. If the cache is stale, a non-bankrupt account could be incorrectly considered bankrupt.

## Invariant 4: Liquidation oracle consistency

**Property:** The liquidation check and the bankruptcy check should use the same health standard. If liquidation uses `Equity` health and bankruptcy uses `Maintenance` health, an account could be considered bankrupt (for bankruptcy purposes) while still being above the liquidation threshold.

**Source basis:** `check_account_bankrupt` calls `get_health_components` with `RiskRequirementType::Full` (need to verify). Liquidation uses `RiskRequirementType::Maintenance`. If there's a mismatch, an account might be liquidatable but not bankrupt, or vice versa.

## Invariant 5: Flash loan + rate limiter bypass

**Property:** During a flash loan, the rate limiter is bypassed (by design). This allows large borrows that would normally be rate-limited. If a user starts a flash loan, borrows a large amount (bypassing rate limits), and uses those funds to manipulate prices or liquidate accounts, the rate limiter protection is ineffective.

**Source basis:** `rate_limiter.rs` — `check_rate_limit` returns `Ok(())` early if `ACCOUNT_IN_FLASHLOAN` flag is set. This is by design for flash loan composability, but it means the rate limiter can be circumvented by wrapping any large borrow in a flash loan.

**Risk assessment:** This is likely "works as intended" (flash loans require returning funds within the same transaction, so the risk is bounded). But if the rate limiter is protecting against oracle manipulation, the bypass could be meaningful.

## Invariant 6: socialize_loss edge case — zero shares

**Property:** If `total_asset_shares == 0` (no depositors), `socialize_loss` will hit a division by zero in `checked_div(total_asset_shares)`.

**Source basis:** `socialize_loss` in `bank.rs`:
```rust
let new_share_value = (total_value - loss_amount)
    .checked_div(total_asset_shares)
    .ok_or_else(math_error!())?;
```
If `total_asset_shares == 0` and `total_value == 0` (since `0 * anything = 0`), then the first branch `total_value <= loss_amount` would trigger (0 <= loss_amount), setting `asset_share_value = 0` and `kill_bank = true`. So the division by zero is NOT reachable if `loss_amount > 0`. If `loss_amount == 0`, then `total_value (0) <= loss_amount (0)` is true, so the first branch triggers again. **This is safe.**

## Strategy priorities

| Priority | Strategy | Rationale |
|----------|----------|-----------|
| 1 | Flash loan + self-liquidation | Novel composition not in existing tests; potential health check bypass |
| 2 | Bankruptcy accounting consistency | Math-heavy, order-dependent, not in fuzz target |
| 3 | Oracle staleness in bankruptcy | `.ok()` swallows errors; stale price → false bankruptcy |
| 4 | Flash loan + liquidation of other account | Composition gap; rate limiter bypass |
| 5 | Flash loan + handle_bankruptcy | Cross-instruction interaction |
| 6 | socialize_loss with near-zero shares | Edge case in division logic |
