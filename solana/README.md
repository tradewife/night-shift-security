# Solana validation harness

Night Shift Security uses two distinguishable strict reproduction paths:

| Method | When | `solana_reproduced` |
|--------|------|---------------------|
| `solana_fixture` | CI default (fast) | Yes, with `IMPACT_USD` / `IMPACT_LAMPORTS` |
| `solana_validator` | `SOLANA_USE_VALIDATOR=1` + RPC + validator-backed exploit | Yes, requires `SOLANA_VALIDATOR_PASS:1` + `SLOT_TARGET` + impact |

## Quick start (fixture / CI)

```bash
cd solana && ./setup.sh
SOLANA_EXPLOIT_ID=mango-markets-2022 \
SOLANA_TARGET_ID=mango-markets-2022 \
SOLANA_SLOT=152000000 \
SOLANA_FIXTURE_TEST=mango_replay \
python3 run_fixture_test.py
```

## QuickNode x402 RPC bridge (no API key)

[Night Shift Security](..) validator replay expects a plain HTTP JSON-RPC URL in `SOLANA_MAINNET_RPC_URL`. QuickNode **x402** uses wallet auth + micropayments instead of API keys — **1M free RPC credits/month per wallet** on the shared agentic tier.

Local sidecar (`solana/x402-proxy/`) exposes `http://127.0.0.1:18989` and forwards to `https://x402.quicknode.com/solana-mainnet`:

```bash
# Prerequisites: Node 18+, dedicated wallet at solana/x402-proxy/.wallet/id.json
# Generate once: solana-keygen new --no-bip39-passphrase -o solana/x402-proxy/.wallet/id.json
# Fund that address with Solana Devnet USDC (Circle faucet) — not your system/treasury id.json
cd solana/x402-proxy && ./start.sh

# In another shell:
export SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989
export SOLANA_USE_VALIDATOR=1
```

| Env | Default | Purpose |
|-----|---------|---------|
| `X402_PAYMENT_NETWORK` | `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1` | Pay on devnet USDC; query mainnet |
| `X402_PAYMENT_MODEL` | `credit-drawdown` | SIWX + bulk credits (best for validator clone bursts) |
| `X402_PROXY_PORT` | `18989` | Local bind port (not 18789 — NSS API tests) |

**Hermes policy:** wallet-funded RPC requires explicit human approval in chat (SOUL). The free tier still uses your wallet for SIWX auth.

## Grant-demo validator replay (Slice 2)

Requires `solana-test-validator`, `solana-cli` (optional), and a mainnet RPC for account clones.

```bash
export SOLANA_MAINNET_RPC_URL=https://api.mainnet-beta.solana.com
# Or: export SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989  # x402 proxy
export SOLANA_USE_VALIDATOR=1

# Solend whale governance (slot ~139896000, Jun 2022)
SOLANA_EXPLOIT_ID=solend-whale-2022 ./run_validator_test.sh

# Cashio infinite mint (slot ~128587000, Mar 2022)
SOLANA_EXPLOIT_ID=cashio-2022 ./run_validator_test.sh
```

From the repo root:

```bash
export SOLANA_MAINNET_RPC_URL=<your-mainnet-rpc>
export SOLANA_USE_VALIDATOR=1
.venv/bin/python -m pytest tests/test_solana_live.py -v
```

### What the validator path does

1. Starts `solana-test-validator` with `--clone-upgradeable-program` for documented programs
2. Waits for local RPC health (`http://127.0.0.1:8899`)
3. Verifies cloned programs are executable on the local ledger
4. Emits strict evidence lines consumed by `solana_validation.py`

**Note:** `--clone` pulls current mainnet account state from your RPC. `SLOT_TARGET` is the documented historical reference slot; the local validator ledger starts fresh (`SLOT_CURRENT` will differ). Slice 3 may add slot-frozen archive replay where RPC supports it.

### Validator-backed vs fixture-only (Slice 2)

| Exploit | Historical slot | Validator-backed |
|---------|-----------------|------------------|
| `solend-whale-2022` | 139,896,000 | Yes |
| `cashio-2022` | 128,587,000 | Yes |
| `mango-markets-2022` | 152,000,000 | **Yes** (Slice 3 — `4MangoMjqJ2firMokCjjGgoK8d4ATcrPZ96ZFFn7VGk4`) |
| `crema-finance-2022` | 140,000,000 | Fixture only |