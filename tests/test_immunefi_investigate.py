"""Tests for scan-driven investigation queue."""

from night_shift_security.immunefi.investigate import (
    build_investigation_config,
    pick_investigation_targets,
)

import night_shift_security.data.immunefi_registry as registry


def _program_by_slug(slug: str):
    for program in registry.IMMUNEFI_PROGRAMS:
        if program.slug == slug:
            return program
    return None


_SAMPLE_SCAN = {
    "programs": [
        {
            "slug": "raydium",
            "name": "Raydium",
            "ecosystem": "solana",
            "max_bounty_usd": 505_000,
            "best_evidence_grade": 4,
            "submission_ready": True,
            "solana_reproduced": 2,
            "candidates_passed": 5,
            "engine_ready": True,
        },
        {
            "slug": "kamino",
            "name": "Kamino",
            "ecosystem": "solana",
            "max_bounty_usd": 1_500_000,
            "best_evidence_grade": 3,
            "submission_ready": False,
            "solana_reproduced": 1,
            "candidates_passed": 3,
            "engine_ready": True,
        },
        {
            "slug": "beanstalk",
            "name": "Beanstalk",
            "ecosystem": "evm",
            "max_bounty_usd": 1_100_000,
            "best_evidence_grade": 4,
            "submission_ready": True,
            "solana_reproduced": 0,
            "candidates_passed": 4,
            "engine_ready": True,
        },
    ]
}


def test_pick_investigation_targets_solana_only():
    targets = pick_investigation_targets(_SAMPLE_SCAN, top_n=2, ecosystem="solana")
    assert len(targets) == 2
    assert targets[0]["slug"] == "raydium"
    assert targets[1]["slug"] == "kamino"


def test_pick_investigation_targets_min_grade():
    targets = pick_investigation_targets(
        _SAMPLE_SCAN, top_n=5, min_evidence_grade=4, ecosystem="solana"
    )
    assert len(targets) == 1
    assert targets[0]["slug"] == "raydium"


def test_pick_investigation_targets_exclude_slug():
    targets = pick_investigation_targets(
        _SAMPLE_SCAN,
        top_n=2,
        ecosystem="solana",
        exclude_slugs=["kamino"],
    )
    assert len(targets) == 1
    assert targets[0]["slug"] == "raydium"


def test_build_investigation_config_dynamic_target():
    program = _program_by_slug("orca")
    assert program is not None
    cfg = build_investigation_config(program)
    assert cfg["target"]["enabled"] is True
    assert cfg["target"]["target_id"] == "orca"
    assert cfg["target"]["exploit_id"] == "crema-finance-2022"
    assert "orca" in cfg["campaign"]["id"]
    assert cfg["templates"] == list(program.templates)