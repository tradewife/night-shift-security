# Strategy: crank yield desync and fee retroactivity

Properties:

- `PROP-KAST-004`
- `PROP-KAST-005`
- `PROP-KAST-006`
- `PROP-KAST-014`
- `PROP-KAST-015`

## Aim

Probe the interaction between:

- `sync`
- `claim_for`
- `configure_earn_manager`
- `transfer_earner`
- `set_recipient`

with emphasis on stale snapshot balances, manager fee flips, and earner migration across fee domains.

## Sequence families

1. `initialize -> add_earn_manager -> add_earner -> sync -> claim_for(snapshot_a)`
2. `initialize -> add_earner -> sync -> configure_earn_manager(f1) -> claim_for -> configure_earn_manager(f2) -> claim_for`
3. `initialize -> add_earner -> sync(delta1) -> transfer_earner -> sync(delta2) -> claim_for`
4. `initialize -> add_earner -> set_recipient -> sync -> claim_for -> remove_earner/remove_orphaned_earner`

## Parameter focus

- snapshot balances below, equal to, and above the intuitive expected value
- index regressions, flat syncs, and resumed positive syncs
- manager fee schedules that jump from 0 to high values and back
- recipient changes just before a claim

## Expected false-positive classes

- trusted earn-authority assumptions where arbitrary snapshot lies are in scope by design
- clean reverts on stale or already-claimed states
- orphan cleanup behavior that only recovers rent without affecting claimable yield

## Candidate signal

Promote only if the sequence causes repeatable yield duplication, retroactive fee rewriting, wrong-recipient payout, or a freeze/revival pattern that misprices later claims.
