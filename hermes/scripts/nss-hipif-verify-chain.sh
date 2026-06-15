#!/usr/bin/env bash
# Exit 0 only when HIPIF chain has all 13 folds and terminal chain_status.
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

.venv/bin/python -m night_shift_security.cli.main hipif gate