#!/usr/bin/env bash
set -euo pipefail

FORK_URL="${ETHEREUM_RPC_URL:?ETHEREUM_RPC_URL required}"
FORK_BLOCK="${FORK_BLOCK:-16825925}"
PORT="${ANVIL_PORT:-8545}"
ATTACKER="${OPERATOR_ATTACKER:-0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266}"
BALANCE_ETH="${ATTACKER_BALANCE_ETH:-1000000}"

anvil \
  --fork-url "$FORK_URL" \
  --fork-block-number "$FORK_BLOCK" \
  --host 0.0.0.0 \
  --port "$PORT" &

ANVIL_PID=$!
sleep 3

RPC="http://127.0.0.1:${PORT}"
WEI="$(cast --to-wei "$BALANCE_ETH" ether)"
cast rpc anvil_setBalance "$ATTACKER" "$WEI" --rpc-url "$RPC"

echo "ANVIL_RPC:${RPC}"
echo "FORK_BLOCK:${FORK_BLOCK}"
echo "ATTACKER:${ATTACKER}"
echo "ATTACKER_BALANCE_ETH:${BALANCE_ETH}"

wait "$ANVIL_PID"