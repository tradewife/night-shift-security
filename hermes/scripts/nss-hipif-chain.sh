#!/usr/bin/env bash
# HIPIF chain bootstrap — env + folded context init; default cron mode runs the full deterministic v4.2 chain.
#
# v5 pivot: production cron pauses until at least one NativeHarness target has
# status=ready (set NSS_HIPIF_PAUSE_FOR_NATIVE=0 to revert to legacy v4.2 chain).
set -euo pipefail

REPO="${NSS_REPO:-/home/kt/projects/rtp/night-shift-security}"
cd "$REPO"

export PATH="$HOME/.local/share/solana/install/active_release/bin:$HOME/.cargo/bin:$PATH"
if [[ -z "${SOLANA_VALIDATOR_BIN:-}" ]]; then
  for candidate in \
    "$HOME/.local/share/solana/install/active_release/bin/solana-test-validator" \
    "$HOME/.cargo/bin/solana-test-validator" \
    /usr/local/bin/solana-test-validator \
    /usr/bin/solana-test-validator; do
    if [[ -x "$candidate" ]]; then
      export SOLANA_VALIDATOR_BIN="$candidate"
      break
    fi
  done
fi

_PRE_HIPIF_MODE="${NSS_HIPIF_MODE:-}"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
if [[ -n "${_PRE_HIPIF_MODE}" ]]; then
  export NSS_HIPIF_MODE="${_PRE_HIPIF_MODE}"
fi

git pull --ff-only 2>/dev/null || true

unset NSS_LOOP_DEPTH_SLUG

MONTH="$(date -u +%Y-%m)"
export NSS_HIPIF_BOUNTY_DEPTH="${NSS_HIPIF_BOUNTY_DEPTH:-1}"
export NSS_KLEND_FIXTURE="${NSS_KLEND_FIXTURE:-0}"
export NSS_HIPIF_MODE="${NSS_HIPIF_MODE:-deterministic}"
export NSS_HIPIF_PAUSE_FOR_NATIVE="${NSS_HIPIF_PAUSE_FOR_NATIVE:-1}"

# v5 substrate precondition: refuse to run the legacy v4.2 chain unless at
# least one native harness is ready. The legacy chain kept producing
# catalogue-only / triage-only findings (see SYSTEM_AUDIT_2026-06-18.md).
if [[ "${NSS_HIPIF_PAUSE_FOR_NATIVE}" == "1" ]]; then
  HARNESS_MANIFEST="$REPO/data/security_results/loop/native_harness_status.json"
  if ! python3 - "$HARNESS_MANIFEST" <<'PY' 2>/dev/null; then
import json, sys
p = sys.argv[1]
try:
    with open(p) as fh:
        data = json.load(fh)
except FileNotFoundError:
    sys.exit(1)  # No manifest yet — pause.
except (OSError, ValueError):
    sys.exit(1)
if not any(entry.get("status") == "ready" for entry in (data.get("harnesses") or {}).values()):
    sys.exit(1)
PY
    echo "NSS_HIPIF_PAUSE_FOR_NATIVE=1 and no native harness ready (${HARNESS_MANIFEST} missing or empty)."
    echo "Pausing cron until at least one NativeHarness target reaches status=ready."
    echo "Set NSS_HIPIF_PAUSE_FOR_NATIVE=0 to revert to legacy v4.2 chain."
    mkdir -p "$(dirname "$HARNESS_MANIFEST")"
    echo "{\"generated_at\": \"$(date -u --iso-8601=seconds)\", \"reason\": \"paused_awaiting_native_harness\", \"action\": \"no_run\"}" \
      > "$HARNESS_MANIFEST"
    exit 0
  fi
fi

# Full bounty-depth chain takes 60–150+ min; Hermes default script timeout is 120s.
export HERMES_CRON_SCRIPT_TIMEOUT="${HERMES_CRON_SCRIPT_TIMEOUT:-10800}"
echo "NSS HIPIF chain bootstrap $(date -Iseconds) bounty_depth=${NSS_HIPIF_BOUNTY_DEPTH} mode=${NSS_HIPIF_MODE} pause_for_native=${NSS_HIPIF_PAUSE_FOR_NATIVE} script_timeout=${HERMES_CRON_SCRIPT_TIMEOUT}"

.venv/bin/python -m night_shift_security.cli.main hipif init \
  --task "Bounty-depth chain SPEC v5.0.0-draft (${MONTH})"

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
  echo "HIPIF_HYBRID_DEGRADED: deterministic bulk finished, but agent/gate phase is not complete yet" >&2
  exit 1
fi

if [[ "${NSS_HIPIF_MODE}" == "agent" ]]; then
  echo "HIPIF_AGENT_ONLY: continue from folded_context current_subgoal"
  echo '{"wakeAgent": true}'
  .venv/bin/python -m night_shift_security.cli.main hipif gate
  exit $?
fi

echo "HIPIF_CHAIN_READY: execute hipif skill subgoal chain through gate; hard stop on submit_ready"
echo "Modes: NSS_HIPIF_MODE=hybrid|deterministic|agent"
echo "Default no-agent cron mode: NSS_HIPIF_MODE=deterministic $0"
echo "Or: .venv/bin/python hermes/scripts/nss-hipif-chain-run.py --phase full"
