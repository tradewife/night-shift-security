#!/usr/bin/env bash
# Autonomous Immunefi + Cantina bounty loop (scan → investigate → qualify).
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

git pull --ff-only 2>/dev/null || true

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

.venv/bin/python -m night_shift_security.cli.main bounty loop "$@"