"""Tests for Immunefi registry and engine scan."""

import json
from pathlib import Path

from night_shift_security.data.immunefi_registry import (
    list_programs,
    program_to_live_target,
)
from night_shift_security.immunefi.scan import run_immunefi_scan, scan_program


def test_list_solana_programs():
    programs = list_programs(ecosystem="solana")
    slugs = {p.slug for p in programs}
    assert "orca" in slugs
    assert "kamino" in slugs
    assert "raydium" in slugs


def test_program_to_live_target_maps_analogue():
    program = list_programs(ecosystem="solana")[0]
    target = program_to_live_target(program)
    assert target.immunefi_program == program.slug
    assert target.templates


def test_scan_program_returns_metrics():
    from night_shift_security.config.loader import gates_from_config, load_config

    program = next(p for p in list_programs() if p.slug == "beanstalk")
    config = load_config()
    result = scan_program(program, config, __import__("night_shift_security.data.exploit_catalog", fromlist=["get_exploit_catalog"]).get_exploit_catalog(), gates_from_config(config))
    assert result["vectors_generated"] > 0
    assert "candidates_passed" in result


def test_run_immunefi_scan_writes_report(tmp_path: Path):
    report = run_immunefi_scan(
        min_max_bounty_usd=500_000,
        limit=3,
        output_dir=tmp_path,
    )
    assert report["curated_programs_scanned"] == 3
    assert Path(report["paths"]["json"]).exists()
    assert Path(report["paths"]["markdown"]).exists()
    payload = json.loads(Path(report["paths"]["json"]).read_text())
    assert payload["zero_rpc"] is True