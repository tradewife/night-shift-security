# Next session queue

**Three bounties closed: Ammalgam DLEX (2026-07-13 honest-zero) + PancakeSwap Infinity (2026-07-13 honest-zero) + Intuition 4d-chess-sequential phase 2 (2026-07-14 honest-zero extended). All engine-level honest-zero with extended provenance. submit_ready unchanged (0).** No further pressure on these targets without trigger conditions (new hook configs, core upgrades, rule changes).

## Priority 0 — Next target

Per SPEC §4.4, the canonical next focus is **MarginFi v2** (Solana lending):

- NativeHarness scaffolded at `scaffolded_count=2` (ethena_native + marginfi_v2)
- Remaining work: Resolve canonical Marginfi v2 group + USDC bank PDA seeds (SDK resolution, filtered getProgramAccounts, or explorer lookup)
- Re-run probe driver
- Flip marginfi_v2 from scaffolded → ready

Alternative: Higher-signal Cantina/Sherlock bounty with unaudited or fresh-contest targets.

## Residual — Ondo Perps (deferred, not closed)

Ondo Perps surfaces exhausted across all waves (0 unauthorized_success, no CHM candidate). Residuals tracked in INVESTIGATION_STATUS.md — only actionable with SIWE re-auth, re-fund, or if Ondo enables WS private channels. Do not reopen without a concrete new impact angle.
