# 2026-06-21 — v6.6 Meteora DLMM Investigation

**Session:** Tenth orchestrator session (v6.6.0-proposal-session10)
**Target:** Meteora DLMM (LbVRzDTvBDEcrthxfZ4RL6yiq3uZw8bS6MwtdY6UhFQ, Solana)
**Outcome:** Honest-zero — 5th empirical-FNR datapoint. All attempts falsified.

## What was done

### NativeHarness scaffold
Created src/night_shift_security/native/meteora.py. Program ID confirmed from MeteoraAg/dlmm-sdk Anchor.toml.

### Ultrafuzz-pattern execution
Three independent fresh-perspective attempts:

1. Fee round-trip — compute_fee(a) vs compute_fee_from_amount(a + compute_fee(a)). Algebraically proven correct.
2. Bin advancement — Active cursor + liquidity extraction. Bin advances monotonically by 1 per depletion.
3. Fee splitting — split_fee() ceiling/floor interactions. Safe by subadditivity of floor.

### Empirical-FNR dataset (N=5)

| # | Substrate | Outcome |
|---|-----------|---------|
| 1 | Ethena V1 (EVM) | Honest-zero |
| 2 | Marginfi v2 (Solana) | Honest-zero |
| 3 | Kamino (Solana) | Honest-zero |
| 4 | Drift (Solana) | Honest-zero |
| 5 | Meteora DLMM (Solana) | Honest-zero |
