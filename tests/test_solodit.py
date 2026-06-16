import json
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, AttackVector
from night_shift_security.platform.solodit import (
    SoloditError,
    apply_solodit_enrichment,
    build_solodit_patterns,
    solodit_queries,
    sync_solodit_findings,
    write_solodit_patterns,
)


def _finding_payload() -> dict:
    return {
        "findings": [
            {
                "id": "64691",
                "slug": "oracle-price-manipulation",
                "title": "Oracle price can be manipulated before borrow",
                "content": "full markdown",
                "summary": "summary",
                "kind": "MARKDOWN",
                "impact": "HIGH",
                "quality_score": 4,
                "general_score": 5,
                "report_date": "2026-01-01",
                "firm_name": "Cyfrin",
                "protocol_name": "Kamino",
                "protocols_protocol": {
                    "name": "Kamino",
                    "protocols_protocolcategoryscore": [
                        {"protocols_protocolcategory": {"title": "Lending"}, "score": 4}
                    ],
                },
                "finders_count": 1,
                "issues_issue_finders": [{"wardens_warden": {"handle": "researcher"}}],
                "issues_issuetagscore": [
                    {"tags_tag": {"title": "Oracle"}},
                    {"tags_tag": {"title": "Price Manipulation"}},
                ],
                "source_link": "https://example.test/finding",
                "github_link": None,
                "pdf_link": None,
                "pdf_page_from": None,
            }
        ],
        "metadata": {"totalResults": 1, "currentPage": 1, "pageSize": 100, "totalPages": 1},
        "rateLimit": {"limit": 20, "remaining": 19, "reset": 0},
    }


def _candidate(template: str = "flash_loan_oracle", target: str = "kamino") -> AttackCandidateResult:
    return AttackCandidateResult(
        vector=AttackVector(template_id=template, target_id=target, parameters={}, label=""),
        success_rate=1.0,
        mean_severity_score=1.0,
        mean_economic_impact_usd=1_000_000,
        reproducibility=1.0,
        generality=1.0,
        realism_score=1.0,
        invariant_violation_count=1,
        severity_score=0.9,
    )


def _normalized_finding() -> dict:
    return {
        "source": "solodit",
        "query_key": "protocol:kamino",
        "synced_at": "2026-06-16T00:00:00+00:00",
        "solodit_id": "64691",
        "slug": "oracle-price-manipulation",
        "title": "Oracle price can be manipulated before borrow",
        "content": "full markdown",
        "summary": "summary",
        "kind": "MARKDOWN",
        "impact": "HIGH",
        "quality_score": 4.0,
        "rarity_score": 5.0,
        "report_date": "2026-01-01",
        "firm_name": "Cyfrin",
        "protocol_name": "Kamino",
        "protocol_categories": ["Lending"],
        "finders_count": 1,
        "finders": ["researcher"],
        "tags": ["Oracle", "Price Manipulation"],
        "source_link": "https://example.test/finding",
        "github_link": None,
        "pdf_link": None,
        "pdf_page_from": None,
    }


def test_solodit_queries_include_targets_and_patterns():
    queries = solodit_queries(scope="target-plus-pattern", target_terms=("kamino",), pattern_tags=("Oracle",))
    keys = {q["query_key"] for q in queries}
    assert keys == {"protocol:kamino", "tag:oracle"}
    assert queries[0]["filters"]["impact"] == ["HIGH", "MEDIUM"]


def test_sync_solodit_findings_normalizes_and_dedupes(tmp_path: Path):
    calls = []

    def fake_post(payload: dict) -> dict:
        calls.append(payload)
        return _finding_payload()

    result = sync_solodit_findings(
        tmp_path,
        scope="targets-only",
        page_size=100,
        max_pages_per_query=1,
        http_post=fake_post,
        sleep_seconds=0,
    )
    assert result["status"] == "ok"
    payload = json.loads((tmp_path / "solodit_findings.json").read_text())
    assert payload["finding_count"] == 1
    assert payload["findings"][0]["tags"] == ["Oracle", "Price Manipulation"]
    assert payload["findings"][0]["protocol_categories"] == ["Lending"]
    assert calls[0]["pageSize"] == 100


def test_sync_solodit_missing_key_skips_without_error(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("CYFRIN_API_KEY", raising=False)
    result = sync_solodit_findings(tmp_path)
    assert result["status"] == "skipped_missing_key"
    payload = json.loads((tmp_path / "solodit_findings.json").read_text())
    assert payload["findings"] == []


def test_sync_solodit_records_query_error(tmp_path: Path):
    def fake_post(_payload: dict) -> dict:
        raise SoloditError("solodit_http_429: Rate limit exceeded")

    result = sync_solodit_findings(
        tmp_path,
        scope="targets-only",
        max_pages_per_query=1,
        http_post=fake_post,
        sleep_seconds=0,
    )
    payload = json.loads((tmp_path / "solodit_findings.json").read_text())
    assert result["status"] == "ok"
    assert payload["finding_count"] == 0
    assert payload["queries"][0]["status"] == "error"
    assert "429" in payload["queries"][0]["message"]


def test_write_solodit_patterns_maps_template_hints(tmp_path: Path):
    findings_path = tmp_path / "solodit_findings.json"
    findings_path.write_text(json.dumps({"findings": [_normalized_finding()]}))
    out_path = tmp_path / "patterns.jsonl"
    result = write_solodit_patterns(findings_path, out_path)
    assert result["pattern_count"] == 1
    pattern = json.loads(out_path.read_text().strip())
    assert pattern["template_hints"] == ["flash_loan_oracle"]


def test_apply_solodit_enrichment_stamps_metadata(tmp_path: Path):
    patterns = build_solodit_patterns({"findings": [_normalized_finding()]})
    path = tmp_path / "patterns.jsonl"
    path.write_text("\n".join(json.dumps(p) for p in patterns) + "\n")
    candidate = _candidate()

    stats = apply_solodit_enrichment([candidate], {"patterns_path": str(path)})

    assert stats["matched"] == 1
    assert candidate.vector.metadata["solodit_quality_max"] == 4.0
    assert candidate.vector.metadata["solodit_refs"][0]["pattern_id"] == "solodit:64691"
