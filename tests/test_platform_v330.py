"""Tests for SPEC v3.3.0 — platform sync, export gates, PoC bundler, IVSS."""

import json
from pathlib import Path

from night_shift_security.bounty.scoring import compute_bounty_score
from night_shift_security.config.loader import load_config
from night_shift_security.data.schemas import Finding, Severity
from night_shift_security.export.immunefi_ivss import format_ivss_section, ivss_vector_for_template
from night_shift_security.export.gates import resolve_export_track
from night_shift_security.export.immunefi_submission import export_bounty_export_tracks
from night_shift_security.export.poc_bundler import bundle_evm_repro_script, poc_metadata
from night_shift_security.orchestration import bounty_loop as bl
from night_shift_security.platform.sync import (
    build_scope_registry,
    platform_diff,
    sync_cantina_api,
    sync_immunefi_listing,
    sync_platforms,
)


def _finding(**kwargs) -> Finding:
    base = dict(
        finding_id="NSS-0099",
        template_id="access_control_escalation",
        target_id="wormhole",
        severity=Severity.HIGH,
        severity_score=0.9,
        economic_impact_usd=1_000_000.0,
        capital_required_usd=10_000.0,
        reproducibility=1.0,
        parameters={},
        invariant_violations=[],
        reproduction_steps=[],
        evidence_grade=4,
        evidence_grade_label="root_cause_artifacts",
        fork_reproduced=True,
        fork_evidence={
            "fork_test": "testForkWormholeBridgePauserAuthSurface",
            "triage_surface_verified": True,
            "balance_verified": True,
            "verifier_method": "triage_surface",
        },
        deployed_viable=False,
        catalog_analogue=False,
        reproduction_tier="fork_reproduced",
    )
    base.update(kwargs)
    return Finding(**base)


def test_resolve_export_track_triage_is_research_surface():
    finding = _finding()
    assert resolve_export_track(finding) == "research_surface"


def test_resolve_export_track_submittable_requires_full_gate():
    finding = _finding(
        deployed_viable=True,
        fork_evidence={
            "fork_test": "testForkEulerHistoricalBlock",
            "balance_verified": True,
            "balance_delta_wei": "1000000000000000000",
        },
        catalog_analogue=False,
    )
    score = compute_bounty_score(finding)
    if bl.qualifies_for_submission(finding, score):
        assert resolve_export_track(finding) == "submittable"
    else:
        assert resolve_export_track(finding) in ("research_surface", "hold")


def test_export_submittable_zero_without_qualify(tmp_path: Path):
    findings = [_finding()]
    result = export_bounty_export_tracks(findings, {"run_at": "2026-06-14"}, tmp_path)
    assert result["submittable_pack_count"] == 0
    assert result["research_pack_count"] >= 1
    sub_dir = tmp_path / "bounty" / "submittable"
    assert not any(sub_dir.glob("**/*.md")) if sub_dir.exists() else True


def test_poc_bundler_emits_forge_test():
    script = bundle_evm_repro_script(_finding())
    assert "forge test --match-test testForkWormholeBridgePauserAuthSurface" in script
    assert "TODO:" not in script


def test_poc_metadata_runnable():
    meta = poc_metadata(_finding())
    assert meta["runnable"] is True
    assert meta["fork_test"] == "testForkWormholeBridgePauserAuthSurface"


def test_ivss_sections_present():
    lines = format_ivss_section(_finding())
    text = "\n".join(lines)
    assert "## IVSS Risk Breakdown" in text
    assert "Attack Vector" in text


def test_ivss_template_mapping():
    vec = ivss_vector_for_template("reentrancy")
    assert vec["integrity"] == "High"


def test_sync_immunefi_listing_parses_slugs():
    html = '<a href="/bug-bounty/wormhole/">Wormhole</a><a href="/bug-bounty/kamino/">'
    result = sync_immunefi_listing(html=html)
    slugs = {p["slug"] for p in result["programs"]}
    assert "wormhole" in slugs
    assert "kamino" in slugs


def test_sync_cantina_api_mock():
    payload = {
        "items": [
            {
                "id": "abc",
                "name": "Morpho",
                "url": "https://cantina.xyz/bounties/abc",
                "status": "live",
                "submissionFee": "0.00",
                "totalRewardPot": "2500000",
                "currencyCode": "USDC",
                "company": {"handle": "morpho", "name": "Morpho"},
            }
        ]
    }
    result = sync_cantina_api(payload=payload)
    assert result["program_count"] == 1
    assert result["programs"][0]["deposit_usd"] == 0.0
    assert result["programs"][0]["max_bounty_usd"] == 2_500_000


def test_build_scope_registry_merges_curated():
    immunefi = sync_immunefi_listing(html='<a href="/bug-bounty/kamino/">')
    cantina = sync_cantina_api(
        payload={
            "items": [
                {
                    "id": "x",
                    "name": "Euler",
                    "status": "live",
                    "submissionFee": "50",
                    "totalRewardPot": "7500000",
                    "company": {"handle": "euler"},
                }
            ]
        }
    )
    scope = build_scope_registry(immunefi, cantina)
    assert scope["entries"]["kamino"]["curated"] is True
    assert scope["entries"]["euler"]["deposit_usd"] == 50.0


def test_platform_sync_skip_network(tmp_path: Path):
    immunefi_path = tmp_path / "immunefi_programs.json"
    cantina_path = tmp_path / "cantina_programs.json"
    immunefi_path.write_text(json.dumps({"programs": [{"slug": "wormhole"}], "program_count": 1}))
    cantina_path.write_text(json.dumps({"programs": [{"slug": "euler", "deposit_usd": 0}], "program_count": 1}))
    result = sync_platforms(tmp_path, skip_network=True)
    assert Path(result["scope_registry"]).is_file()


def test_platform_diff_reports_gaps(tmp_path: Path):
    immunefi_path = tmp_path / "immunefi_programs.json"
    cantina_path = tmp_path / "cantina_programs.json"
    immunefi_path.write_text(
        json.dumps(
            {
                "programs": [{"slug": "wormhole"}, {"slug": "frankendancer"}, {"slug": "injective"}],
                "program_count": 3,
            }
        )
    )
    cantina_path.write_text(
        json.dumps({"programs": [{"slug": "euler"}, {"slug": "kiln"}], "program_count": 2})
    )
    diff = platform_diff(tmp_path)
    assert diff["immunefi"]["live_count"] == 3
    assert "frankendancer" in diff["immunefi"]["missing_from_curated"]
    assert diff["cantina"]["live_count"] == 2


def test_bounty_loop_coinbase_uses_dedicated_config():
    assert bl._CONFIG_OVERRIDES["coinbase"] == "coinbase_cantina.json"
    assert bl._CONFIG_OVERRIDES["polymarket"] == "polymarket_cantina.json"


def test_cantina_override_configs_have_matching_target_paths():
    config_dir = Path("src/night_shift_security/config")
    expected = {
        "coinbase": "coinbase_cantina.json",
        "euler": "euler_cantina.json",
        "polymarket": "polymarket_cantina.json",
        "reserve-protocol": "reserve_protocol_cantina.json",
    }
    for slug, config_name in expected.items():
        cfg = load_config(config_dir / config_name)
        target_path = config_dir / str(cfg["target"]["config_path"])
        target_cfg = load_config(target_path)
        assert target_cfg["target_id"] == slug


def test_wormhole_registry_max_bounty_updated():
    from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS

    wormhole = next(p for p in IMMUNEFI_PROGRAMS if p.slug == "wormhole")
    assert wormhole.max_bounty_usd == 1_000_000


def test_deposit_usd_penalty_in_scoring():
    from night_shift_security.data.bounty_program import BountyProgram

    finding = _finding(target_id="uniswap", catalog_analogue=True)
    program = BountyProgram(
        platform="cantina",
        slug="uniswap",
        name="Uniswap",
        ecosystem="evm",
        max_bounty_usd=15_500_000,
        product_types=("amm",),
        templates=("composability_risk",),
        deposit_usd=50.0,
        deposit_required=True,
    )
    score = compute_bounty_score(finding, program)
    assert score.score_components.get("deposit_penalty") == 0.9


def test_fork_targets_reserve_and_polymarket():
    from night_shift_security.data.fork_targets import get_fork_targets

    ids = {t.target_id for t in get_fork_targets()}
    assert "beanstalk-governance-2022" in ids
    assert "polymarket-polygon-nomad-analogue" in ids
