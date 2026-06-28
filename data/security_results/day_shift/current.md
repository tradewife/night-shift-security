# Session plan — v6.31 Raydium CP-Swap + CLMM forensic depth

**Status: closed** (2026-06-28) — v6.31 Raydium CP-Swap + CLMM additive forensic depth (session-36).

## Summary

Re-audit of the two Raydium programs (CP-Swap and CLMM, Immunefi $505K) for adversarial depth. Both had been previously walked in the broader v-cycle audit baseline (see CHANGELOG entry ".v6 x cycle results" — "Audited 8 well-defended DeFi protocols (Kamino, Uniswap v4, Aave v3, Raydium, Wormhole, Orca, Jito, Morpho)"). This pass adds the explicit exploit-grade verification: numerical fuzz of new feature math, full trace of Token-2022 mint-safety flow, cross-program CPI audit, precision/solvency stress, oracle manipulation bounds.

### Findings (5 deep-dive lanes)

1. **CLMM limit order settlement fuzz** — `hermes/scripts/clmm_limit_order_fuzz.py`. **100,000 + 5 iterations, 0 anomalies.** No over-payment, no vault drain, no dust compounding. The per-segment `-1` dust deduction in `settle_filled_order` is correctly bounded — single-token loss per segment, not cumulative across orders.
2. **Token-2022 PermanentDelegate extension** — `is_supported_mint` (5-step check) in BOTH CP-Swap and CLMM was traced. Step 3 (SupportMintAssociated ATA bypass) is gated by 2 hardcoded admin keys per program. **Regular users cannot create pools with dangerous mints.** **Design concern** (NOT exploit): CLMM is missing `close_support_mint_associated.rs` (CP-Swap has it). Once registered, CLMM support mints cannot be revoked. Admin discipline required.
3. **Cross-program CPI between CP-Swap and CLMM** — **None.** Programs are isolated. Only standard-program CPIs (SPL Token, Token-2022, System, ATA, Metaplex NFT for CLMM positions).
4. **CLMM reward distribution precision** — Q64.64 growth simulation across L=10^6..10^24. Vault shortfall graceful. `claim + owed ≤ emitted` invariant holds. wrapping_add overflow non-viable in practice.
5. **Observation oracle TWAP manipulation** — buffer = 25 min (100 obs × 15s spacing), validator ±15s timestamp influence, `tick_cumulative` overflow at max-tick takes ~660k years (non-issue). External-protocol trust risk only.

### What did NOT move

- **`submit_ready` unchanged**: still 1 (OnRe H1 from v6.13). No new candidate from Raydium depth survived `qualifies_for_submission()`.
- **No NSS pipeline changes**: 972 tests still passing; baseline unchanged on the path the cron uses.
- **No bounty submission made**: this was a forensic-depth pass, not an active hunt.

### Files / artifacts

- **CHANGELOG.md** — appended v6.31 entry.
- **SPEC.md** — version bumped to `6.31.0-raydium-forensic-depth-session36`; new §0.0 block (existing pattern).
- **Lab notebooks** — `data/security_results/lab_notebook/2026-06-28-raydium-forensic-analysis.md` (initial pass), `…-raydium-phase2-analysis.md` (interim), `…-raydium-phase2-complete.md` (final).
- **Fuzz harness** — `hermes/scripts/clmm_limit_order_fuzz.py` (re-runnable, deterministic).
- Archived v6.30 plan to `data/security_results/day_shift/archive/2026-06-28-v6-30-token2022-fee-invariants.md`.

### Recommendations (no action required this session)

1. **Track admin-key governance for `create_support_mint_associated`.** Both CP-Swap and CLMM admin keys (`GThUX1Atko4tqhN2NaiTazWSeFWMuiUvfFnyJyUghFMJ`) are gated, but if compromised they are the only path to a pool with a dangerous Token-2022 mint.
2. **Consider backport of `close_support_mint_associated` to CLMM.** Symmetry with CP-Swap; provides admin recovery in case of accidental registration.
3. **External protocols consuming Raydium TWAP** must implement their own validation layer; the 25-minute window is too short for safe liquidation gating relying on a single oracle source.
4. **Migration gating**: new pools should use `swap_v2.rs` (Token-2022 native) rather than the legacy SPL-only `swap.rs`.

## Submission gate status

| Gate | Status |
|------|--------|
| OnRe H1 (v6.13) | **submit_ready=1** (unchanged) |
| Raydium new findings | **0 submit_ready** (no candidate survived `qualifies_for_submission`) |
| Overall `submit_ready` | **1**, unchanged |

## References

- CHANGELOG.md v6.31 entry
- SPEC.md §0.0 v6.31 block
- `data/security_results/lab_notebook/2026-06-28-raydium-phase2-complete.md`
- `hermes/scripts/clmm_limit_order_fuzz.py`
- `sources/raydium/cp-swap-repo/` and `sources/raydium/repo/` (cloned; gitignored per AGENTS.md)
