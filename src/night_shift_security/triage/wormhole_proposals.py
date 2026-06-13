"""Scoped Hermes proposals from Wormhole triage-ranked files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.domain.attack_hypotheses.base import AttackHypothesis, validate_hypothesis

_SURFACE_VARIANTS: dict[str, list[dict[str, Any]]] = {
    "bridge": [
        {
            "template": "access_control_escalation",
            "parameters": {
                "privilege_escalation_pressure": 0.92,
                "role_bypass_severity": 0.88,
                "zero_root_exploitability": 0.82,
                "target_role_preference": "owner",
            },
        },
        {
            "template": "composability_risk",
            "parameters": {
                "chain_depth": 0.95,
                "leverage_intensity": 0.8,
                "callback_chain_likelihood": 0.9,
            },
        },
    ],
    "token_bridge": [
        {
            "template": "access_control_escalation",
            "parameters": {
                "privilege_escalation_pressure": 0.78,
                "role_bypass_severity": 0.7,
                "zero_root_exploitability": 0.65,
                "target_role_preference": "admin",
            },
        },
        {
            "template": "composability_risk",
            "parameters": {
                "chain_depth": 0.85,
                "leverage_intensity": 0.72,
                "callback_chain_likelihood": 0.88,
            },
        },
    ],
    "cpi": [
        {
            "template": "composability_risk",
            "parameters": {
                "chain_depth": 0.9,
                "leverage_intensity": 0.78,
                "callback_chain_likelihood": 0.92,
            },
        },
    ],
    "default": [
        {
            "template": "access_control_escalation",
            "parameters": {
                "privilege_escalation_pressure": 0.55,
                "role_bypass_severity": 0.5,
                "zero_root_exploitability": 0.45,
                "target_role_preference": "owner",
            },
        },
    ],
}


def _surface_bucket(path: str) -> str:
    lowered = path.lower()
    if "token_bridge" in lowered or "tokenbridge" in lowered:
        return "token_bridge"
    if "bridge" in lowered or "portal" in lowered or "messaging" in lowered:
        return "bridge"
    if "cpi" in lowered or "solitaire" in lowered:
        return "cpi"
    return "default"


def build_wormhole_triage_proposals(
    triage_path: Path,
    *,
    min_score: int = 5,
    max_files: int = 8,
) -> list[dict[str, Any]]:
    payload = json.loads(triage_path.read_text())
    files = [f for f in payload.get("files", []) if int(f.get("score", 0)) >= min_score]
    files.sort(key=lambda f: (-int(f.get("score", 0)), f.get("path", "")))
    selected = files[:max_files]

    proposals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for ranked in selected:
        path = str(ranked.get("path", ""))
        bucket = _surface_bucket(path)
        for variant in _SURFACE_VARIANTS.get(bucket, _SURFACE_VARIANTS["default"]):
            key = (variant["template"], path)
            if key in seen:
                continue
            seen.add(key)
            hypothesis = AttackHypothesis(
                hypothesis_id="probe",
                template=variant["template"],
                parameters=dict(variant["parameters"]),
                metadata={},
            )
            valid, reason = validate_hypothesis(hypothesis)
            if not valid:
                continue
            proposals.append(
                {
                    "template": variant["template"],
                    "parameters": variant["parameters"],
                    "ranked_file": path,
                    "surface_bucket": bucket,
                    "delegate_note": (
                        f"wormhole triage score={ranked.get('score')} "
                        f"signals={','.join(ranked.get('signals', []))}"
                    ),
                }
            )
    return proposals


def write_wormhole_triage_proposals(
    triage_path: Path,
    output_dir: Path,
    *,
    min_score: int = 5,
    max_files: int = 8,
    campaign_id: str = "immunefi-wormhole-2026-06",
) -> Path:
    proposals = build_wormhole_triage_proposals(
        triage_path,
        min_score=min_score,
        max_files=max_files,
    )
    run_id = f"wormhole-triage-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    doc = {
        "run_id": run_id,
        "campaign_id": campaign_id,
        "target_slug": "wormhole",
        "catalog_analogue": "nomad-bridge-2022",
        "triage_source": str(triage_path),
        "proposals": proposals,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    latest = output_dir / "latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_path.name)
    return out_path