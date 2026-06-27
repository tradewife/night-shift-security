# Strategy: scaled-ui sync and fee-claim drift

Properties:

- `PROP-KAST-002`
- `PROP-KAST-003`
- `PROP-KAST-013`
- `PROP-KAST-017`

## Aim

Target the highest-value rebasing question directly:

- repeated `sync` near fractional boundaries
- `set_fee` before and after rebasing steps
- `claim_fees` after mixed-size accrual epochs
- visible supply vs admin-claimable excess conservation

## Sequence families

1. `initialize -> wrap -> sync(delta_small)^n -> claim_fees`
2. `initialize -> wrap -> set_fee(f1) -> sync(delta_small) -> set_fee(f2) -> sync(delta_large) -> claim_fees`
3. `initialize -> wrap(dust) -> sync(delta_small) -> wrap(medium) -> sync(delta_small) -> claim_fees -> unwrap`
4. `initialize -> wrap -> sync(delta_up) -> sync(delta_down_or_flat) -> sync(delta_up) -> claim_fees`

## Parameter focus

- ext index values just above and below a rounding threshold
- dust wrap sizes that interact poorly with `amount_to_principal_down`
- fee changes bracketing the same effective accrual window
- repeated zero-ish or flat syncs to test idempotency

## Expected false-positive classes

- local mirror multiplier states that the real M mint would never emit
- acknowledged dust-only rounding loss without measurable amplification
- simulated ext mint extension layouts that diverge from mainnet Token-2022 behavior

## Candidate signal

Promote only if repeated sync/claim sequences create measurable admin gain, measurable holder loss, or a repeatable divergence between bridge accrual and holder-visible/admin-visible value accounting.
