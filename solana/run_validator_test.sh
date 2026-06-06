#!/usr/bin/env bash
# Grant-demo path: solana-test-validator with mainnet clones (Slice 2+ tightening).
# Slice 1 falls back to fixture runner when clone replay is not configured.
set -euo pipefail
cd "$(dirname "$0")"

EXPLOIT_ID="${SOLANA_EXPLOIT_ID:-}"
if [[ -z "$EXPLOIT_ID" ]]; then
  echo "SOLANA_EXPLOIT_ID required" >&2
  exit 2
fi

if [[ -z "${SOLANA_MAINNET_RPC_URL:-}" ]]; then
  echo "SOLANA_MAINNET_RPC_URL not set; falling back to fixture replay" >&2
  exec python3 run_fixture_test.py
fi

echo "solana-test-validator grant-demo mode: clone replay not yet wired for ${EXPLOIT_ID}"
echo "Falling back to fixture strict path for Slice 1"
exec python3 run_fixture_test.py