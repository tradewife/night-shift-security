#!/usr/bin/env bash
# Deterministic Kamino coordinator cycle — plan + parametric pipeline + status.
set -euo pipefail
cd /home/kt/projects/rtp/night-shift-security

CONFIG=src/night_shift_security/config/kamino_shoestring.json
PY=".venv/bin/python -m night_shift_security.cli.main"

if [[ ! -f data/security_results/knowledge/coordinator_state.json ]]; then
  $PY --config "$CONFIG" coordinator init
fi

echo "=== coordinator plan (top 1) ==="
$PY --config "$CONFIG" coordinator plan --top 1

echo "=== coordinator cycle (parametric) ==="
$PY --config "$CONFIG" coordinator cycle

echo "=== coordinator status ==="
$PY coordinator status