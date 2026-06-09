"""Protocol recon loader — minimal invariant/threat-model slice (METHODOLOGY Recon phase)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RECON_ROOT = Path(__file__).resolve().parents[3] / "sources"


def recon_path_for_target(target_id: str) -> Path:
    return _RECON_ROOT / target_id / "recon.json"


def load_recon(target_id: str) -> dict[str, Any] | None:
    """Load recon.json for a target if present under sources/<target_id>/."""
    path = recon_path_for_target(target_id)
    if not path.is_file():
        return None
    with open(path) as handle:
        return json.load(handle)


def merge_recon_into_target_config(section: dict[str, Any]) -> dict[str, Any]:
    """Merge recon invariants and state hints into a live-target config dict."""
    target_id = str(section.get("target_id", ""))
    recon = load_recon(target_id)
    if recon is None:
        return section

    merged = dict(section)
    overrides = dict(merged.get("state_overrides", {}))
    hints = recon.get("state_hints", {})
    for key, value in hints.items():
        overrides.setdefault(key, value)

    metadata = dict(overrides.get("metadata", {}))
    metadata.setdefault("recon_version", recon.get("recon_version", "1.0"))
    metadata.setdefault("catalog_analogue", recon.get("catalog_analogue", ""))
    metadata["recon_invariants"] = [inv["id"] for inv in recon.get("invariants", [])]
    metadata["threat_model"] = recon.get("threat_model", {})
    metadata["programs"] = recon.get("programs", metadata.get("programs", {}))
    overrides["metadata"] = metadata
    merged["state_overrides"] = overrides

    if not merged.get("exploit_id") and recon.get("catalog_analogue"):
        merged.setdefault("exploit_id", recon["catalog_analogue"])

    return merged