"""Tests for zero-RPC shoestring submission export."""

import json
from pathlib import Path

from night_shift_security.data.schemas import (
    Finding,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.export.immunefi_submission import (
    generate_immunefi_markdown,
    generate_reproduction_script,
    resolve_exploit_id,
)
from night_shift_security.export.shoestring_submission import (
    export_shoestring_pack,
    select_best_submission,
    shoestring_evidence_grade,
)


def _crema_finding(**overrides) -> Finding:
    base = Finding(
        finding_id="NSS-0044",
        template_id="composability_risk",
        target_id="crema_finance",
        severity=Severity.HIGH,
        severity_score=0.41,
        economic_impact_usd=2_640_000.0,
        capital_required_usd=2_000_000.0,
        reproducibility=1.0,
        parameters={"protocol_hops": 3, "leverage_multiplier": 5.0, "use_callback_chain": True},
        invariant_violations=[
            InvariantViolation("isolated_protocol_risk", "bounded exposure", "3-hop chain", "desc"),
        ],
        reproduction_steps=[ReproductionStep("map_protocol_graph", "attacker", {"hops": 3})],
        mitigations=["Isolate collateral accounting"],
        evidence_grade=4,
        evidence_grade_label="root_cause_artifacts",
        solana_reproduced=True,
        solana_slot=140_000_000,
        solana_evidence={
            "exploit_id": "crema-finance-2022",
            "target_id": "crema-finance-2022",
            "slot": 140_000_000,
            "method": "solana_fixture",
            "impact_usd": 8_800_000.0,
        },
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_resolve_exploit_id_prefers_solana_anchor_over_rediscovery():
    finding = _crema_finding(rediscovered_exploit_id="harvest-finance-2020")
    assert resolve_exploit_id(finding) == "crema-finance-2022"


def test_markdown_includes_catalog_and_lab_sections():
    md = generate_immunefi_markdown(_crema_finding())
    assert "Crema Finance Flash Loan LP Drain" in md
    assert "## Lab vs Deployed Reality" in md
    assert "crema-finance-2022" in md
    assert "8,800,000" in md


def test_fixture_repro_script_has_zero_rpc_path():
    script = generate_reproduction_script(
        _crema_finding(),
        run_meta={"shoestring_mode": True},
    )
    assert "run_fixture_test.py" in script
    assert "SOLANA_EXPLOIT_ID=\"crema-finance-2022\"" in script
    assert "run_validator_test.sh" not in script


def test_shoestring_grade_credits_fixture_without_cpcv():
    finding = _crema_finding(evidence_grade=1)
    assert shoestring_evidence_grade(finding) == 4


def test_select_best_submission_prefers_fixture_grade4():
    fixture = _crema_finding()
    weaker = _crema_finding(finding_id="NSS-0001", evidence_grade=3, solana_evidence={"method": "catalog_solana"})
    best = select_best_submission([weaker, fixture])
    assert best is not None
    assert best.finding_id == "NSS-0044"


def test_markdown_frames_live_target_not_catalog_title():
    md = generate_immunefi_markdown(
        _crema_finding(),
        run_meta={
            "live_target": {
                "target_id": "kamino",
                "protocol_name": "Kamino",
                "immunefi_program": "kamino",
                "exploit_id": "mango-markets-2022",
            },
        },
    )
    assert "composability_risk — Kamino" in md
    assert "## Live Target Context" in md
    assert "**Protocol**: Kamino" in md
    assert "catalogue-analogue probe" in md
    assert "Crema Finance Flash Loan LP Drain" not in md.split("## Summary")[0]


def test_export_shoestring_pack_uses_live_target_slug(tmp_path: Path):
    result = export_shoestring_pack(
        [_crema_finding(evidence_grade=1)],
        {
            "run_at": "2026-06-09T00:00:00+00:00",
            "shoestring_mode": True,
            "live_target": {
                "target_id": "kamino",
                "immunefi_program": "kamino",
                "exploit_id": "mango-markets-2022",
            },
        },
        tmp_path,
    )
    assert "kamino" in result["pack_dir"]
    assert result["catalog_exploit_id"] == "crema-finance-2022"


def test_export_shoestring_pack(tmp_path: Path):
    result = export_shoestring_pack(
        [_crema_finding()],
        {"run_at": "2026-06-09T00:00:00+00:00", "shoestring_mode": True},
        tmp_path,
    )
    assert result["selected_finding_id"] == "NSS-0044"
    assert result["catalog_exploit_id"] == "crema-finance-2022"
    pack_dir = Path(result["pack_dir"])
    assert (pack_dir / "README.md").exists()
    assert (pack_dir / "NSS-0044.md").exists()
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    assert manifest["zero_rpc"] is True