# Next session queue

**Ammalgam DLEX Cantina closed honest-zero with extended provenance (2026-07-13).** No submit-ready bug identified. Transition to next target.

## Priority 0 — Next target selection

Per SPEC §4.4, recommended next targets:

1. **MarginFi v2** (Solana lending): NativeHarness scaffolded at `scaffolded_count=2` (ethena_native + marginfi_v2). Needs canonical Marginfi v2 group + USDC bank PDA seeds resolved (SDK resolution, filtered getProgramAccounts, or explorer lookup), then probe driver re-run to flip marginfi_v2 from scaffolded → ready.
2. **Higher-signal Cantina/Sherlock bounty**: Evaluate current bounty landscape for unaudited or fresh-contest targets with higher submission probability.

## Residual — Ondo Perps (deferred, not closed)

Ondo Perps surfaces exhausted across all waves (0 unauthorized_success, no CHM candidate). Residuals tracked in INVESTIGATION_STATUS.md — only actionable with SIWE re-auth, re-fund, or if Ondo enables WS private channels. Do not reopen without a concrete new impact angle.
