"""Opengrep/Semgrep SARIF ingestion for concrete candidate seeds."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.knowledge.concrete_candidates import upsert_candidates
from night_shift_security.semantic.candidates import (
    ConcreteCandidate,
    candidate_from_entrypoint,
    write_candidates_jsonl,
)

DEFAULT_TOOL_FINDINGS = Path("data/security_results/knowledge/tool_findings.jsonl")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_sarif(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"SARIF file not found: {path}")
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("SARIF root must be a JSON object")
    return payload


def sarif_results(sarif: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for run in sarif.get("runs") or []:
        if not isinstance(run, dict):
            continue
        tool_name = ((run.get("tool") or {}).get("driver") or {}).get("name") or "opengrep"
        rules = {
            str(rule.get("id") or ""): rule
            for rule in (((run.get("tool") or {}).get("driver") or {}).get("rules") or [])
            if isinstance(rule, dict)
        }
        for result in run.get("results") or []:
            if not isinstance(result, dict):
                continue
            rule_id = str(result.get("ruleId") or "")
            loc = {}
            locations = result.get("locations") if isinstance(result.get("locations"), list) else []
            if locations and isinstance(locations[0], dict):
                loc = locations[0].get("physicalLocation") or {}
            region = loc.get("region") or {}
            artifact = loc.get("artifactLocation") or {}
            out.append(
                {
                    "tool_name": tool_name,
                    "rule_id": rule_id,
                    "rule_name": (rules.get(rule_id) or {}).get("name") or rule_id,
                    "message": (result.get("message") or {}).get("text") or "",
                    "file": artifact.get("uri") or "",
                    "line": int(region.get("startLine") or 1),
                    "level": result.get("level") or "",
                    "trusted": False,
                }
            )
    return out


def _nearest_entrypoint(finding: dict[str, Any], semantic_map: dict[str, Any]) -> dict[str, Any]:
    file = str(finding.get("file") or "")
    line = int(finding.get("line") or 1)
    entries = [
        e for e in (semantic_map.get("entrypoints") or []) if str(e.get("file") or "").endswith(file)
    ]
    if entries:
        before = [e for e in entries if int(e.get("line") or 0) <= line]
        return sorted(before or entries, key=lambda e: abs(int(e.get("line") or 0) - line))[0]
    return {
        "kind": "static_finding",
        "name": str(finding.get("rule_id") or "opengrep_finding"),
        "selector_or_discriminator": "",
        "file": file,
        "line": line,
        "source_ref": {
            "repo": semantic_map.get("repo") or "",
            "file": file,
            "symbol": str(finding.get("rule_id") or ""),
        },
        "signals": {},
    }


def findings_to_candidates(
    findings: list[dict[str, Any]],
    semantic_map: dict[str, Any],
    *,
    slug: str,
) -> list[ConcreteCandidate]:
    candidates: list[ConcreteCandidate] = []
    seen: set[str] = set()
    for finding in findings:
        entry = _nearest_entrypoint(finding, semantic_map)
        candidate = candidate_from_entrypoint(
            entry,
            target_slug=slug,
            campaign_id=f"opengrep-{slug}",
            provenance_source="opengrep",
        )
        candidate.provenance.update(
            {
                "tool_name": finding.get("tool_name") or "opengrep",
                "rule_id": finding.get("rule_id") or "",
                "trusted": False,
                "evidence": [finding],
            }
        )
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        candidates.append(candidate)
    return candidates


def append_tool_findings(findings: list[dict[str, Any]], path: Path = DEFAULT_TOOL_FINDINGS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for finding in findings:
            payload = dict(finding)
            payload.setdefault("generated_at", _utc_now())
            fh.write(json.dumps(payload, sort_keys=True) + "\n")
    return path


def run_opengrep(
    *,
    slug: str,
    repo: Path,
    out_dir: Path,
    rules_dir: Path,
    semantic_map_path: Path | None = None,
    store_path: Path | None = None,
    tool: str | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sarif_path = out_dir / "opengrep.sarif"
    candidates_path = out_dir / "opengrep_candidates.jsonl"
    binary = tool or shutil.which("opengrep") or shutil.which("semgrep") or ""
    if not binary:
        result = {
            "status": "tool_missing",
            "tool": "opengrep",
            "message": "Install opengrep or semgrep to run static rules",
            "sarif": str(sarif_path),
            "candidate_count": 0,
        }
        return result

    cmd = [binary, "--sarif", "--config", str(rules_dir), str(repo)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        sarif_path.write_text(proc.stdout)
    if proc.returncode not in (0, 1):
        return {
            "status": "failed",
            "tool": binary,
            "returncode": proc.returncode,
            "stderr": proc.stderr[-2000:],
            "sarif": str(sarif_path),
            "candidate_count": 0,
        }

    findings = sarif_results(load_sarif(sarif_path)) if sarif_path.is_file() else []
    append_tool_findings(findings)
    candidates: list[ConcreteCandidate] = []
    if semantic_map_path and semantic_map_path.is_file():
        semantic_map = json.loads(semantic_map_path.read_text())
        candidates = findings_to_candidates(findings, semantic_map, slug=slug)
        write_candidates_jsonl(candidates, candidates_path)
        if store_path is not None:
            upsert_candidates(candidates, store_path)
    return {
        "status": "ok",
        "tool": binary,
        "returncode": proc.returncode,
        "sarif": str(sarif_path),
        "findings": len(findings),
        "candidate_count": len(candidates),
        "candidates": str(candidates_path),
    }
