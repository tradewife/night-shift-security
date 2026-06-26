# Session plan — next
Status: queued

## Objective

Complete the Lombard follow-up on second-ring surfaces, then resume pre-existing carry-forward items (OnRe human-gate, WEB-003, 3F Grunt).

## Lombard carry-forward

1. **Lombard Token Pool as NativeHarness target**: CCIP-based pool with `base_token_pool` external crate — not suitable for Crucible IDL fuzzing. Requires Python/NativeHarness approach. Promote `lombard_token_pool.py` test from `tests/test_native_lombard.py`.
2. **RatioOracle consortium-rotation sequences**: Build a dedicated ratio_oracle test in harness or NativeHarness that exercises stale-ratio rejection after consortium upgrade.
3. **Corpus refinement for corridor + lbtc**: The 9-program corridor at 0.8% edge and lbtc at 5.1% edge leave substantial uncovered surface. Merge corpus from standalone consortium/mailbox/bridge runs into corridor.

## Pre-existing carry-forward

1. Resolve the OnRe human-gate decision (`data/security_results/bounty/submittable/onre/NSS-ONRE-1.json`).
2. Build a production-bootstrap PositionManager scaffold for H1-prime falsifier.
3. Stateful fuzz campaign on 3F Grunt H4/H9/H11/H17 surface.
4. WEB-003 review when Origin reviewers available.

## Blocks

- `secp256k1_recover` syscall in litesvm — blocks BasculeGMP CPI. Until resolved, `bascule_gmp=None` on AssetRouter remains required in harness.
