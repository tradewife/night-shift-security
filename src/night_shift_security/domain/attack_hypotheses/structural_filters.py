"""Early structural filters — discard low-quality hypotheses before simulation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses.ranking import attach_ranking_signals

STRUCTURAL_FILTER_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "dedupe": True,
    "feasibility_checks": True,
    "min_priority_score": 0.05,
    "auditvault_axes": {
        "enabled": False,
        "required_min_count": 1,
        "priority_bump_per_ref": 0.02,
        "path": "data/security_results/knowledge/auditvault_patterns.jsonl",
    },
}

_BYPASS_GENERATION_METHODS = frozenset({"catalog_seed", "ground_truth"})


@dataclass
class FilterStats:
    input_count: int = 0
    output_count: int = 0
    dropped: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    def record_drop(self, reason: str) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "dropped": self.dropped,
            "reasons": dict(self.reasons),
        }


def _feasibility_check(template_id: str, parameters: dict[str, Any]) -> tuple[bool, str]:
    """Template-specific structural impossibilities on execution parameters."""
    if template_id == "governance_capture":
        if float(parameters.get("voting_power_pct", 0.0)) < 10.0:
            return False, "voting_power_pct below minimum plausible threshold"
    elif template_id == "treasury_drain":
        if float(parameters.get("withdrawal_pct", 0.0)) < 20.0:
            return False, "withdrawal_pct too low for treasury drain"
    elif template_id == "flash_loan_oracle":
        if float(parameters.get("loan_amount_usd", 0.0)) < 100_000.0:
            return False, "loan_amount_usd too small for oracle manipulation"
    elif template_id == "reentrancy":
        if int(parameters.get("recursion_depth", 0)) < 2:
            return False, "recursion_depth too shallow"
    elif template_id == "composability_risk":
        if int(parameters.get("protocol_hops", 0)) < 2:
            return False, "protocol_hops too shallow for composability chain"
    elif template_id == "upgradeability_risk":
        if not parameters.get("upgrade_method"):
            return False, "upgrade_method required"
    elif template_id == "access_control_escalation":
        if not parameters.get("target_role"):
            return False, "target_role required"
    return True, ""


def vector_fingerprint(vector: AttackVector) -> tuple[Any, ...]:
    """Stable deduplication key for template execution parameters."""
    normalized: list[tuple[str, Any]] = []
    for key, value in sorted(vector.parameters.items()):
        if isinstance(value, float):
            normalized.append((key, round(value, 4)))
        elif isinstance(value, bool):
            normalized.append((key, value))
        else:
            normalized.append((key, value))
    return (vector.template_id, vector.target_id, tuple(normalized))


def should_bypass_priority_floor(vector: AttackVector) -> bool:
    """Catalog seeds and ground-truth vectors skip the priority floor."""
    metadata = vector.metadata or {}
    if metadata.get("bypass_structural_filters"):
        return True
    if vector.label.startswith("catalog_seed_"):
        return True
    if metadata.get("generation_method") in _BYPASS_GENERATION_METHODS:
        return True
    return False


def _load_auditvault_axes_by_slug(path: Path) -> dict[str, list[str]]:
    if not path.is_file():
        return {}
    axes_by_slug: dict[str, set[str]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        slug = str(row.get("protocol_slug") or "").strip().lower()
        if not slug:
            continue
        for axis in row.get("atlas_axes") or []:
            axes_by_slug.setdefault(slug, set()).add(str(axis))
    return {slug: sorted(ax) for slug, ax in axes_by_slug.items()}


def auditvault_axes_for_target(target_id: str, axes_index: dict[str, list[str]]) -> list[str]:
    return list(axes_index.get(str(target_id or "").strip().lower(), []))



def _structural_validity(vector: AttackVector) -> tuple[bool, str]:
    """Validate hypothesis-layer vectors; grid vectors are assumed valid."""
    metadata = vector.metadata or {}
    if not metadata.get("hypothesis_id"):
        return True, ""

    from night_shift_security.domain.attack_hypotheses.base import (
        attack_vector_to_hypothesis,
        validate_hypothesis,
    )

    hypothesis = attack_vector_to_hypothesis(vector)
    return validate_hypothesis(hypothesis)


def apply_structural_filters(
    vectors: list[AttackVector],
    config: dict[str, Any] | None = None,
) -> tuple[list[AttackVector], FilterStats]:
    """
    Apply early structural filters before expensive simulation.

    Filters: structural validity, dedup fingerprint, feasibility heuristics,
    priority floor (catalog/ground-truth bypass priority floor only).
    """
    cfg = {**STRUCTURAL_FILTER_DEFAULTS, **(config or {})}
    stats = FilterStats(input_count=len(vectors))

    if not cfg.get("enabled", True):
        stats.output_count = len(vectors)
        ranked = [attach_ranking_signals(vector) for vector in vectors]
        return sorted(
            ranked,
            key=lambda v: (v.metadata or {}).get("priority_score", 0.0),
            reverse=True,
        ), stats

    axes_cfg = cfg.get("auditvault_axes") or {}
    axes_enabled = bool(axes_cfg.get("enabled", False))
    axes_index = (
        _load_auditvault_axes_by_slug(Path(axes_cfg.get("path", "data/security_results/knowledge/auditvault_patterns.jsonl")))
        if axes_enabled
        else {}
    )
    required_min = int(axes_cfg.get("required_min_count", 1))
    priority_bump = float(axes_cfg.get("priority_bump_per_ref", 0.02))

    seen: set[tuple[Any, ...]] = set()
    kept: list[AttackVector] = []

    for vector in vectors:
        vector = attach_ranking_signals(vector)
        metadata = vector.metadata or {}

        valid, reason = _structural_validity(vector)
        if not valid:
            stats.record_drop("structural_invalid")
            continue

        if cfg.get("dedupe", True):
            fingerprint = vector_fingerprint(vector)
            if fingerprint in seen:
                stats.record_drop("duplicate")
                continue
            seen.add(fingerprint)

        if cfg.get("feasibility_checks", True) and not should_bypass_priority_floor(vector):
            feasible, _ = _feasibility_check(vector.template_id, vector.parameters)
            if not feasible:
                stats.record_drop("infeasible")
                continue

        min_priority = float(cfg.get("min_priority_score", 0.05))
        priority = float(metadata.get("priority_score", 0.0))
        if axes_enabled:
            axes = auditvault_axes_for_target(vector.target_id, axes_index)
            metadata["auditvault_atlas_axes"] = axes
            if len(axes) < required_min and not should_bypass_priority_floor(vector):
                # Advisory penalty — vector is still kept, but loses ranking lift.
                metadata["auditvault_atlas_axis_gap"] = required_min - len(axes)
                stats.record_drop("auditvault_axis_gap_kept_with_penalty")
            else:
                bump = priority_bump * min(len(axes), 5)
                priority += bump
                metadata["auditvault_priority_bump"] = bump
                metadata.pop("auditvault_atlas_axis_gap", None)
        if (
            not should_bypass_priority_floor(vector)
            and priority < min_priority
        ):
            stats.record_drop("low_priority")
            continue

        metadata["filter_passed"] = True
        kept.append(
            AttackVector(
                template_id=vector.template_id,
                parameters=vector.parameters,
                target_id=vector.target_id,
                label=vector.label,
                metadata=metadata,
            )
        )

    kept.sort(
        key=lambda v: (v.metadata or {}).get("priority_score", 0.0),
        reverse=True,
    )
    stats.output_count = len(kept)
    stats.dropped = stats.input_count - stats.output_count
    return kept, stats