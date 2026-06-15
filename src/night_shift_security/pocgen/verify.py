"""Run generated PoC verifier artifacts and parse impact markers."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from night_shift_security.knowledge.concrete_candidates import load_candidate_records
from night_shift_security.semantic.candidates import ConcreteCandidate


def _load_candidate(candidate_id: str, store_path: Path) -> ConcreteCandidate | None:
    for record in load_candidate_records(store_path):
        if record.get("candidate_id") == candidate_id:
            return ConcreteCandidate.from_dict(record)
    return None


def _parse_markers(text: str) -> dict[str, Any]:
    markers: dict[str, Any] = {}
    for line in text.splitlines():
        if "DELTA_WEI" in line:
            markers["DELTA_WEI"] = line.rsplit(":", 1)[-1].strip()
        if "TOKEN_DELTA" in line:
            markers["TOKEN_DELTA"] = line.rsplit(":", 1)[-1].strip()
        if "MEASURED_DELTA_LAMPORTS" in line:
            markers["MEASURED_DELTA_LAMPORTS"] = line.rsplit(":", 1)[-1].strip()
    return markers


def verify_candidate_poc(
    candidate_id: str,
    *,
    store_path: Path,
    artifact_path: Path | None = None,
    output_dir: Path = Path("data/security_results/poc"),
) -> dict[str, Any]:
    candidate = _load_candidate(candidate_id, store_path)
    if candidate is None:
        return {"status": "missing_candidate", "candidate_id": candidate_id}

    if candidate.chain == "solana":
        python = shutil.which("python") or shutil.which("python3") or ""
        test_path = artifact_path or Path("solana/generated") / candidate.target_slug / f"{candidate_id}_test.py"
        if not python:
            return {"status": "tool_missing", "tool": "python", "candidate_id": candidate_id}
        cmd = [python, "-m", "pytest", str(test_path)]
    else:
        forge = shutil.which("forge") or ""
        test_path = artifact_path or Path("foundry/generated") / candidate.target_slug / f"{candidate_id}.t.sol"
        if not forge:
            return {"status": "tool_missing", "tool": "forge", "candidate_id": candidate_id}
        cmd = [forge, "test", "--match-path", str(test_path)]

    if not test_path.is_file():
        return {"status": "missing_artifact", "candidate_id": candidate_id, "path": str(test_path)}

    proc = subprocess.run(cmd, capture_output=True, text=True)
    markers = _parse_markers(proc.stdout + "\n" + proc.stderr)
    result = {
        "status": "passed" if proc.returncode == 0 else "failed_closed",
        "candidate_id": candidate_id,
        "returncode": proc.returncode,
        "artifact": str(test_path),
        "markers": markers,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{candidate_id}.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    result["result_path"] = str(out)
    return result
