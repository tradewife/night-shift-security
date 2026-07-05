#!/bin/bash
# Run Symbiotic invariant tests and log results
# Usage: ./run_invariant_tests.sh [runs] [depth]

set -euo pipefail

REPO_DIR="/home/kt/projects/rtp/night-shift-security/sources/symbiotic/repo"
INVESTIGATION_DIR="/home/kt/projects/rtp/night-shift-security/data/security_results/investigations/2026-07-05-symbiotic-cantina"
RUNS="${1:-100}"
DEPTH="${2:-500}"

cd "$REPO_DIR"

echo "=== Running SymbioticCoreInvariants (${RUNS}runs x ${DEPTH}depth) ==="
FOUNDRY_INVARIANT_RUNS="$RUNS" FOUNDRY_INVARIANT_DEPTH="$DEPTH" \
  forge test --match-contract SymbioticCoreInvariants -vvv 2>&1 | \
  tee /tmp/symbiotic-invariant-run.txt

# Extract results
PASSED=$(grep -c "\[PASS\]" /tmp/symbiotic-invariant-run.txt || echo 0)
FAILED=$(grep -c "\[FAIL\]" /tmp/symbiotic-invariant-run.txt || echo 0)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "{\"run_id\":\"$(date -u +%Y-%m-%d-%H%M%S)\",\"timestamp\":\"$TIMESTAMP\",\"type\":\"invariant\",\"runs\":$RUNS,\"depth\":$DEPTH,\"passed\":$PASSED,\"failed\":$FAILED}" \
  >> "$INVESTIGATION_DIR/runs.jsonl"

echo "=== Results: ${PASSED} passed, ${FAILED} failed ==="
exit $FAILED
