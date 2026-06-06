"""Stateless findings deduplication — canonical vector key."""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from night_shift_security.data.schemas import Finding


@dataclass
class DedupeReport:
    """Summary of a deduplication pass."""

    before_count: int
    after_count: int
    dropped_count: int
    dropped_examples: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "before_count": self.before_count,
            "after_count": self.after_count,
            "dropped_count": self.dropped_count,
            "dropped_examples": self.dropped_examples,
        }


def canonical_params(parameters: dict[str, Any]) -> dict[str, Any]:
    """Normalize attack parameters for stable comparison."""
    normalized: dict[str, Any] = {}
    for key in sorted(parameters.keys()):
        value = parameters[key]
        if isinstance(value, bool):
            normalized[key] = value
        elif isinstance(value, float):
            normalized[key] = round(value, 6)
        elif isinstance(value, int):
            normalized[key] = value
        else:
            normalized[key] = str(value)
    return normalized


def protocol_id(finding: Finding) -> str:
    """Protocol scope for dedupe key — prefer explicit target, then rediscovery id."""
    if finding.target_id:
        return finding.target_id
    if finding.rediscovered_exploit_id:
        return finding.rediscovered_exploit_id
    return "generic"


def primary_invariant(finding: Finding) -> str:
    """Primary broken invariant — first violation id, or empty."""
    if finding.invariant_violations:
        return finding.invariant_violations[0].invariant_id
    return ""


def canonical_key(finding: Finding) -> str:
    """
    Conservative dedupe key:

    template_id + canonical parameters + protocol + primary invariant
    """
    payload = {
        "template_id": finding.template_id,
        "parameters": canonical_params(finding.parameters),
        "protocol": protocol_id(finding),
        "primary_invariant": primary_invariant(finding),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _finding_rank(finding: Finding) -> tuple:
    """Higher is better — used to pick the survivor per key."""
    return (
        finding.severity_score,
        finding.economic_impact_usd,
        finding.confidence,
        1 if finding.rediscovered_exploit_id else 0,
    )


def dedupe_findings(
    findings: list[Finding],
    *,
    max_examples: int = 10,
) -> tuple[list[Finding], DedupeReport]:
    """
    Collapse duplicate findings sharing a canonical key.

    Keeps the highest-ranked survivor per key. Original finding_ids are
    preserved on survivors; duplicates are dropped.
    """
    before = len(findings)
    if before == 0:
        return [], DedupeReport(0, 0, 0)

    best_by_key: dict[str, Finding] = {}
    dropped_examples: list[dict] = []

    for finding in findings:
        key = canonical_key(finding)
        existing = best_by_key.get(key)
        if existing is None:
            best_by_key[key] = finding
            continue

        if _finding_rank(finding) > _finding_rank(existing):
            if len(dropped_examples) < max_examples:
                dropped_examples.append(_dropped_example(existing, finding, key))
            best_by_key[key] = finding
        else:
            if len(dropped_examples) < max_examples:
                dropped_examples.append(_dropped_example(finding, existing, key))

    deduped = sorted(best_by_key.values(), key=_finding_rank, reverse=True)
    after = len(deduped)

    return deduped, DedupeReport(
        before_count=before,
        after_count=after,
        dropped_count=before - after,
        dropped_examples=dropped_examples,
    )


def _dropped_example(dropped: Finding, kept: Finding, key: str) -> dict:
    return {
        "dropped_id": dropped.finding_id,
        "kept_id": kept.finding_id,
        "template_id": dropped.template_id,
        "protocol": protocol_id(dropped),
        "primary_invariant": primary_invariant(dropped),
        "canonical_key": key[:16],
        "dropped_severity_score": round(dropped.severity_score, 4),
        "kept_severity_score": round(kept.severity_score, 4),
    }


def log_dedupe_report(report: DedupeReport, *, log=print) -> None:
    """Emit human-readable before/after summary."""
    log(f"  Before: {report.before_count}")
    log(f"  After:  {report.after_count}")
    log(f"  Dropped: {report.dropped_count}")
    if report.dropped_examples:
        log("  Dropped examples:")
        for ex in report.dropped_examples:
            log(
                f"    {ex['dropped_id']} → duplicate of {ex['kept_id']} "
                f"({ex['template_id']} / {ex['protocol']} / {ex['primary_invariant']})"
            )