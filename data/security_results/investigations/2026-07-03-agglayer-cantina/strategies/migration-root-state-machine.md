# Strategy: Migration Root State Machine

## Properties Covered

- `PROP-AGG-004`
- `PROP-AGG-010`

## Hypothesis

The migration branch in `verifyPessimisticTrustedAggregator` is intentionally exceptional: it requires `newLocalExitRoot == rollup.lastLocalExitRoot`, then temporarily sets `rollup.lastLocalExitRoot = 0` before building verifier inputs and clears `isRollupMigrating`. A bug here could roll back roots, complete migration under incomplete bridge coverage, or desynchronize `getRollupExitRoot()`.

## Plan

1. Create local rollup with non-zero `lastLocalExitRoot`.
2. Toggle migration state using the same path production uses.
3. Exercise:
   - correct bootstrap LER,
   - mismatched LER,
   - zero LER special case,
   - repeated migration call,
   - concurrent rollup root update before/after migration.
4. After each accepted transition, independently compute rollup exit root and compare to `AgglayerManager.getRollupExitRoot()`.

## Expected False Positives

- Mock verifier accepts impossible proof inputs.
- Setup bypasses the production aggchain deployment path.
- Independent root calculator uses wrong sparse tree depth or ordering.

## Promotion Evidence

- Local EVM trace showing accepted state transition that violates expected migration state or root aggregation.
- Minimal reproduction with pre/post `RollupData`, `isRollupMigrating`, GER root map, and events.
