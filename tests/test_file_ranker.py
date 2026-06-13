"""Tests for per-file triage ranker."""

from pathlib import Path

from night_shift_security.triage.file_ranker import filter_by_min_score, rank_files, write_rank_report


def test_rank_files_scores_oracle_and_bridge(tmp_path: Path):
    (tmp_path / "programs" / "klend" / "src").mkdir(parents=True)
    (tmp_path / "programs" / "klend" / "src" / "oracle_price.rs").write_text("// oracle")
    (tmp_path / "bridge").mkdir(parents=True)
    (tmp_path / "bridge" / "wormhole_portal.sol").write_text("// bridge")
    (tmp_path / "utils").mkdir(parents=True)
    (tmp_path / "utils" / "math.rs").write_text("// math")

    ranked = rank_files(tmp_path)
    by_path = {r.path: r.score for r in ranked}
    assert by_path["bridge/wormhole_portal.sol"] == 5
    assert by_path["programs/klend/src/oracle_price.rs"] == 4
    assert by_path["utils/math.rs"] >= 2

    high = filter_by_min_score(ranked, 4)
    assert len(high) == 2


def test_write_rank_report(tmp_path: Path):
    (tmp_path / "lending").mkdir(parents=True)
    (tmp_path / "lending" / "borrow.rs").write_text("// borrow")
    out = tmp_path / "out.json"
    payload = write_rank_report(tmp_path, out, slug="kamino", min_score=1)
    assert payload["slug"] == "kamino"
    assert out.is_file()
    assert payload["above_min"] >= 1