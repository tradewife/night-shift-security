"""AuditVault + advisory corpus adapter — sandbox-safe unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from night_shift_security.platform import auditvault as av
from night_shift_security.platform.auditvault import (
    DEFAULT_FINDINGS_PATH,
    DEFAULT_KNOWLEDGE_PATH,
    DEFAULT_PATTERNS_PATH,
    auditvault_summary,
    build_auditvault_patterns,
    sync_auditvault_findings,
    write_auditvault_ids,
    write_auditvault_patterns,
)
from night_shift_security.platform.corpus import (
    AUDIT_CORPUS_DEFAULTS,
    enrich_with_audit_corpus,
)


@pytest.fixture()
def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "auditvault"
    (repo / "findings").mkdir(parents=True)
    (repo / "protocols").mkdir()
    (repo / "protocols" / "Wormhole").mkdir()
    proto_md = (
        "---\n"
        "name: Wormhole\n"
        "url: https://wormhole.com\n"
        "sector: bridge\n"
        "---\n"
        "# Wormhole protocol entry\n"
        "Cross-chain messaging network.\n"
        "[[Bridge]]\n"
    )
    (repo / "protocols" / "Wormhole" / "Wormhole.md").write_text(proto_md)

    finding_md = (
        "---\n"
        "title: Wormhole Signature Replay\n"
        "bug: cross-chain replay\n"
        "impact: Critical\n"
        "tags: [bridge, \"Cross-chain Replay\", Solana]\n"
        "protocols: [Wormhole, wormhole]\n"
        "auditors: [Trail of Bits, Neodyme]\n"
        "report_date: 2024-08-15\n"
        "report: https://example.com/audit/wormhole-sig-replay.pdf\n"
        "source: https://github.com/example/wormhole-findings\n"
        "---\n"
        "# Cross-chain signature replay\n"
        "Vault authority set lacks chain-domain separation; see [[Wormhole]].\n"
    )
    (repo / "findings" / "wormhole-sig-replay.md").write_text(finding_md)

    second_md = (
        "---\n"
        "title: Optimistic Oracle Latency\n"
        "bug: logic error\n"
        "impact: High\n"
        "tags: [oracle, \"Price Manipulation\"]\n"
        "protocols: [uma]\n"
        "auditors: [OpenZeppelin]\n"
        "report_date: 2024-02-01\n"
        "report: https://example.com/audit/uma-oracle.pdf\n"
        "---\n"
        "Oracle price lag exploited for $X.\n"
    )
    (repo / "findings" / "uma-oracle.md").write_text(second_md)

    bad_md = "no frontmatter at all\nnerver parse me\n"
    (repo / "findings" / "broken.md").write_text(bad_md)
    return repo


def test_severity_score_mapping():
    assert av._severity_score("Critical") == 5
    assert av._severity_score("critical", "MEDIUM") == 5
    assert av._severity_score("HIGH") == 4
    assert av._severity_score("medium") == 3
    assert av._severity_score("Informational") == 1
    assert av._severity_score("unknown") == 0


def test_frontmatter_split_handles_lists_and_strings():
    meta, body = av._split_frontmatter(
        "---\n"
        "title: Foo\n"
        "tags: [a, b, c]\n"
        "report: \"https://x/y.pdf\"\n"
        "---\nbody text\n"
    )
    assert meta["title"] == "Foo"
    assert meta["tags"] == ["a", "b", "c"]
    assert meta["report"].startswith("https://")
    assert body.strip() == "body text"


def test_wikilink_extraction():
    body = "[[Wormhole]] and [[LayerZero/onboard]] and [[Aave]] references."
    assert av._protocols_in_text(body) == ["Aave", "LayerZero", "Wormhole"]


def test_atlas_axes_extract():
    text = (
        "This is a bridge finding with oracle price manipulation "
        "and MEV extraction."
    )
    assert av._atlas_axes(["bridge"], text, "bridge") == ["bridge", "mev", "oracle"]


def test_template_hints():
    texts = ["Cross-chain replay via guard signature", "Oracle latency edge case"]
    hints = [av._template_hints("Critical", ["bridge"], texts[0], "cross-chain replay")]
    assert hints[0] and "access_control_escalation" in hints[0]


def test_sync_auditvault_findings_no_repo(tmp_path: Path):
    out = sync_auditvault_findings(tmp_path / "missing", tmp_path / "out")
    assert out["status"] == "skipped_no_repo"
    assert Path(out["path"]).is_file()


def test_sync_auditvault_findings_parses_repo(fake_repo: Path, tmp_path: Path):
    out = sync_auditvault_findings(fake_repo, tmp_path / "out")
    assert out["status"] == "ok"
    assert out["finding_count"] >= 2
    assert out["protocol_count"] == 1

    payload = json.loads((tmp_path / "out" / "auditvault_findings.json").read_text())
    titles = [row["title"] for row in payload["findings"]]
    assert "Wormhole Signature Replay" in titles
    wormhole = next(r for r in payload["findings"] if "Wormhole" in r["title"])
    assert wormhole["severity_score"] == 5.0
    assert "bridge" in wormhole["atlas_axes"]
    assert "access_control_escalation" in wormhole["template_hints"]
    assert wormhole["primary_protocol_name"] == "Wormhole"
    assert wormhole["primary_protocol_url"] == "https://wormhole.com"
    assert wormhole["auditors"] == ["Trail of Bits", "Neodyme"]
    assert wormhole["source"] == "auditvault"

    # Broken entries recorded as warning, not failing the whole run.
    assert any("broken.md" in w for w in payload["warnings"]) or out["status"] == "ok"


def test_build_patterns_then_summary(fake_repo: Path, tmp_path: Path):
    sync_auditvault_findings(fake_repo, tmp_path / "out")
    patterns_path = tmp_path / "p.jsonl"
    ids_path = tmp_path / "ids.jsonl"
    payload = json.loads((tmp_path / "out" / "auditvault_findings.json").read_text())
    result = write_auditvault_patterns(
        tmp_path / "out" / "auditvault_findings.json", patterns_path
    )
    write_auditvault_ids(payload, ids_path)
    assert result["pattern_count"] == payload["finding_count"]
    assert patterns_path.is_file()

    summary = auditvault_summary(tmp_path / "out" / "auditvault_findings.json")
    assert summary["status"] in {"ok", "parsed_with_warnings"}
    assert any(s["slug"] == "wormhole" for s in summary["slugs"])
    assert summary["slugs"][0]["severity_max"] >= 4.0
    assert summary["axis_counts"].get("bridge", 0) >= 1


def test_patterns_distill_dedup(tmp_path: Path):
    payload = {
        "findings": [
            {
                "auditvault_id": "abc123",
                "title": "T",
                "impact": "High",
                "severity_score": 4.0,
                "primary_protocol_slug": "wormhole",
                "primary_protocol_name": "Wormhole",
                "tags": ["bridge"],
                "atlas_axes": ["bridge"],
                "template_hints": ["access_control_escalation"],
                "auditors": [],
                "source_link": "",
                "report_date": None,
                "sector": "",
            }
        ]
    }
    patterns = build_auditvault_patterns(payload)
    assert patterns and patterns[0]["pattern_id"] == "auditvault:abc123"
    assert patterns[0]["protocol_slug"] == "wormhole"
    assert patterns[0]["atlas_axes"] == ["bridge"]


def test_corpus_enrichment_unifies_solodit_and_auditvault(
    tmp_path: Path, monkeypatch
):
    # Manufacture Solodit + AuditVault patterns.
    auditvault_dir = tmp_path / "platform"
    auditvault_dir.mkdir()
    av_payload = {
        "findings": [
            {
                "auditvault_id": "f1",
                "title": "Wormhole Replay",
                "impact": "Critical",
                "severity_score": 5.0,
                "primary_protocol_slug": "wormhole",
                "primary_protocol_name": "Wormhole",
                "tags": ["bridge"],
                "atlas_axes": ["bridge", "oracle"],
                "template_hints": ["access_control_escalation"],
                "auditors": [],
                "source_link": "",
                "report_date": None,
                "sector": "bridge",
            }
        ]
    }
    (auditvault_dir / "auditvault_findings.json").write_text(json.dumps(av_payload))
    av_patterns = auditvault_dir / "auditvault_patterns.jsonl"
    ids_path = auditvault_dir / "auditvault_ids.jsonl"
    write_auditvault_patterns(auditvault_dir / "auditvault_findings.json", av_patterns)
    write_auditvault_ids(av_payload, ids_path)

    solodit_dir = tmp_path / "solodit_p"
    solodit_dir.mkdir(parents=True, exist_ok=True)
    (solodit_dir / "patterns.jsonl").write_text(
        json.dumps({
            "pattern_id": "solodit:ps1",
            "title": "Wormhole observed depositor",
            "impact": "HIGH",
            "quality_score": 4.0,
            "rarity_score": 3.5,
            "protocol_name": "wormhole",
            "query_key": "protocol:wormhole",
            "tags": ["Bridge"],
            "template_hints": ["access_control_escalation"],
            "source_link": "https://example.com/w",
        }) + "\n"
    )

    from night_shift_security.data.schemas import AttackCandidateResult, AttackVector

    vector = AttackVector(
        template_id="access_control_escalation",
        parameters={"target_role": "guardian"},
        target_id="wormhole",
        label="wormhole-guardian-misconfig",
        metadata={},
    )
    candidate = AttackCandidateResult(
        vector=vector,
        success_rate=1.0,
        mean_severity_score=1.0,
        mean_economic_impact_usd=1_000_000,
        reproducibility=1.0,
        generality=1.0,
        realism_score=1.0,
        invariant_violation_count=1,
        severity_score=0.9,
    )
    config = {
        **AUDIT_CORPUS_DEFAULTS,
        "solodit": {
            "enabled": True,
            "patterns_path": str(solodit_dir / "patterns.jsonl"),
        },
        "auditvault": {
            "enabled": True,
            "patterns_lookup_path": str(av_patterns),
            "ids_lookup_path": str(ids_path),
            "max_refs_per_candidate": 3,
            "severity_min": 3,
        },
    }
    stats = enrich_with_audit_corpus([candidate], config)
    assert stats["enabled"] is True
    assert stats["matched"] == 1
    assert stats["auditvault_matched"] == 1
    assert stats["solodit_matched"] == 1

    meta = candidate.vector.metadata
    assert meta["solodit_refs"], "Solodit refs missing"
    assert meta["auditvault_refs"], "AuditVault refs missing"
    assert meta["auditvault_severity_max"] == 5.0
    assert "bridge" in meta["atlas_axes"]
    assert meta["audit_corpus_score"] == pytest.approx(
        AUDIT_CORPUS_DEFAULTS["conviction"]["bonus_per_ref"] * 1.5,
        rel=1e-6,
    )
    assert meta["audit_corpus_ref_count"] == 2


def test_corpus_disabled_returns_zero(monkeypatch):
    from night_shift_security.data.schemas import AttackCandidateResult, AttackVector

    candidate = AttackCandidateResult(
        vector=AttackVector(
            template_id="reentrancy",
            parameters={"recursion_depth": 3},
            target_id="uniswap",
            label="uniswap-reentrancy",
            metadata={},
        ),
        success_rate=1.0,
        mean_severity_score=1.0,
        mean_economic_impact_usd=1_000_000,
        reproducibility=1.0,
        generality=1.0,
        realism_score=1.0,
        invariant_violation_count=1,
        severity_score=0.9,
    )
    stats = enrich_with_audit_corpus([candidate], {"enabled": False})
    assert stats == {"enabled": False, "matched": 0, "auditvault_matched": 0, "solodit_matched": 0}
