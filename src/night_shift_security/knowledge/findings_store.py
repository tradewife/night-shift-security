"""Lightweight JSONL findings store with lineage support."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult, Finding, attack_vector_key


@dataclass
class StoredRecord:
    record_id: str
    run_at: str
    record_type: str
    hypothesis_id: str
    parent_ids: list[str] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)
    generation_method: str = ""
    template_id: str = ""
    target_id: str = ""
    label: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    rejected: bool = False
    evidence_grade: int = 0
    evidence_grade_label: str = "none"
    axis_scores: dict[str, float] = field(default_factory=dict)
    axis_survival_rate: float = 0.0
    severity_score: float = 0.0
    gate_outcomes: dict[str, Any] = field(default_factory=dict)
    promoted: bool = False
    finding_id: str = ""
    priority_score: float = 0.0
    novelty_score: float = 0.0
    campaign_id: str = ""
    reproduction_tier: str = "simulation"
    deployed_viable: bool = False
    catalog_analogue: bool = False
    submission_readiness: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredRecord:
        return cls(
            record_id=data["record_id"],
            run_at=data["run_at"],
            record_type=data["record_type"],
            hypothesis_id=data.get("hypothesis_id", ""),
            parent_ids=list(data.get("parent_ids", [])),
            lineage=list(data.get("lineage", [])),
            generation_method=data.get("generation_method", ""),
            template_id=data.get("template_id", ""),
            target_id=data.get("target_id", ""),
            label=data.get("label", ""),
            parameters=dict(data.get("parameters", {})),
            rejected=bool(data.get("rejected", False)),
            evidence_grade=int(data.get("evidence_grade", 0)),
            evidence_grade_label=data.get("evidence_grade_label", "none"),
            axis_scores=dict(data.get("axis_scores", {})),
            axis_survival_rate=float(data.get("axis_survival_rate", 0.0)),
            severity_score=float(data.get("severity_score", 0.0)),
            gate_outcomes=dict(data.get("gate_outcomes", {})),
            promoted=bool(data.get("promoted", False)),
            finding_id=data.get("finding_id", ""),
            priority_score=float(data.get("priority_score", 0.0)),
            novelty_score=float(data.get("novelty_score", 0.0)),
            campaign_id=str(data.get("campaign_id", "")),
            reproduction_tier=str(data.get("reproduction_tier", "simulation")),
            deployed_viable=bool(data.get("deployed_viable", False)),
            catalog_analogue=bool(data.get("catalog_analogue", False)),
            submission_readiness=str(data.get("submission_readiness", "draft")),
        )


@dataclass
class RecordRunStats:
    added: int = 0
    candidates: int = 0
    findings: int = 0
    lineage_roots: int = 0
    store_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FindingsStore:
    path: Path
    records: list[StoredRecord] = field(default_factory=list)
    by_hypothesis_id: dict[str, list[StoredRecord]] = field(default_factory=dict)
    children_index: dict[str, set[str]] = field(default_factory=dict)

    def _index_record(self, record: StoredRecord) -> None:
        if record.hypothesis_id:
            self.by_hypothesis_id.setdefault(record.hypothesis_id, []).append(record)
        for parent_id in record.parent_ids:
            self.children_index.setdefault(parent_id, set()).add(record.hypothesis_id)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_record_id(hypothesis_id: str, run_at: str, record_type: str) -> str:
    if hypothesis_id:
        return f"{hypothesis_id}:{run_at}:{record_type}"
    return str(uuid.uuid4())


def _vector_metadata(candidate: AttackCandidateResult) -> dict[str, Any]:
    return dict(candidate.vector.metadata or {})


def _gate_outcomes(candidate: AttackCandidateResult) -> dict[str, Any]:
    return {
        "rejected": candidate.rejected,
        "rejection_reason": candidate.rejection_reason,
        "mc_reproducibility": candidate.mc_reproducibility,
        "mc_simulations": candidate.mc_simulations,
        "foundry_confirmed": candidate.foundry_confirmed,
        "fork_confirmed": candidate.fork_confirmed,
        "fork_reproduced": candidate.fork_reproduced,
        "solana_confirmed": candidate.solana_confirmed,
        "solana_reproduced": candidate.solana_reproduced,
        "pbo": candidate.pbo,
        "cpcv_verdict": candidate.cpcv_verdict,
        "catalog_exploit_id": candidate.catalog_exploit_id,
    }


def _candidate_record(
    candidate: AttackCandidateResult,
    run_at: str,
    *,
    promoted: bool = False,
    finding_id: str = "",
) -> StoredRecord:
    meta = _vector_metadata(candidate)
    hypothesis_id = str(meta.get("hypothesis_id") or candidate.vector.label)
    return StoredRecord(
        record_id=_stable_record_id(hypothesis_id, run_at, "finding" if promoted else "candidate"),
        run_at=run_at,
        record_type="finding" if promoted else "candidate",
        hypothesis_id=hypothesis_id,
        parent_ids=list(meta.get("parent_ids", [])),
        lineage=list(meta.get("lineage", [])),
        generation_method=str(meta.get("generation_method", "")),
        template_id=candidate.vector.template_id,
        target_id=candidate.vector.target_id,
        label=candidate.vector.label,
        parameters=dict(candidate.vector.parameters),
        rejected=candidate.rejected,
        evidence_grade=candidate.evidence_grade,
        evidence_grade_label=candidate.evidence_grade_label,
        axis_scores=dict(candidate.axis_scores),
        axis_survival_rate=candidate.axis_survival_rate,
        severity_score=candidate.severity_score,
        gate_outcomes=_gate_outcomes(candidate),
        promoted=promoted,
        finding_id=finding_id,
        priority_score=float(meta.get("priority_score", 0.0)),
        novelty_score=float(meta.get("novelty_score", 0.0)),
        campaign_id=str(meta.get("campaign_id", "")),
        reproduction_tier=candidate.reproduction_tier,
        deployed_viable=candidate.deployed_viable,
        catalog_analogue=candidate.catalog_analogue,
        submission_readiness=candidate.submission_readiness,
    )


def _finding_lookup(
    findings: list[Finding],
    candidates: list[AttackCandidateResult],
) -> dict[str, Finding]:
    """Map candidate vector keys to promoted findings."""
    by_key: dict[tuple[Any, ...], Finding] = {}
    for finding in findings:
        key = attack_vector_key(
            finding.template_id,
            finding.target_id,
            finding.parameters,
        )
        by_key[key] = finding

    lookup: dict[str, Finding] = {}
    for candidate in candidates:
        if candidate.rejected:
            continue
        key = candidate.vector.key()
        finding = by_key.get(key)
        if finding is None:
            continue
        meta = _vector_metadata(candidate)
        hypothesis_id = str(meta.get("hypothesis_id") or candidate.vector.label)
        lookup[hypothesis_id] = finding
    return lookup


def load_store(path: Path) -> FindingsStore:
    """Load append-only JSONL store and build lineage indexes."""
    store = FindingsStore(path=path)
    if not path.exists():
        return store

    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = StoredRecord.from_dict(json.loads(line))
            store.records.append(record)
            store._index_record(record)
    return store


def record_run(
    candidates: list[AttackCandidateResult],
    findings: list[Finding],
    run_meta: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> RecordRunStats:
    """Append evaluated candidates and promoted findings to the JSONL store."""
    cfg = config or {}
    store_path = Path(cfg.get("path", "data/security_results/knowledge/findings_store.jsonl"))
    store_path.parent.mkdir(parents=True, exist_ok=True)

    run_at = str(run_meta.get("run_at") or _utc_now_iso())
    campaign_id = str(run_meta.get("campaign_id", "") or "")
    finding_by_hypothesis = _finding_lookup(findings, candidates)
    promoted_hypothesis_ids = set(finding_by_hypothesis.keys())

    new_records: list[StoredRecord] = []
    lineage_roots: set[str] = set()

    for candidate in candidates:
        meta = _vector_metadata(candidate)
        hypothesis_id = str(meta.get("hypothesis_id") or candidate.vector.label)
        promoted = hypothesis_id in promoted_hypothesis_ids
        finding = finding_by_hypothesis.get(hypothesis_id)
        record = _candidate_record(
            candidate,
            run_at,
            promoted=promoted,
            finding_id=finding.finding_id if finding else "",
        )
        if campaign_id:
            record.campaign_id = campaign_id
        new_records.append(record)

        root = record.lineage[0] if record.lineage else hypothesis_id
        if root:
            lineage_roots.add(root)

    with open(store_path, "a") as handle:
        for record in new_records:
            handle.write(json.dumps(record.to_dict(), default=str) + "\n")

    return RecordRunStats(
        added=len(new_records),
        candidates=sum(1 for r in new_records if r.record_type == "candidate" and not r.promoted),
        findings=sum(1 for r in new_records if r.promoted),
        lineage_roots=len(lineage_roots),
        store_path=str(store_path),
    )


def ancestors(store: FindingsStore, hypothesis_id: str) -> list[str]:
    """Return ordered ancestor hypothesis IDs for the latest known record."""
    records = store.by_hypothesis_id.get(hypothesis_id, [])
    if not records:
        return []
    latest = records[-1]
    ordered: list[str] = []
    seen: set[str] = set()
    for parent_id in latest.lineage:
        if parent_id and parent_id not in seen:
            ordered.append(parent_id)
            seen.add(parent_id)
    return ordered


def descendants(store: FindingsStore, hypothesis_id: str) -> list[str]:
    """Return direct and indirect descendant hypothesis IDs."""
    result: list[str] = []
    seen: set[str] = set()
    frontier = list(store.children_index.get(hypothesis_id, set()))
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        result.append(current)
        frontier.extend(store.children_index.get(current, set()))
    return result


def lineage_survival_stats(store: FindingsStore) -> dict[str, Any]:
    """Compute survival rates grouped by generation method and lineage depth."""
    if not store.records:
        return {
            "total_records": 0,
            "by_generation_method": {},
            "by_lineage_depth": {},
            "promotion_rate": 0.0,
            "mean_evidence_grade": 0.0,
        }

    by_method: dict[str, dict[str, Any]] = {}
    by_depth: dict[int, dict[str, Any]] = {}
    grades: list[int] = []
    promoted = 0

    for record in store.records:
        grades.append(record.evidence_grade)
        if record.promoted:
            promoted += 1

        method = record.generation_method or "unknown"
        method_bucket = by_method.setdefault(
            method,
            {"count": 0, "promoted": 0, "mean_evidence_grade": 0.0, "grades": []},
        )
        method_bucket["count"] += 1
        method_bucket["grades"].append(record.evidence_grade)
        if record.promoted:
            method_bucket["promoted"] += 1

        depth = len(record.lineage)
        depth_bucket = by_depth.setdefault(
            depth,
            {"count": 0, "promoted": 0, "grades": []},
        )
        depth_bucket["count"] += 1
        depth_bucket["grades"].append(record.evidence_grade)
        if record.promoted:
            depth_bucket["promoted"] += 1

    for bucket in by_method.values():
        grades_list = bucket.pop("grades")
        bucket["mean_evidence_grade"] = round(
            sum(grades_list) / len(grades_list),
            4,
        ) if grades_list else 0.0
        bucket["promotion_rate"] = round(
            bucket["promoted"] / bucket["count"],
            4,
        ) if bucket["count"] else 0.0

    for depth, bucket in by_depth.items():
        grades_list = bucket.pop("grades")
        bucket["mean_evidence_grade"] = round(
            sum(grades_list) / len(grades_list),
            4,
        ) if grades_list else 0.0
        bucket["promotion_rate"] = round(
            bucket["promoted"] / bucket["count"],
            4,
        ) if bucket["count"] else 0.0

    return {
        "total_records": len(store.records),
        "by_generation_method": by_method,
        "by_lineage_depth": {str(k): v for k, v in sorted(by_depth.items())},
        "promotion_rate": round(promoted / len(store.records), 4),
        "mean_evidence_grade": round(sum(grades) / len(grades), 4),
    }


def best_evidence_per_lineage_root(store: FindingsStore) -> dict[str, dict[str, Any]]:
    """Highest evidence grade reached per lineage root."""
    best: dict[str, dict[str, Any]] = {}
    for record in store.records:
        root = record.lineage[0] if record.lineage else record.hypothesis_id
        if not root:
            continue
        current = best.get(root)
        if current is None or record.evidence_grade > current["evidence_grade"]:
            best[root] = {
                "hypothesis_id": record.hypothesis_id,
                "evidence_grade": record.evidence_grade,
                "evidence_grade_label": record.evidence_grade_label,
                "promoted": record.promoted,
                "severity_score": record.severity_score,
                "generation_method": record.generation_method,
            }
    return best


def campaign_stats(store: FindingsStore, campaign_id: str) -> dict[str, Any]:
    """Aggregate records for a single campaign_id across runs."""
    records = [r for r in store.records if r.campaign_id == campaign_id]
    if not records:
        return {
            "campaign_id": campaign_id,
            "record_count": 0,
            "runs": 0,
            "promoted": 0,
            "mean_evidence_grade": 0.0,
            "mean_novelty_score": 0.0,
        }

    run_times = {r.run_at for r in records}
    grades = [r.evidence_grade for r in records]
    novelty = [r.novelty_score for r in records if r.novelty_score > 0]
    return {
        "campaign_id": campaign_id,
        "record_count": len(records),
        "runs": len(run_times),
        "promoted": sum(1 for r in records if r.promoted),
        "mean_evidence_grade": round(sum(grades) / len(grades), 4),
        "mean_novelty_score": round(sum(novelty) / len(novelty), 4) if novelty else 0.0,
        "deployed_viable_count": sum(1 for r in records if r.deployed_viable),
        "catalog_analogue_count": sum(1 for r in records if r.catalog_analogue),
    }