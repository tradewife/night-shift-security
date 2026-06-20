Frame 2 — Kamino cumulative_borrow_rate ceiling.

**Question:** Can a saturation/wrap-around path in `compound_interest` or `borrow_factor_f` allow depositors to realize more interest than borrows actually paid?

**Verdict:** Falsified. See `attempt.md`. Five layered guards (BorrowRateCurve::validate, host_fixed_interest_rate_bps u16, get_borrow_factor floor at Fraction::ONE, BigFraction U256 storage ceiling, saturating u128 arithmetic) make ceiling-reaching mathematically infeasible.

**Status:** empirical-FNR datapoint candidate. The kamino_measured_delta.json's `cumulative_borrow_rate_changed=true` with `borrowed_amount_sf_delta=0` envelope is *exactly* the benign pattern this frame predicts when defenses work.

**Files in this artifact:**
- `attempt.md` — reasoning chain + reproduction analysis + reflection.
- `evidence.json` — falsification evidence envelope with five source anchors.

**Hand-off to Frame 3:** Cross-CPI in flash callback — does the explicit `is_flash_forbidden_cpi_call` guard hold in all entry-points, or can a kamino CPI be re-entered between flash-borrow and repay to mutate reserve state?
