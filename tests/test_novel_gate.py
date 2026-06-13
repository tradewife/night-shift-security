"""Tests for Block C novel gate scoring."""

from pathlib import Path

from night_shift_security.orchestration.novel_gate import (
    score_novel_batch,
    write_human_gate_report,
)


def _minimal_findings(path: Path, *, catalog: bool, grade: int = 4) -> None:
    path.write_text(
        """
{
  "run_at": "2026-06-13T00:00:00Z",
  "campaign_id": "test-campaign",
  "findings": [
    {
      "finding_id": "f-novel-1",
      "target_id": "kamino-klend",
      "template_id": "flash_loan_oracle",
      "severity": "high",
      "severity_score": 0.9,
      "economic_impact_usd": 5000000.0,
      "reproducibility": 1.0,
      "priority_score": 0.8,
      "novelty_score": 0.7,
      "evidence_grade": %d,
      "catalog_analogue": %s,
      "deployed_viable": true,
      "reproduction_tier": "solana_validator",
      "solana_confirmed": true,
      "fork_reproduced": false,
      "solana_evidence": {
        "method": "solana_validator",
        "balance_verified": true,
        "balance_delta_lamports": 50000000000
      }
    }
  ]
}
"""
        % (grade, "true" if catalog else "false")
    )


def test_novel_gate_separates_catalogue(tmp_path: Path):
    novel_path = tmp_path / "novel.json"
    cat_path = tmp_path / "catalog.json"
    _minimal_findings(novel_path, catalog=False)
    _minimal_findings(cat_path, catalog=True)

    batch = score_novel_batch([novel_path, cat_path])
    assert len(batch["novel_candidates"]) == 1
    assert batch["novel_candidates"][0]["finding_id"] == "f-novel-1"
    assert batch["novel_candidates"][0]["human_gate"] != "hold_catalogue_analogue"


def test_write_human_gate_report(tmp_path: Path):
    findings = tmp_path / "findings.json"
    _minimal_findings(findings, catalog=False, grade=3)
    batch = score_novel_batch([findings])
    out = tmp_path / "gate.json"
    write_human_gate_report(batch, out)
    assert out.is_file()
    data = out.read_text()
    assert "human_gate_pending" in data