"""Tests for LLM quality eval harness."""

from night_shift_security.eval.llm_quality import run_llm_quality_eval


def test_run_llm_quality_eval(tmp_path):
    result = run_llm_quality_eval(output_dir=tmp_path)
    assert len(result["providers"]) == 2
    assert result["gate"] == "validate_hypothesis"
    assert "winner" in result
    assert (tmp_path / "knowledge" / "llm_quality_eval.json").exists()