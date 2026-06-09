#!/usr/bin/env bash
# Immunefi scan wrapper (no LLM, zero RPC).
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

.venv/bin/python -m night_shift_security.cli.main scan --ecosystem solana "$@"