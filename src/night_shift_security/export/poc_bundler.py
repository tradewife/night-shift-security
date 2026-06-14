"""Bundle runnable PoC scripts from fork targets and Solana harness paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from night_shift_security.data.fork_targets import ForkTarget, get_fork_targets
from night_shift_security.data.schemas import Finding
from night_shift_security.export.finding_resolve import resolve_exploit_id


def _fork_target_for_finding(finding: Finding) -> ForkTarget | None:
    exploit_id = resolve_exploit_id(finding)
    candidates = [exploit_id, finding.target_id or ""]
    fork_ev = finding.fork_evidence or {}
    if fork_ev.get("target_id"):
        candidates.append(str(fork_ev["target_id"]))
    if fork_ev.get("fork_test"):
        test_name = str(fork_ev["fork_test"])
        for target in get_fork_targets():
            if target.fork_test == test_name:
                return target
    for raw in candidates:
        if not raw:
            continue
        for target in get_fork_targets():
            if target.exploit_id == raw or target.target_id == raw:
                return target
    return None


def bundle_evm_repro_script(
    finding: Finding,
    *,
    run_meta: dict[str, Any] | None = None,
) -> str:
    """Emit a bash wrapper that runs the real Foundry fork test for this finding."""
    run_meta = run_meta or {}
    target = _fork_target_for_finding(finding)
    fork_ev = finding.fork_evidence or {}
    fork_test = (
        str(fork_ev.get("fork_test") or "")
        or (target.fork_test if target else "")
        or "testForkEulerHistoricalBlock"
    )
    rpc_env = (target.rpc_env_var if target else "ETHEREUM_RPC_URL")
    rpc_url = run_meta.get("ethereum_rpc_url") or f"${{{rpc_env}}}"
    block = fork_ev.get("block_number") or (target.block_number if target else 0)
    block_flag = f"--fork-block-number {block}" if block else ""
    block_echo = f" {block_flag}" if block_flag else ""

    return f"""#!/usr/bin/env bash
# Runnable EVM fork PoC — {finding.finding_id}
# Target: {finding.target_id or (target.target_id if target else "unknown")}
# Fork test: {fork_test}

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$ROOT/foundry/foundry.toml" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/foundry/foundry.toml" ]; then
  echo "Could not locate foundry/ (foundry.toml)" >&2
  exit 1
fi
cd "$ROOT/foundry"

export {rpc_env}="${{{rpc_env}:-{rpc_url}}}"
echo "==> forge test --match-test {fork_test}{block_echo}"
forge test --match-test {fork_test} -vv {block_flag}

echo "==> PASS: fork PoC executed (expect DELTA_WEI or IMPACT_USD in output for submittable)"
"""


def bundle_solana_repro_script(
    finding: Finding,
    *,
    run_meta: dict[str, Any] | None = None,
) -> str:
    """Emit a bash wrapper for KLend/validator harness replay."""
    run_meta = run_meta or {}
    exploit = resolve_exploit_id(finding) or "TARGET_EXPLOIT_ID"
    probe = (finding.solana_evidence or {}).get("probe") or (finding.parameters or {}).get("klend_probe", "")
    probe_export = f'export KLEND_PROBE="{probe}"\n' if probe else ""
    rpc_url = run_meta.get("solana_mainnet_rpc_url", "http://127.0.0.1:18989")

    if probe or finding.target_id == "kamino":
        return f"""#!/usr/bin/env bash
# Solana KLend live probe reproduction — {finding.finding_id}

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$ROOT/solana/run_klend_harness.py" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/solana/run_klend_harness.py" ]; then
  echo "Could not locate solana/run_klend_harness.py" >&2
  exit 1
fi
cd "$ROOT"

export NSS_KLEND_FIXTURE=0
export NSS_KLEND_DEPTH=1
export SOLANA_MAINNET_RPC_URL="${{SOLANA_MAINNET_RPC_URL:-{rpc_url}}}"
{probe_export}
echo "==> KLend live harness"
python3 solana/run_klend_harness.py
"""

    slot = finding.solana_slot or (finding.solana_evidence or {}).get("slot", 0)
    return f"""#!/usr/bin/env bash
# Solana validator reproduction — {finding.finding_id}
# Exploit anchor: {exploit}

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
while [ ! -f "$ROOT/solana/run_validator_test.sh" ] && [ "$ROOT" != "/" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/solana/run_validator_test.sh" ]; then
  echo "Could not locate solana/run_validator_test.sh" >&2
  exit 1
fi
cd "$ROOT/solana"

export SOLANA_EXPLOIT_ID="{exploit}"
export SOLANA_USE_VALIDATOR=1
export SOLANA_MAINNET_RPC_URL="${{SOLANA_MAINNET_RPC_URL:-{rpc_url}}}"
export SOLANA_SLOT="{slot}"
./run_validator_test.sh
"""


def bundle_reproduction_script(
    finding: Finding,
    *,
    language: str | None = None,
    run_meta: dict[str, Any] | None = None,
) -> str:
    """Prefer runnable fork/validator scripts over TODO Solidity stubs."""
    if language == "solana" or finding.solana_reproduced or finding.solana_confirmed:
        return bundle_solana_repro_script(finding, run_meta=run_meta)
    if finding.fork_reproduced or (finding.fork_evidence or {}).get("fork_test"):
        return bundle_evm_repro_script(finding, run_meta=run_meta)
    method = (finding.solana_evidence or {}).get("method", "")
    if method in ("solana_fixture", "solana_validator"):
        return bundle_solana_repro_script(finding, run_meta=run_meta)
    return bundle_evm_repro_script(finding, run_meta=run_meta)


def poc_metadata(finding: Finding) -> dict[str, Any]:
    target = _fork_target_for_finding(finding)
    fork_ev = finding.fork_evidence or {}
    return {
        "finding_id": finding.finding_id,
        "fork_test": fork_ev.get("fork_test") or (target.fork_test if target else None),
        "target_id": target.target_id if target else finding.target_id,
        "runnable": bool(
            finding.fork_reproduced
            or finding.solana_reproduced
            or fork_ev.get("fork_test")
            or target
        ),
    }