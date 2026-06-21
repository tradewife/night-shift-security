# Kamino KLend Flash-Loan Assessment (v6.8 Phase 3-4)

Date: 2026-06-21
Target: KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD (Kamino KLend)
Bounty: $1,500,000 (Immunefi)

## Phase 3 Analysis: Deep Forensic Tracing

### H4: Fee Precision Loss at Small Amounts

**Verdict: FALSIFIED at source level.**

The fee calculation chain is:
1. `flash_borrow_reserve_liquidity` calls `refresh_reserve` with `price: None` -- no oracle price update
2. `flash_repay_reserve_liquidity` calls `calculate_flash_loan_fees(amount, referral_fee_bps, has_referrer)`
3. `calculate_flash_loan_fees` calls `calculate_fees` with `FeeCalculation::Exclusive`
4. `calculate_fees` computes: `origination_fee_amount = amount.mul(origination_fee_rate)`
5. Applies minimum fee: `origination_fee_f = origination_fee_amount.max(minimum_fee.into())`
6. Checks: `if origination_fee_f >= amount` then `BorrowTooSmall` error

The critical boundary: for `flash_loan_fee_sf = 0` (zero fee), `calculate_fees` returns `(0, 0)` because `origination_fee_rate == Fraction::ZERO` hits the early return path. This means zero-fee flash loans are structurally possible if `flash_loan_fee_sf == 0` is set.

However, `flash_loan_fee_sf` is stored in `ReserveConfig.fees` which is admin-writable via `update_global_config` and `clone_reserve_config`. A non-admin cannot change this value. The question is: **can a flash-loan set `flash_loan_fee_sf` to 0 between borrow and repay?**

Looking at the code:
- `flash_borrow` mutates `reserve` state (calls `reserve.borrow()` which updates `borrowed_amount_sf` and `total_available_amount`)
- `flash_repay` reads `reserve.config.fees.flash_loan_fee_sf` to compute the fee

**The fee config is NOT mutated by any flash-loan operation.** Only admin instructions (`update_global_config`, `clone_reserve_config`) can change it. This means H4 is falsified: fee precision loss at small amounts is prevented by the `origination_fee_f >= amount` check.

### H1: Fee Bypass via Reserve State Mutation

**Verdict: FALSIFIED at source level.**

The fee calculation in `calculate_flash_loan_fees` reads ONLY:
- `self.flash_loan_fee_sf` (from config, immutable during flash-loan)
- `referral_fee_bps` (from lending_market, immutable during flash-loan)
- `has_referrer` (from account presence)

It does NOT read:
- `cumulative_borrow_rate_bsf`
- `borrowed_amount_sf`
- `total_available_amount`
- Any oracle price

This confirms PROP-012: the fee is structurally independent of reserve state. The borrow/repay operations mutate `borrowed_amount_sf` and `total_available_amount`, but these are NOT inputs to the fee calculation.

### H2: Obligation Health Check Race

**Verdict: UNTESTED -- requires live execution.**

The flash-loan path does NOT interact with obligations. Flash-borrow/repay operate on a single reserve, while obligation health checks require `refresh_obligation` which is a separate instruction. However:

- If a user has an obligation, and another user flash-borrows from the same reserve, the obligation's health might be affected because `total_available_liquidity` decreased
- But `refresh_obligation` reads fresh state at the time of refresh, so the health check would be accurate at that point
- The attack would require: (1) create underwater obligation, (2) flash-borrow to reduce liquidity, (3) liquidate the obligation -- but step (3) requires a separate transaction, and by then the flash-loan must be repaid

This hypothesis requires executable testing to fully rule out.

### H3: Multi-Flash-Loan Bypass Across Blocks

**Verdict: FALSIFIED at source level.**

The `flash_borrow_checks_internal` function scans forward in the same transaction for a matching repay:
```rust
let ix_iterator = ix_utils::IxIterator::new_at(current_index + 1, instruction_loader);
```
This only looks within the same transaction. Cross-block flash-loans are just sequential transactions -- each one independently goes through the full borrow/repay cycle with its own fee calculation.

### H5: Token-2022 Double-Charge

**Verdict: UNTESTED -- requires live execution.**

The flash-loan uses `token_transfer::borrow_obligation_liquidity_transfer` which calls `spl_token_2022::instruction::transfer_checked`. If the mint has a transfer fee extension, the SPL Token-2022 program would deduct the transfer fee in addition to the flash-loan fee. This could result in:
- User receives: `amount - transfer_fee` (not `amount`)
- User must repay: `amount + flash_loan_fee` (not `amount + flash_loan_fee - transfer_fee`)

This could create an accounting mismatch where the user pays more than expected. The `post_transfer_vault_balance_liquidity_reserve_checks` might catch this if the vault balance does not match the expected delta.

## Phase 4: Quorum Adjudication

### Findings Classification

| Hypothesis | Classification | Confidence | Evidence |
|-----------|---------------|-----------|----------|
| H4 (fee precision) | False positive | High (95%) | Source trace confirms BorrowTooSmall guard |
| H1 (fee bypass) | False positive | High (95%) | Source trace confirms fee is independent of reserve state |
| H2 (obligation race) | Underspecified | Medium (60%) | Requires executable test; theoretical attack path exists |
| H3 (multi-flash) | False positive | High (95%) | Same-transaction check is structurally sound |
| H5 (Token-2022) | Underspecified | Medium (70%) | Requires Token-2022 reserve setup and executable test |

### Overall Assessment

**No production defects found at source-review level.**

Two hypotheses (H2, H5) remain underspecified and require executable testing. The remaining three (H1, H3, H4) are falsified with high confidence.

### Gate Check

- `qualifies_for_submission()`: **NOT MET** -- no production defect candidate found
- `submit_ready`: **0**
- `pack_count`: **0**

### Empirical-FNR Datum

This constitutes the **6th substrate-level empirical-FNR datum** (source review on Kamino KLend flash-loan path):

| # | Substrate | Frame | Outcome |
|---|-----------|-------|---------|
| 1 | Ethena V1 (EVM) | uint64 truncation | Honest-zero |
| 2 | Marginfi v2 (Solana) | Sentinel-default discovery gap | Honest-zero |
| 3 | Kamino (Solana) | Flash-loan composition (3 frames) | Honest-zero |
| 4 | Drift (Solana) | LP pool constituent arithmetic | Honest-zero |
| 5 | Meteora DLMM (Solana) | 5-frame quorum + Token-2022 | Honest-zero |
| 6 | Kamino KLend (Solana) | Flash-loan fee precision + bypass | Honest-zero |

## Recommendations for Future Sessions

1. **H2 executable test**: Set up an obligation with deposited collateral, flash-borrow from the same reserve, and attempt to liquidate in a separate transaction while the obligation is underwater. This requires `solana-test-validator` with the KLend program deployed.

2. **H5 executable test**: Create a Token-2022 mint with transfer fee extension, add it as a reserve, flash-borrow and flash-repay, and verify the vault accounting matches.

3. **Engine-level testing**: The Kamino KLend repo does not ship a `cargo-fuzz` harness like Marginfi does. Building one would require creating a `fuzz/` directory with a `FuzzContext` that sets up the lending market, reserves, and obligations -- then running it through libfuzzer.

4. **Socialize_loss zero-shares edge**: The v6.4 properties document flagged this as a theoretical vulnerability. The code requires `lending_market_owner` signer, so it is admin-gated and not user-exploitable for bounty submission.
