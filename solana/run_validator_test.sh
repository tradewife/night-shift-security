#!/usr/bin/env bash
# Slice 2: real solana-test-validator clone replay for validator-backed exploits.
# Exits non-zero on failure — never emits fixture impact lines (strict path only).
set -euo pipefail
cd "$(dirname "$0")"

EXPLOIT_ID="${SOLANA_EXPLOIT_ID:-}"
if [[ -z "$EXPLOIT_ID" ]]; then
  echo "SOLANA_EXPLOIT_ID required" >&2
  exit 2
fi

if [[ -z "${SOLANA_MAINNET_RPC_URL:-}" ]]; then
  echo "SOLANA_MAINNET_RPC_URL required for validator replay" >&2
  exit 2
fi

exec python3 run_validator_replay.py