#!/usr/bin/env bash
# NSS health watchdog — silent when green, stderr on failure.
# Register: hermes cron create "every 6h" --no-agent --script nss-health.sh --name nss-health --profile night-shift --deliver local
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

if [ ! -d .venv ]; then
  echo "NSS health FAIL: .venv missing at $REPO" >&2
  exit 1
fi

.venv/bin/python -m pytest -q --tb=no 2>&1 || {
  echo "NSS health FAIL: pytest failed" >&2
  exit 1
}

# Silent success (no-agent cron: empty stdout = no delivery)
exit 0