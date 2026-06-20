# Frame 3 — Kamino flash-callback CPI composition (falsified)

**Spec:** v6.3.0-proposal-session7
**Date:** 2026-06-21
**Author:** Orchestrator session-7 (frame-3 only)
**Target:** Kamino KLend `is_flash_forbidden_cpi_call` + cross-instruction composition between flash_borrow and flash_repay
**Outcome:** Falsified. Two converging defenses (CPI deep-strict + repay-fee static) confirm the bug class does not exist.

---

## Question

Can a CPI (direct or indirect) into Kamino's own instructions mutate `reserve.liquidity` state between `flash_borrow_reserve_liquidity` and `flash_repay_reserve_liquidity` such that the repay computes a value-extracting fee? Or alternatively, can a user's top-level instruction between borrow+repay introduce value-extraction relying on a state-mutation path?

## Evidence

`evidence.json` — see same directory. Four source anchors cited.

## Reproduction reasoning

The frame inspects four layers:

1. **`is_flash_forbidden_cpi_call()`** — `ix_utils.rs` — checks BOTH conditions:
   ```rust
   if crate::ID != current_ixn.program_id { return Ok(true); }
   if get_stack_height() > TRANSACTION_LEVEL_STACK_HEIGHT { return Ok(true); }
   ```
   That is, the flash_* call must be at top-level (`get_stack_height() == TRANSACTION_LEVEL_STACK_HEIGHT`) AND the immediate caller must be `crate::ID` (which means it's top-level). Both must be true.

2. **`flash_borrow_check_matching_repay`** — `flash_ixs.rs` — strict byte-level matching:
   - `liquidity_amount` must match between borrow and repay (8 bytes le-equal at data offset 8..16).
   - `borrow_instruction_index` must equal the actual borrow-index at repay time.
   - Account layout must match exactly (account-by-account pubkey match, error `InvalidFlashRepay`).

3. **`flash_repay_reserve_liquidity` fee math** — `lending_operations.rs` — pure function of user-supplied `flash_loan_amount`, `lending_market.referral_fee_bps`, and `has_referrer`. **No reserve-state read at all.**

4. **Borrow-side refresh** — `handler_flash_borrow_reserve_liquidity` calls `refresh_reserve` which mutates `cumulative_borrow_rate_bsf` per current slot. This mutation is the *only* state mutation the borrow handler performs beyond `flash_borrow_reserve_liquidity` (which calls `reserve.borrow(liquidity_amount_f, true)`). The rate-mutation is what frame 1 already proved has no follow-up consumer in the repay math.

## Falsification

**Kill criterion holds (failed).** For cross-CPI of any form (direct or indirect) to extract value, BOTH (a) the borrow+repay pair must be susceptible to a state-mutation path that the repay consumes, AND (b) the repay-fee must be derivable from that state. Neither is true:

- **(a) false: Two layers of CPI defense.** First, `is_flash_forbidden_cpi_call` blocks CPI from below the tx-level. Second, the `flash_borrow_checks` walk from `current_index + 1` looking for a matching repay at top-level only. Even within top-level, the matching-account-layout check forces the *user's* account-shape to be identical between borrow and repay, eliminating room for an attacker to slip in unrelated kamino instructions that mutate state in value-extracting ways. 
- **(b) false: the repay math is independent of reserve state, also confirmed by frame 1.** A redundant confirmation is the strongest signal: two independent frames, each arriving at the same conclusion independently, using completely different lens (frame 1: source code inspect for math dependency; frame 3: source code inspect for CPI guard).

## Reflection — what this frame taught

The KLend codebase has explicit, well-designed CPI defenses. Even though the user composes a multi-instruction transaction that intermixes Kamino and non-Kamino programs, the flash_* pair enforces both single-pair AND top-level AND match-bytes. The triple constraint is what makes the protocol robust to reentrancy across any depth.

A class of vulnerability that *would* exist on a less-careful codebase:
- A naive flash_borrow+flash_repay pair that did NOT pin `get_stack_height() == TRANSACTION_LEVEL_STACK_HEIGHT` would expose itself to nested CPl from a composable outer program (e.g., a meta-flash aggregator). 
- Kamino explicitly forbids this, making KLend a stricter protocol than Compound v3 (which permits flashBorrow at non-tx-level in some deployment paths).

What this means for the system:
- The empirical FNR for the v6.3 three-attempt structure is **3-of-3 falsified**, with two frames converging on a redundant confirmation that the repay-fee surface is structurally protected.
- This is a positive falsification result, not a negative one — and crucially, the *redundancy* between frames 1 and 3 is a real win for the multi-attempt structure (single-linear probes would not have produced the cross-frame corroboration).
- See the quorum file for the joint verdict and reflection on the v6.3 operating model itself.

— kthxbye.
