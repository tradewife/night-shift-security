"""Slither static analysis adapters — scoped to triage-ranked files."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_DETECTORS: tuple[str, ...] = (
    "arbitrary-send-eth",
    "incorrect-equality",
    "uninitialized-state",
    "reentrancy-eth",
    "suicidal",
)

_LOGIC_DETECTORS: tuple[str, ...] = (
    "arbitrary-send-eth",
    "incorrect-equality",
    "uninitialized-state",
    "reentrancy-eth",
)


@dataclass
class SlitherFinding:
    check: str
    impact: str
    confidence: str
    description: str
    filename: str
    function: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def slither_available() -> bool:
    return shutil.which("slither") is not None


def run_slither_on_files(
    files: list[str],
    *,
    project_root: Path,
    detectors: list[str] | None = None,
    timeout_s: int = 300,
) -> dict[str, Any]:
    """
    Run Slither on ranked files within project_root.

    Uses --filter-paths when possible; falls back to per-file invocation.
    """
    if not slither_available():
        return {
            "success": False,
            "error": "slither not found on PATH — install: pip install slither-analyzer",
            "findings": [],
        }

    det = detectors or list(_LOGIC_DETECTORS)
    det_arg = ",".join(det)
    root = project_root.resolve()
    existing = [f for f in files if (root / f).is_file()]
    if not existing:
        return {
            "success": False,
            "error": "no existing files in ranked list",
            "findings": [],
            "requested": files,
        }

    filter_paths = ",".join(existing)
    cmd = [
        "slither",
        str(root),
        "--filter-paths",
        filter_paths,
        "--detect",
        det_arg,
        "--json",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"success": False, "error": str(exc), "findings": []}

    findings: list[dict[str, Any]] = []
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
            detectors_out = payload.get("results", {}).get("detectors", [])
            for item in detectors_out:
                elements = item.get("elements") or []
                filename = elements[0].get("source_mapping", {}).get("filename_short", "") if elements else ""
                findings.append(
                    SlitherFinding(
                        check=item.get("check", ""),
                        impact=item.get("impact", ""),
                        confidence=item.get("confidence", ""),
                        description=item.get("description", ""),
                        filename=filename,
                        function=elements[0].get("name", "") if elements else "",
                    ).to_dict()
                )
        except json.JSONDecodeError:
            findings.append({"raw_stdout": proc.stdout[:2000]})

    return {
        "success": proc.returncode == 0 or bool(findings),
        "exit_code": proc.returncode,
        "command": cmd,
        "stderr": proc.stderr[-1000:] if proc.stderr else "",
        "findings": findings,
        "files_scanned": existing,
        "detectors": det,
    }


def load_ranked_files_from_triage(triage_path: Path, *, min_score: int = 4) -> list[str]:
    if not triage_path.is_file():
        return []
    data = json.loads(triage_path.read_text())
    return [f["path"] for f in data.get("files", []) if int(f.get("score", 0)) >= min_score]