#!/usr/bin/env bash
# Start local x402 → Solana mainnet JSON-RPC proxy for NSS validator replay.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d node_modules ]]; then
  npm install
fi

: "${X402_PROXY_PORT:=18989}"
: "${X402_PROXY_HOST:=127.0.0.1}"
: "${X402_RPC_NETWORK:=solana-mainnet}"
: "${X402_PAYMENT_NETWORK:=solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1}"
: "${X402_PAYMENT_MODEL:=credit-drawdown}"

if [[ -z "${SOLANA_KEYPAIR:-}" && ! -f "${SOLANA_KEYPAIR_FILE:-$HOME/.config/solana/id.json}" ]]; then
  echo "No Solana keypair. Set SOLANA_KEYPAIR_FILE or SOLANA_KEYPAIR (JSON array)." >&2
  echo "Generate: solana-keygen new" >&2
  exit 1
fi

exec node server.mjs