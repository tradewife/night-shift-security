Frame 1 — Kamino flash_borrow repay-timing race.

**Question:** Does the flash_repay fee math depend on the post-flash reserve state, opening a yield-skim via atomic flash-borrow+repay?

**Verdict:** Falsified. See `attempt.md`. The flash_repay fee is `(protocol_fee, referrer_fee) = reserve.config.fees.calculate_flash_loan_fees(flash_loan_amount_f, lending_market.referral_fee_bps, has_referrer)` — pure function of the user-supplied amount, the market-wide referral BPS, and a boolean. Reserve-side `borrowed_amount_sf` and `cumulative_borrow_rate_bsf` are never read in the repay path.

**Status:** empirical-FNR datapoint #3 candidate. Quorum-decision pending.

**Files in this artifact:**
- `attempt.md` — frame reasoning + reproduction analysis + reflection.
- `evidence.json` — falsification evidence envelope (kill-criterion evaluated, source anchors cited).

**Hand-off to Frame 2:** Cumulative-rate monotonicity ceiling — raises the question: is `reserve.liquidity.cumulative_borrow_rate_bsf` (BigFraction / U256 storage) reachable at ceiling in adversarial conditions, allowing depositors to skim yield beyond borrower-payment?
