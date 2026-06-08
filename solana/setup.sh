#!/usr/bin/env bash
# Solana harness setup — fixture path (CI) + optional validator tooling check
set -euo pipefail
cd "$(dirname "$0")"

chmod +x run_fixture_test.py run_validator_replay.py run_validator_test.sh 2>/dev/null || true

SOLANA_EXPLOIT_ID=mango-markets-2022 \
SOLANA_TARGET_ID=mango-markets-2022 \
SOLANA_SLOT=152000000 \
SOLANA_FIXTURE_TEST=mango_replay \
python3 run_fixture_test.py >/dev/null || {
  echo "Fixture self-check failed"
  exit 1
}

if command -v solana-test-validator &>/dev/null; then
  echo "Solana harness ready (fixture + solana-test-validator installed)."
else
  echo "Solana harness ready (fixture mode). Install solana-cli for grant-demo validator replay."
fi