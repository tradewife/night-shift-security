# Kamino KLend Flash-Loan Property Catalog (v6.8 Phase 2)

Source: `sources/kamino/klend/programs/klend/src/`
Date: 2026-06-21

## Flash-loan invariants

| ID | Property | Category | Source |
|----|----------|----------|--------|
| PROP-001 | Flash-loan fee is pure fn of `(amount, referral_fee_bps, has_referrer)`. Fee computed BEFORE reserve state mutation. | Fee purity | `lending_operations.rs:L2230` |
| PROP-002 | Every flash-borrow must have exactly one matching repay with identical amount and accounts. | Pairing | `flash_ixs.rs:flash_borrow_check_matching_repay` |
| PROP-003 | No CPI between borrow and repay. Stack height == TX level AND program_id == crate::ID. | No-CPI | `flash_ixs.rs:L67-71` |
| PROP-004 | Multiple flash-borrows in same tx rejected. | Single borrow | `flash_ixs.rs:L81-83` |
| PROP-005 | Flash loans disabled when flash_loan_fee_sf == u64::MAX. | Config gate | `lending_operations.rs:L2204` |
| PROP-006 | Vault balance == reserve accounting +/- token delta after every transfer. | Conservation | `lending_checks.rs:post_transfer_vault_balance` |
| PROP-007 | total_available_liquidity == vault_amount - borrowed + interest. | Accounting | `state/reserve.rs` |
| PROP-008 | cumulative_borrow_rate_bsf monotonically non-decreasing. | Rate monotonicity | `state/reserve.rs:accrue_interest` |
| PROP-009 | Obligation collateral >= liabilities * liquidation_threshold after every operation. | Health | `lending_checks.rs` |
| PROP-010 | Flash-borrow from reserve A does not affect reserve B available liquidity. | Isolation | Single-reserve operation |
| PROP-011 | refresh_reserve required before borrow/withdraw/liquidate. | Refresh ordering | `lending_checks.rs` |
| PROP-012 | Fee calc only reads flash_loan_fee_sf, not cumulative_borrow_rate or total_borrows. | Fee independence | `calculate_flash_loan_fees` |

## Attack hypotheses

| ID | Hypothesis | Risk |
|----|-----------|------|
| H1 | Fee bypass via reserve state mutation between borrow and repay | Medium - PROP-014 says fee is independent, but verify empirically |
| H2 | Flash-loan composition with obligation health check race | High - obligation health may be stale during flash window |
| H3 | Multi-flash-loan bypass across blocks via slot timing | Low - PROP-004 catches same-tx, cross-tx is separate |
| H4 | Fee precision loss at small amounts (1 lamport) | Medium - integer division could produce zero fee |
| H5 | Token-2022 double-charge (transfer fee + flash fee) | Medium - depends on token extension interaction |

## Test strategy

Each hypothesis maps to a strategy in Phase 3:
- H1 -> Strategy 1 (fee edge cases)
- H10 -> Strategy 2 (cross-reserve composition)  
- H9 -> Strategy 3 (obligation lifecycle)
- H2 -> Strategy 4 (liquidation + flash-loan race)
- H5 -> Strategy 5 (Token-2022)
