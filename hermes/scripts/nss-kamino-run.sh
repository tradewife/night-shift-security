#!/usr/bin/env bash
# Kamino shoestring pipeline — requires hermes_proposals/latest.json when using external expansion.
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

CONFIG="src/night_shift_security/config/kamino_shoestring.json"
PROPOSALS="data/security_results/hermes_proposals/latest.json"

ARGS=(--config "$CONFIG")
if [ -f "$PROPOSALS" ]; then
  ARGS+=(--proposals "$PROPOSALS")
fi

.venv/bin/python -m night_shift_security.cli.main "${ARGS[@]}" run