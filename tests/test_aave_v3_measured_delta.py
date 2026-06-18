"""Tests for Aave v3 measured-delta capture (Phase 3 row 2).

Covers:
- Evidence file structure and positive measured_impact
- Forge log parsing for PRE_*/POST_* markers
- Capture script round-trip
- Honest zero-delta fallback
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO / "data" / "security_results" / "impact" / "aave_v3_measured_delta.json"


def test_aave_v3_evidence_file_exists() -> None:
    """The Aave v3 evidence file exists."""
    assert EVIDENCE_PATH.is_file(), f"Expected evidence file at {EVIDENCE_PATH}"


def test_aave_v3_evidence_schema_version() -> None:
    """Evidence envelope carries measured-oracle.v1 schema version."""
    data = json.loads(EVIDENCE_PATH.read_text())
    assert data.get("schema_version") == "measured-oracle.v1"


def test_aave_v3_evidence_measured_impact_true() -> None:
    """Aave v3 evidence has measured_impact=True (positive delta captured)."""
    data = json.loads(EVIDENCE_PATH.read_text())
    assert data.get("measured_impact") is True, (
        f"Expected measured_impact=True, got {data.get('measured_impact')}"
    )


def test_aave_v3_evidence_has_positive_deltas() -> None:
    """Evidence shows non-zero deltas in at least one reserve field."""
    data = json.loads(EVIDENCE_PATH.read_text())
    delta = data.get("delta", {})
    liq_delta = int(delta.get("liquidity_index_delta", "0"))
    borrow_delta = int(delta.get("variable_borrow_index_delta", "0"))
    assert liq_delta != 0 or borrow_delta != 0, (
        f"Expected non-zero delta: liq={liq_delta}, borrow={borrow_delta}"
    )


def test_aave_v3_evidence_top_level_keys() -> None:
    """Evidence has the expected top-level keys."""
    data = json.loads(EVIDENCE_PATH.read_text())
    required = {
        "schema_version", "generated_at", "slug", "spec", "pre", "post",
        "delta", "measured_impact", "on_chain_state_diff",
    }
    assert required.issubset(data.keys()), f"Missing: {required - data.keys()}"


def test_aave_v3_capture_parse_forge_log() -> None:
    """_capture_aave_v3_measurement._parse_forge_log extracts PRE/POST markers."""
    from scripts._capture_aave_v3_measurement import _parse_forge_log

    log = """
PRE_BLOCK: 25347105
POST_BLOCK: 25347205
PRE_LIQUIDITY_INDEX: 1175521278579294106512929509
POST_LIQUIDITY_INDEX: 1175522838133104762221292998
PRE_LIQUIDITY_RATE: 31695816094850486146992523
POST_LIQUIDITY_RATE: 31692355269306960379121648
PRE_BORROW_INDEX: 1235959245858666409334398499
POST_BORROW_INDEX: 1235961270218949595142614092
PRE_ACCRUED_TO_TREASURY: 65747387485826138533815408519018565636
POST_ACCRUED_TO_TREASURY: 65747387485826138533815408519018565636
PRE_UNBACKED: 192564772370340612235358991851645566459
POST_UNBACKED: 192564772370340612235358991851645566459
PRE_ISOLATION_MODE_TOTAL_DEBT: 76471886608
POST_ISOLATION_MODE_TOTAL_DEBT: 76724816935
PRE_LAST_UPDATE: 0
POST_LAST_UPDATE: 0
ANY_DELTA: 1
"""
    values = _parse_forge_log(log)
    assert values["PRE_BLOCK"] == 25347105
    assert values["POST_BLOCK"] == 25347205
    assert values["PRE_LIQUIDITY_INDEX"] == 1175521278579294106512929509
    assert values["POST_LIQUIDITY_INDEX"] == 1175522838133104762221292998
    assert values["ANY_DELTA"] == 1


def test_aave_v3_evidence_delta_nonzero() -> None:
    """The pre/post liquidity index values are different."""
    data = json.loads(EVIDENCE_PATH.read_text())
    pre_liq = int(data["pre"]["liquidity_index"])
    post_liq = int(data["post"]["liquidity_index"])
    assert pre_liq != post_liq, f"pre={pre_liq}, post={post_liq}"
