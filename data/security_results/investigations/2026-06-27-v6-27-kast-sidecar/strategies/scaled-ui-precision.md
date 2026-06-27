# Strategy: scaled-ui precision boundary

Properties:

- `PROP-KAST-002`
- `PROP-KAST-003`
- `PROP-KAST-012`
- `PROP-KAST-013`
- `PROP-KAST-017`

## Aim

Stress `sync`, `set_fee`, and `claim_fees` near boundary conditions where scaled-ui rebasing math, fee extraction, and repeated index updates may diverge.
The new focus is on repeated tiny multiplier changes, alternating small/large updates, and whether visible holder rebasing and fee-admin surplus stay aligned with bridge-side accrual.

## Sequence families

1. `initialize -> wrap -> sync -> claim_fees -> unwrap`
2. `initialize -> wrap -> sync -> sync -> claim_fees`
3. `initialize -> wrap(x) -> sync(delta1) -> wrap(y) -> sync(delta2) -> unwrap`
4. `initialize -> wrap -> set_fee(f1) -> sync(delta_small)^k -> claim_fees -> set_fee(f2) -> sync(delta_large) -> claim_fees`
5. `initialize -> wrap(dust) -> sync(delta_small) -> wrap(medium) -> sync(delta_small) -> unwrap(dust) -> claim_fees`
6. `initialize -> wrap -> sync(delta_up) -> sync(delta_flat) -> sync(delta_up) -> claim_fees`

## Parameter focus

- balances near 1, tiny dust, and medium balances
- fee bps near `0`, small non-zero, and upper bound
- repeated `sync` with very small positive deltas
- alternating small and large deltas
- repeated `set_fee` with the same fee to test idempotency around sync boundaries
- visible ext supply vs admin-claimable surplus after each sync edge

## Expected false-positive classes

- mirror arithmetic that does not match Token-2022 scaled-ui semantics
- harness-created multiplier states unreachable on chain
- fee rounding that only produces acknowledged dust behavior
- ext mint or scaled-ui extension states that a local mirror can synthesize but the real M mint cannot

## Candidate signal

A candidate is only promoted if repeated sequences produce net caller/admin gain beyond pure acknowledged dust, if holder-visible rebasing diverges from bridge-side accrual in a repeatable way, or if fee claim drains more than the protocol fee bucket.

## Fresh-context seed priorities

1. tiny repeated multiplier bumps around the same base index
2. alternating dust and medium wraps between syncs
3. fee flips immediately before and after `sync`
