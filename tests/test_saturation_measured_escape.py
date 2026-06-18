"""Audit correction C4 — measured-delta escape valve for catalogue-only saturation."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.bounty.native_picker import has_measured_delta
from night_shift_security.orchestration import bounty_loop as bl


def _write_impact(
    path: Path,
    *,
    slug: str,
    slot0_delta: str = "0",
    token_delta: str = "0",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "delta": {
            "tokens": [{
                "token": "0xUSDC",
                "holder": "0xAttacker",
                "delta_raw_units": token_delta,
                "decimals": 6,
            }],
            "pool_slots": [{
                "pool_id": "0xPool",
                "sqrt_price_x96_pre": "0",
                "sqrt_price_x96_post": slot0_delta,
                "sqrt_price_x96_delta": slot0_delta,
            }],
        },
        "measured_impact": False,
    }
    path.write_text(json.dumps(payload))
    return path


def test_has_measured_delta_returns_false_when_evidence_missing(tmp_path: Path):
    # No impact/<slug>_measured_delta.json and no concrete_candidates.jsonl.
    assert has_measured_delta(
        "uniswap_v4",
        knowledge_path=tmp_path / "missing.jsonl",
        impact_path=tmp_path / "missing_impact.json",
    ) is False


def test_has_measured_delta_returns_true_on_slot0(tmp_path: Path):
    impact_path = tmp_path / "impact" / "uniswap_v4_measured_delta.json"
    _write_impact(
        impact_path, slug="uniswap_v4",
        slot0_delta="79228162514264337593543950336",  # 2**96
    )
    assert has_measured_delta("uniswap_v4", impact_path=impact_path) is True


def test_has_measured_delta_returns_true_on_token_delta(tmp_path: Path):
    impact_path = tmp_path / "impact" / "kamino_measured_delta.json"
    _write_impact(
        impact_path, slug="kamino",
        token_delta="5000000",  # 5 USDC
    )
    assert has_measured_delta("kamino", impact_path=impact_path) is True


def test_has_measured_delta_returns_false_on_zero_everywhere(tmp_path: Path):
    impact_path = tmp_path / "impact" / "kamino_measured_delta.json"
    _write_impact(
        impact_path, slug="kamino",
        slot0_delta="0", token_delta="0",
    )
    assert has_measured_delta("kamino", impact_path=impact_path) is False


def test_maybe_mark_saturated_catalogue_only_without_measured_delta(tmp_path: Path):
    """Path 1 — catalogue-only findings + no measured-delta escape -> saturated."""
    state: dict = {"saturated_slugs": ["kamino"]}
    evaluation = {
        "scored": [
            {"catalog_analogue": True, "submission_recommendation": "shoestring_only"},
        ],
        "submit_candidates": [],
        "best_recommendation": "shoestring_only",
    }
    bl._maybe_mark_saturated(
        state, "raydium", evaluation,
    )
    assert "raydium" in state["saturated_slugs"]


def test_maybe_mark_saturated_catalogue_only_with_measured_delta_escapes(tmp_path: Path):
    """Path 2 (audit C4) — catalogue-only findings + positive measured-delta
    evidence wins the escape and the slug does NOT saturate."""
    impact_path = tmp_path / "impact" / "uniswap_v4_measured_delta.json"
    _write_impact(
        impact_path, slug="uniswap_v4",
        slot0_delta="79228162514264337593543950336",
    )
    state: dict = {"saturated_slugs": ["kamino"]}
    evaluation = {
        "scored": [
            {"catalog_analogue": True, "submission_recommendation": "shoestring_only"},
        ],
        "submit_candidates": [],
        "best_recommendation": "shoestring_only",
    }
    bl._maybe_mark_saturated(
        state, "uniswap_v4", evaluation,
    )
    assert "uniswap_v4" not in state["saturated_slugs"]


def test_maybe_mark_saturated_keeps_unsaturated_when_submit_ready(tmp_path: Path):
    state: dict = {"saturated_slugs": []}
    evaluation = {
        "scored": [
            {"catalog_analogue": True, "submission_recommendation": "submit_now"},
        ],
        "submit_candidates": [{"finding_id": "x"}],
        "best_recommendation": "submit_now",
    }
    bl._maybe_mark_saturated(state, "wormhole", evaluation)
    assert "wormhole" not in state["saturated_slugs"]
