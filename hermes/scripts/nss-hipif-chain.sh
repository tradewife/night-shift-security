#!/usr/bin/env bash
# HIPIF chain bootstrap — env + folded context init; hybrid hands bulk depth to Python then agent.
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

unset NSS_LOOP_DEPTH_SLUG

MONTH="$(date -u +%Y-%m)"
export NSS_HIPIF_BOUNTY_DEPTH="${NSS_HIPIF_BOUNTY_DEPTH:-1}"
export NSS_KLEND_FIXTURE="${NSS_KLEND_FIXTURE:-0}"
export NSS_HIPIF_MODE="${NSS_HIPIF_MODE:-hybrid}"
# Deterministic bulk takes 60–150+ min; Hermes default script timeout is 120s.
export HERMES_CRON_SCRIPT_TIMEOUT="${HERMES_CRON_SCRIPT_TIMEOUT:-10800}"
echo "NSS HIPIF chain bootstrap $(date -Iseconds) bounty_depth=${NSS_HIPIF_BOUNTY_DEPTH} mode=${NSS_HIPIF_MODE} script_timeout=${HERMES_CRON_SCRIPT_TIMEOUT}"

.venv/bin/python -m night_shift_security.cli.main hipif init \
  --task "Bounty-depth chain SPEC v3.3.0 (${MONTH})"

.venv/bin/python -m night_shift_security.cli.main hipif read

if [[ "${NSS_HIPIF_MODE}" == "deterministic" ]]; then
  echo "NSS HIPIF deterministic full chain (no-agent)"
  exec .venv/bin/python hermes/scripts/nss-hipif-chain-run.py --phase full
fi

if [[ "${NSS_HIPIF_MODE}" == "hybrid" ]]; then
  echo "NSS HIPIF hybrid: deterministic bulk depth phase"
  .venv/bin/python hermes/scripts/nss-hipif-chain-run.py --phase deterministic
  echo ""
  .venv/bin/python -m night_shift_security.cli.main hipif status
  echo ""
  echo "HIPIF_HYBRID_AGENT_PHASE: Complete remaining subgoals from current_subgoal through gate."
  echo "Agent subgoals (delegate_task required): depth_wormhole_bridge, refine_conditional, coordinator_conditional"
  echo "Then journal_fold (lab-notebook) and gate."
  echo "MANDATORY FINAL COMMAND (exit 1 if incomplete): .venv/bin/python -m night_shift_security.cli.main hipif gate"
  echo "Do NOT end your turn until hipif gate exits 0. Short text-only responses are forbidden."
  echo '{"wakeAgent": true}'
  exit 0
fi

if [[ "${NSS_HIPIF_MODE}" == "agent" ]]; then
  echo "HIPIF_AGENT_ONLY: continue from folded_context current_subgoal"
  echo '{"wakeAgent": true}'
  exit 0
fi

echo "HIPIF_CHAIN_READY: execute hipif skill subgoal chain through gate; hard stop on submit_ready"
echo "Modes: NSS_HIPIF_MODE=hybrid|deterministic|agent"
echo "Deterministic fallback: NSS_HIPIF_MODE=deterministic $0"
echo "Or: .venv/bin/python hermes/scripts/nss-hipif-chain-run.py --phase full"