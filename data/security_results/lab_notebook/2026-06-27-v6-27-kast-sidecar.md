# KAST/m_ext sidecar: Crucible cross-instance swap, H5 recantation, honest-zero outcome

**Date:** 2026-06-27  
**Author:** Droid (v6.27 KAST sidecar)  
**Duration:** ~6 hours  
**Targets:** `m_ext` (scaled-ui, crank, no-yield), `ext_swap`, `ext_a` (no-yield, cross-instance swap partner)

## Summary

This session conducted an deep-dive Crucible-based invariant fuzzing campaign on the KAST M0 Solana M Extensions bug bounty (Immunefi). After ~40,000+ total fuzzing executions across 5+ campaign variants, **no confirmed production defects were found**. The harness reached 23/23 actions across 2 m_ext instances + ext_swap CPI router, with 0 crashes in all campaigns.

## Key outcomes

### H5 definitive recantation

The earlier `claim_for` collateral check finding was conclusively determined to be a **false positive**. In crank mode, EXT tokens are plain tokens without ScaledUiAmount multipliers. The comparison `ext_supply + rewards > vault_ui` uses mathematically equivalent units:
- `ext_supply + rewards` = raw EXT tokens (1:1 with current M value at mint time)
- `vault_ui = principal_to_amount_down(vault_raw, m_index)` = vault M value in current M units

The check `ext_supply * INDEX_SCALE / m_index <= vault_raw` is algebraically equivalent to what the program does. The `claim_fees` instruction in scaled-ui mode uses a different formula (`principal_to_amount_up`) because scaled-ui EXT tokens DO have their own ScaledUiAmount multiplier — different variant, different accounting, not a contradiction.

### Cross-instance swap integration (ext_a + ext_swap)

Added a second m_ext instance (`ext_a`, no-yield variant at `3joDhmLtHLrSBGfeAe1xQiv3gjikes3x8S4N3o6Ld8zB`) alongside the primary instance. Integrated with `ext_swap` (`MSwapi3WhNKMUGm9YrxGhypgUEt7wYQH3ZgG32XoWzH`) for cross-instance swap operations:
- `ext_swap_wrap`: M -> EXT via ext_swap CPI passthrough
- `ext_swap_unwrap`: EXT -> M via ext_swap CPI passthrough  
- `ext_swap_swap`: EXT_A (no-yield) -> primary EXT (scaled-ui) via ext_swap CPI atomically (unwrap + wrap)

All 3 ext_swap actions executing correctly, 0 crashes.

### Value conservation invariant

Added a custom invariant check in `after_action()` that verifies `ext_supply * ext_index <= vault_raw * m_index` (total EXT value <= total vault M value). This catches any wrap/sync/claim sequence that creates value. Result: **0 genuine violations**. The only false positives came from `last_m_index` being stale in the global account between an `update_multiplier` and a `sync` call - the invariant uses the stored index while the program correctly uses the M mint's current multiplier.

### Campaign results (most recent)

| Variant | Actions | Executions | OK rate | Edges | Crashes |
|---------|---------|------------|---------|-------|---------|
| Scaled-ui (23-act, cross-instance) | 23/23 | 2,629 | 82% | 4,121/25,520 | 0 |
| Crank (23-act, cross-instance) | 23/23 | 2,308 | 61% | 4,239/25,844 | 0 |

## Files changed/created

- `sources/crucible/fuzz/kast/src/main.rs` — Full fuzzer: 23 actions, cross-instance swap, ext_swap CPI, value invariant
- `src/night_shift_security/native/kast_state_model.py` — Python state machine model (wrap/sync/claim/unwrap)
- `data/security_results/investigations/2026-06-27-v6-27-kast-sidecar/` — All investigation artifacts updated

## Carry-forward

The program has sustained 4 professional audits (Asymmetric Research, Adevar Labs, OtterSec, Halborn) and the Crucible harness now covers the complete instruction surface with cross-instance swap support. No further ROI expected from continued m_ext/ext_swap fuzzing. Recommend pivoting to a the next target.
