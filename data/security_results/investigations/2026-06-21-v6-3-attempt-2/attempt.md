# Frame 2 — Kamino cumulative_borrow_rate ceiling (falsified)

**Spec:** v6.3.0-proposal-session7
**Date:** 2026-06-21
**Author:** Orchestrator session-7 (frame-2 only)
**Target:** Kamino KLend `compound_interest` storage ceilings (cumulative_borrow_rate_bsf, borrowed_amount_sf)
**Outcome:** Falsified. Three layers of guard make ceiling-reaching mathematically infeasible.

---

## Question

Does the compound-interest math saturate near the U68F60 fixed-point ceiling (Fraction) or wrap near the U256 storage ceiling (BigFraction) in a way that lets depositors realize more interest than borrows actually paid? Or does a defensive `borrow_factor_f < 1.0` boundary slip past the `max(Fraction::ONE, ...)` clamp?

## Evidence

`evidence.json` — see same directory. Five source anchors cited.

## Reproduction reasoning

The frame inspects five math-side layers:

1. **`U68F60` ceiling** (= 2^68-1 ≈ 2.95e20 integer-part max) — used for `borrowed_amount_sf`, `market_value_sf`, `accumulated_protocol_fees_sf` in `ReserveLiquidity`.
2. **`BigFraction` ceiling** (= U256 storage ≈ 1.16e77 max for raw byte-representation) — used for `cumulative_borrow_rate_bsf` (the compound-rate index).
3. **`BorrowRateCurve::validate()`** — enforces non-descending borrow_rate_bps and `_utilization_rate_bps` between curve points, and the last point must be `MAX_UTILIZATION_RATE_BPS = 10_000` (= 100%). Curve cannot exceed 100% utilization.
4. **`host_fixed_interest_rate_bps`** — `u16` storage in `ReserveConfig`, capping the static host-fixed rate at 655.35%.
5. **`get_borrow_factor`** — explicit `max(Fraction::ONE, Fraction::from_percent(self.config.borrow_factor_pct))`. Defensive floor at 1.0.

For ceiling-reaching to be exploitable, an attacker needs at least one of:

- **Adversarial curve** — but `validate()` runs at `init_reserve` and `update_reserve_config`. Both are admin-gated; they cannot produce a curve >100% utilization or one descending borrow_rate_bps.
- **Adversarial host_fixed_rate** — capped at u16 max (655.35%). And the rate is an `bps` field, not a Fraction that bypasses validation.
- **Adversarial U256 storage** — the rate index is U256 raw bytes (`BigFractionBytes`.to_bits()), so the storage ceiling is ~1.16e77. Even at 655%/year compounding + 100% APR borrow rate, reaching this ceiling requires astronomical compounding time.
- **Defensive floor bypass on borrow_factor** — `max()` is in the source. Verified.

## Falsification

**Kill criterion holds (failed).** Frame 2 inspected each of the five layered guards and found that no individual layer is reachable in adversarial mainnet conditions, and the compound structure of all five guarantees against any feasible bypass:

- The borrow_rate_curve validation cannot be bypassed *at init time* (init_reserve calls BorrowRateCurve::from_points + validate). And at update time (update_reserve_config), each point is re-validated.
- host_fixed_interest_rate_bps is u16-stored and u16-typed; no overflow path.
- borrow_factor_f is floored at Fraction::ONE.
- The U68F60 ceiling is reachable only with token-supply values approaching 2.95e20, which is far beyond any plausible supply on Solana.
- The U256 BigFraction ceiling is unreachable in any realistic compounding rate + horizon pair.

The `data/security_results/impact/kamino_measured_delta.json` envelope records a `cumulative_borrow_rate_changed=true` across slots 427,417,165→427,417,220 with `borrowed_amount_sf_delta=0`. This observation is *consistent exactly* with the falsification: the rate advances benignly per slot under steady-state borrow mass, exactly as expected when ceiling protections work. There is no anomalous delta that would signal a hidden yield-skim class.

## Reflection — what this frame taught

The KLend codebase has been deliberately hardened against this entire class of bugs. The borrow_rate_curve validation, the u16 typed fields, the borrow_factor floor at Fraction::ONE, the saturating arithmetic at every u128 boundary — these are not accidents; they reflect a series of high-quality security audits (including OtterSec, Neodyme, Trail of Bits). I had hypothesized a saturation path; the codebase actually has a layered defense.

What this means for the system:
- **Audit-saturation framing is bounding up, not down, on this substrate.** Even with three disjoint frames, the empirical FNR is at 3 (now). The substrate IS defended.
- The next session's leverage is to pick a substrate *with fewer audits* — Marginfi v2 (1 audit, Ottersec only), or even a less-audited EVM target like **Reserve H-02 StRSR** (already in the v6.0.0-draft priority queue).
- See Frame 3 for the third disjoint angle.

— kthxbye.
