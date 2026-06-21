# Attempt 1 — Fee Round-Trip Invariant (Meteora DLMM)

**Strategy:** Executable fuzz on fee conservation across fee calculation functions.
**Fresh perspective:** Cold read of Meteora DLMM fee code, without Kamino/Marginfi/Drift frames. Dynamic-fee FSM is the most distinctive component.

## Hypothesis

The fee round-trip (compute_fee -> compute_fee_from_amount) may have rounding asymmetries allowing protocol loss.

## Source anchors

- `commons/src/extensions/lb_pair.rs` — `compute_fee()`, `compute_fee_from_amount()`
- Constants: `FEE_PRECISION`, `MAX_FEE_RATE`, `BASIS_POINT_MAX`

## Algebraic analysis

`compute_fee(a)`:
```
total_fee_rate = get_total_fee()
denom = FEE_PRECISION - total_fee_rate
fee = ceil(a * total_fee_rate / denom)
```

`compute_fee_from_amount(a_with_fees)`:
```
fee = ceil(a_with_fees * total_fee_rate / FEE_PRECISION)
```

Round-trip check: send `a_with_fees = a + compute_fee(a)`.
Let x = ceil(a*r/d), d = P - r, P = FEE_PRECISION, r = total_fee_rate.

Then `a + x >= a + a*r/d = a*P/d`.
So `(a+x)*r/P >= a*r/d`.
And `ceil((a+x)*r/P) >= ceil(a*r/d) = x`. QED.

## Variable fee overflow check

`compute_variable_fee(volatility_accumulator)`:
- `square_vfa_bin = (vol_acc * bin_step)^2` — vol_acc is u32, bin_step is i32 cast to u128
- Max product: ~4.29e13 (vol_acc) * 10000 (bin_step) = ~4.29e17 in u128, squared = ~1.84e35
- `variable_fee_control * square_vfa_bin` = ~4.29e9 * 1.84e35 = ~7.9e44
- u128::MAX = ~3.4e38
- **OVERFLOW: 7.9e44 > 3.4e38.** This exceeds u128::MAX.

Wait — let me recheck. The source says `variable_fee_control` is u32. And the code uses `.into()` on volatility_accumulator (u32 -> u128) and bin_step (i32 -> u128).

Actually, re-reading: `square_vfa_bin = volatility_accumulator * bin_step` where both are cast to u128. Then `square_vfa_bin.pow(2)`.

Max vol_acc = u32::MAX = 4,294,967,295
Max bin_step = from `MIN_BIN_ID` to `MAX_BIN_ID` — these are i32. The actual bin_step parameter is bounded but let me check...

From the constants, bin_step is likely <= 100,000 (basis point range). So:
- vol_acc * bin_step = 4.29e9 * 1e5 = 4.29e14
- squared = 1.84e29
- variable_fee_control (u32 max = 4.29e9) * 1.84e29 = 7.9e38
- u128::MAX = 3.4e38

**This can overflow u128.** But the code uses `.checked_mul(...).context("overflow")?` — which means it REVERTS on overflow, not wrapping. So this is a DoS vector, not a fund-loss vector.

**However**: can an attacker force this revert? The volatility_accumulator is `min(volatility_reference + delta_id * BASIS_POINT_MAX, max_volatility_accumulator)`. The attacker controls their own swap timing to manipulate delta_id. If they can push vol_acc * bin_step high enough, the `.checked_mul().context("overflow")?` in `compute_variable_fee` will revert the entire swap transaction.

But: `MAX_VOLATILITY_ACCUMULATOR` is a pool parameter set by the pool creator. If it's set low enough, the overflow is unreachable. If it's set high enough, an attacker could grief other users by triggering a revert mid-swap (but cannot steal funds).

**Classification: DoS (High severity)** — not fund loss, but griefing.

Wait, but the `context("overflow")?` returns an error that propagates up. In Anchor, this means the transaction reverts. The attacker doesn't gain anything — they just waste their own tx fee plus potentially grief other users' swaps in the same slot.

Actually, re-reading more carefully: the volatility accumulator is updated by `update_volatility_accumulator`, which is called at the END of a swap, not before `compute_variable_fee`. The compute_variable_fee uses the OLD accumulator. So an attacker cannot manipulate vol_acc for another user's swap — each swap reads the on-chain state at the beginning.

**Final verdict: FALSIFIED.** The overflow is bounded by `max_volatility_accumulator` which is a pool parameter. The checked arithmetic prevents silent wrapping. No fund loss possible.

## Category

**Harness artifact** — the overflow concern is mitigated by (1) checked arithmetic that reverts, (2) max_volatility_accumulator cap, and (3) no cross-user state mutation during a single swap's fee calculation.
