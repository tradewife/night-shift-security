# Strategy: crank earner lifecycle and claim ordering

Properties:

- `PROP-KAST-004`
- `PROP-KAST-005`
- `PROP-KAST-006`
- `PROP-KAST-012`
- `PROP-KAST-014`
- `PROP-KAST-015`

## Aim

Exercise the densest state machine in the target:

- earn manager lifecycle
- earner lifecycle
- `claim_for`
- `sync`
- `configure_earn_manager`
- recipient changes

## Sequence families

1. `initialize -> add_earn_manager -> add_earner -> sync -> claim_for`
2. `initialize -> add_earner -> transfer_earner -> sync -> claim_for`
3. `initialize -> add_earner -> remove_earner -> remove_orphaned_earner`
4. `initialize -> add_earn_manager -> configure_earn_manager -> sync -> claim_for`
5. `initialize -> add_earner -> set_recipient -> claim_for`
6. `initialize -> add_earner -> sync -> configure_earn_manager(f1) -> claim_for -> configure_earn_manager(f2) -> claim_for`
7. `initialize -> add_earner -> sync(delta1) -> transfer_earner -> sync(delta2) -> claim_for`

## Parameter focus

- zero, dust, and non-zero pending yield
- fee updates before and after claim
- stale vs fresh snapshot balance values
- earner transferred between managers with different fee bps
- index regressions or flat syncs relative to `last_claim_index`
- recipient updates immediately before claim

## Expected false-positive classes

- unreachable earn-program state because CPI partner account is incompletely modeled
- acknowledged simple pending-yield loss on removal without escalation
- stale snapshots that only revert cleanly
- trusted earn-authority misuse that requires arbitrary off-chain lies without protocol amplification

## Candidate signal

Promote only if lifecycle reordering duplicates yield, redirects yield to the wrong authority, retroactively reprices already-accrued rewards, or preserves a drainable orphan state after manager or earner transition.

## Fresh-context seed priorities

1. manager-to-manager transfers across mismatched fee schedules
2. stale snapshot balances submitted after intervening syncs
3. remove/reactivate/orphan cleanup ordering around inactive managers
