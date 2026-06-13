#!/usr/bin/env bash
# HIPIF chain bootstrap — env + folded context init; agent executes subgoal chain via hipif skill.
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

git pull --ff-only 2>/dev/null || true

# Full chain runs all depth passes nightly — no day-of-week pin
unset NSS_LOOP_DEPTH_SLUG

MONTH="$(date -u +%Y-%m)"
echo "NSS HIPIF chain bootstrap $(date -Iseconds)"

.venv/bin/python -m night_shift_security.cli.main hipif init \
  --task "Night chain SPEC v3.1.0 (${MONTH})"

.venv/bin/python -m night_shift_security.cli.main hipif read

if [[ "${NSS_HIPIF_MODE:-}" == "deterministic" ]]; then
  echo "NSS HIPIF deterministic chain (no-agent)"
  exec .venv/bin/python hermes/scripts/nss-hipif-chain-run.py
fi

echo "HIPIF_CHAIN_READY: execute hipif skill subgoal chain through gate; hard stop on submit_ready"
echo "Deterministic fallback: NSS_HIPIF_MODE=deterministic $0"
echo "Or: .venv/bin/python hermes/scripts/nss-hipif-chain-run.py"