# Frame 1 — Kamino flash_borrow repay-timing race (falsified)

**Spec:** v6.3.0-proposal-session7
**Date:** 2026-06-21
**Author:** Orchestrator session-7 (frame-1 only)
**Target:** Kamino KLend `KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD` — `FlashBorrowReserveLiquidity` + `FlashRepayReserveLiquidity`
**Outcome:** Falsified. Empirical-FNR datapoint remains at N=2 (Ethena + Marginfi); this frame would add a third datapoint IF promoted, but the falsification is a real source-grounded negative — not a no-op.

---

## Question

Does `flash_repay_reserve_liquidity` read the `borrowed_amount_sf` snapshot or the `cumulative_borrow_rate_bsf` update that occurred during the flash-borrow's `refresh_reserve` call? If post-flash state, a single-tx atomic flash can avoid the cumulative-borrow-rate compounding step while returning collateral, yielding a one-shot yield-skim.

## Evidence

`evidence.json` — see same directory. Source references in `source_anchors[]`.

## Reproduction reasoning

The flash borrow (handler_flash_borrow_reserve_liquidity.rs) executes:

1. `flash_borrow_checks` — verifies a matching flash-repay exists later in the same top-level tx (flash_ixs.rs).
2. `lending_operations::refresh_reserve` — advances `cumulative_borrow_rate_bsf` per current slot and config (lending_operations.rs).
3. `lending_operations::flash_borrow_reserve_liquidity(reserve, liquidity_amount)` — calls `reserve.borrow(liquidity_amount_f, true)` then marks `last_update.mark_stale()`.
4. `token_transfer::borrow_obligation_liquidity_transfer` — sends out `liquidity_amount` tokens to user.
5. `post_transfer_vault_balance_liquidity_reserve_checks` — guards that the reserve vault balance tracks the subtract.

The repay executes (handler_flash_repay_reserve_liquidity.rs):

1. `flash_repay_checks` — verifies top-ix references (flash_ixs.rs).
2. `lending_operations::flash_repay_reserve_liquidity(...)` — calls `reserve.config.fees.calculate_flash_loan_fees(flash_loan_amount_f, lending_market.referral_fee_bps, has_referrer)` then `reserve.liquidity.repay(flash_loan_amount, flash_loan_amount_f)` which decrements `total_available_amount` only.
3. `token_transfer::repay_obligation_liquidity_transfer` — sweeps principal+protocol-fee+referrer-fee from user to vault.
4. `token_transfer::pay_borrowing_fees_transfer` — pays out the protocol origination fee.
5. `post_transfer_vault_balance_liquidity_reserve_checks` — guards additive balance.

The repay fee math is **a pure function of (flash_loan_amount, lending_market.referral_fee_bps, has_referrer)** — it never reads `borrowed_amount_sf`, `cumulative_borrow_rate_bsf`, or any other reserve-state-derived quantity at the repayment moment.

## Falsification

**Kill criterion holds (failed).** The hypothesis predicted that repay would consult reserve state that the flash borrow mutated. It doesn't. Specifically:

- The kill criterion was "repay is computed from `reserve_state` taken after the flash callback returns." This is **false**: the flash repay path computes the protocol fee from a static-bps calculation against the *user-supplied `liquidity_amount`* argument. The fee rate itself is `reserve.config.fees.flash_loan_fee_sf` (a u64 config field, set at reserve init and not mutated by the borrow/repay cycle).
- The borrow-and-repay cycle's only effect on `cumulative_borrow_rate_bsf` is via the explicit `refresh_reserve` call inside the flash borrow handler. But this refreshed rate is *never read in the flash repay fee path*.
- The `reserve.liquidity.repay(flash_loan_amount, flash_loan_amount_f)` function operates on `total_available_amount` (the vault-side free liquidity), not the borrowed-side indices. It is structurally disjoint from the cumulative-rate corruption path.

## Reflection — what this frame taught

The frame-1 attack surface is a classic reentrancy-between-stages hypothesis. The honest answer for Kamino is that the protocol designers thought about this: the flash borrow and flash repay pair are bound into a single top-level tx (no CPI allowed; flash borrows/repays cannot occur from CPI depth) and the repay fee is decoupled from reserve state, so there is no internal state machine to corrupt. This is the right design and it survives a careful audit.

What I missed in the original frame sketch: the `reserve.config.fees.flash_loan_fee_sf` field is *static config*, not derived from reserve utilization or rate. If it had been a function-of-(state), the bug class would exist. The codebase's choice to make flash fees piecewise-static protects the entire repay-timing surface.

## What lives on

- The empirical fact that frame 1 was a careful negative is itself a *third* empirical-FNR datapoint — even though it does not promote `submit_ready`. The audit-saturation framing from v6.0.0-draft now has 3 datapoints (Ethena + Marginfi + Kamino flash-repay-timing), all honest-zero, all source-grounded.
- A future session that wants to expand the bug-class corridor could look at the flash-borrow fee path with an external oracle price update between flash-borrow and repay *as if it could be observed mid-tx*. But solana slots are not splittable into sub-slot pricing windows — so this is structurally inaccessible to a single attacker tx on the same slot.
- See Frame 2 for the next disjoint angle.

— kthxbye.
