# Lab notebook — x402 validator replay (Solend + Cashio)

**Date:** 2026-06-11  
**Wallet:** `8iRgfudGfynuiNWzyer1GArXeWQJkejWNeBA6VS8Yfjo` (dedicated NSS x402, devnet USDC funded)  
**RPC:** `SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989` → QuickNode x402 mainnet

## Same vs prior

Prior: validator replay blocked (no RPC / treasury wallet concern).  
Now: dedicated wallet + funded devnet USDC; strict reproduction green on two catalog anchors.

## Shell harness

| Exploit | SLOT_TARGET | SOLANA_VALIDATOR_PASS | IMPACT_USD |
|---------|-------------|----------------------|------------|
| solend-whale-2022 | 139896000 | 1 | 25M |
| cashio-2022 | 128587000 | 1 | 52M |

## Pytest

`tests/test_solana_live.py` — 2 passed after registering attack templates (was missing `governance_capture` import).

## Open

- Mango validator replay (`mango-markets-2022`) — Slice 3 profile exists
- First Immunefi submission pack with `deployed_viable` + Level 3–4 evidence