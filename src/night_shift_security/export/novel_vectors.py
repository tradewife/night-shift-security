"""Novel attack vector catalog export — ranked hypotheses with test status."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.validation.evidence_grading import shoestring_evidence_grade_candidate


def _candidate_catalog_entry(candidate: AttackCandidateResult) -> dict[str, Any]:
    meta = dict(candidate.vector.metadata or {})
    return {
        "hypothesis_id": str(meta.get("hypothesis_id") or candidate.vector.label),
        "template_id": candidate.vector.template_id,
        "target_id": candidate.vector.target_id,
        "label": candidate.vector.label,
        "parameters": dict(candidate.vector.parameters),
        "generation_method": str(meta.get("generation_method", "")),
        "priority_score": float(meta.get("priority_score", 0.0)),
        "novelty_score": float(meta.get("novelty_score", 0.0)),
        "rejected": candidate.rejected,
        "rejection_reason": candidate.rejection_reason,
        "evidence_grade": candidate.evidence_grade,
        "shoestring_evidence_grade": shoestring_evidence_grade_candidate(candidate),
        "severity_score": round(candidate.severity_score, 4),
        "reproduction_tier": candidate.reproduction_tier,
        "deployed_viable": candidate.deployed_viable,
        "catalog_analogue": candidate.catalog_analogue,
        "submission_readiness": candidate.submission_readiness,
        "solana_reproduced": candidate.solana_reproduced,
        "fork_reproduced": candidate.fork_reproduced,
        "parent_ids": list(meta.get("parent_ids", [])),
        "lineage": list(meta.get("lineage", [])),
    }


def export_novel_vector_catalog(
    candidates: list[AttackCandidateResult],
    run_meta: dict[str, Any],
    output_dir: Path,
    *,
    min_novelty_score: float = 0.0,
    include_rejected: bool = True,
) -> Path:
    """
    Export ranked hypothesis catalog with test outcomes.

    Writes knowledge/novel_vectors.jsonl (all entries) and novel_vectors_top.json.
    """
    knowledge_dir = output_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for candidate in candidates:
        if candidate.rejected and not include_rejected:
            continue
        entry = _candidate_catalog_entry(candidate)
        if entry["novelty_score"] < min_novelty_score:
            continue
        entries.append(entry)

    entries.sort(
        key=lambda e: (e["novelty_score"], e["priority_score"], e["severity_score"]),
        reverse=True,
    )

    jsonl_path = knowledge_dir / "novel_vectors.jsonl"
    with open(jsonl_path, "w") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, default=str) + "\n")

    summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_meta.get("run_at"),
        "campaign_id": run_meta.get("campaign_id", ""),
        "entry_count": len(entries),
        "min_novelty_score": min_novelty_score,
        "top_entries": entries[:50],
    }
    top_path = knowledge_dir / "novel_vectors_top.json"
    top_path.write_text(json.dumps(summary, indent=2, default=str))

    return jsonl_path