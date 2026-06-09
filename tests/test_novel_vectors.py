"""Tests for novel vector catalog export."""

import json
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, AttackVector
from night_shift_security.export.novel_vectors import export_novel_vector_catalog


def _candidate(novelty: float, rejected: bool = False) -> AttackCandidateResult:
    return AttackCandidateResult(
        vector=AttackVector(
            template_id="flash_loan_oracle",
            parameters={"loan_amount_usd": 1_000_000},
            target_id="kamino",
            label="kamino_test",
            metadata={
                "hypothesis_id": f"hyp-{novelty}",
                "novelty_score": novelty,
                "priority_score": 0.5,
            },
        ),
        success_rate=1.0,
        mean_severity_score=0.5,
        mean_economic_impact_usd=1_000_000.0,
        reproducibility=1.0,
        generality=0.5,
        realism_score=0.5,
        invariant_violation_count=1,
        severity_score=0.5,
        rejected=rejected,
    )


def test_export_novel_vector_catalog(tmp_path: Path):
    path = export_novel_vector_catalog(
        [_candidate(0.8), _candidate(0.2), _candidate(0.9, rejected=True)],
        {"run_at": "2026-06-09T00:00:00+00:00", "campaign_id": "test-campaign"},
        tmp_path,
        include_rejected=True,
    )
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 3
    top = json.loads((tmp_path / "knowledge" / "novel_vectors_top.json").read_text())
    assert top["entry_count"] == 3
    assert top["campaign_id"] == "test-campaign"
    assert top["top_entries"][0]["novelty_score"] == 0.9