"""Tests for live-target configuration and harness."""

import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401

from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.target_harness import evaluate_target_vectors, generate_target_vectors
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.target_config import (
    load_live_target,
    resolve_target_exploit,
    resolve_target_states,
    target_summary,
)


def test_load_live_target_from_config_path():
    config = load_config()
    config["target"] = {
        "enabled": True,
        "config_path": "targets/solend-whale-2022.json",
    }
    target = load_live_target(config)
    assert target is not None
    assert target.target_id == "solend-whale-2022"
    assert target.chain == "solana"
    assert "governance_capture" in target.templates


def test_resolve_target_states_uses_catalog_exploit():
    config = load_config()
    config["target"] = {
        "enabled": True,
        "config_path": "targets/cashio-2022.json",
    }
    target = load_live_target(config)
    assert target is not None
    exploit = resolve_target_exploit(target, get_exploit_catalog())
    assert exploit is not None
    states = resolve_target_states(target, get_exploit_catalog())
    assert len(states) == 1
    assert states[0].protocol_id == target.target_id


def test_target_harness_generates_scoped_vectors():
    config = load_config()
    config["target"] = {
        "enabled": True,
        "config_path": "targets/solend-whale-2022.json",
    }
    target = load_live_target(config)
    assert target is not None
    vectors = generate_target_vectors(target, config)
    assert vectors
    assert all(v.target_id == target.target_id for v in vectors)
    assert all(v.template_id in target.templates for v in vectors)


def test_load_kamino_target():
    config = load_config()
    config["target"] = {
        "enabled": True,
        "config_path": "targets/kamino.json",
    }
    target = load_live_target(config)
    assert target is not None
    assert target.target_id == "kamino"
    assert target.immunefi_program == "kamino"
    assert target.exploit_id == "mango-markets-2022"
    assert "flash_loan_oracle" in target.templates
    assert target.program_id.startswith("KLend")


def test_target_harness_evaluates_candidates():
    config = load_config()
    config["target"] = {
        "enabled": True,
        "config_path": "targets/solend-whale-2022.json",
    }
    target = load_live_target(config)
    gates = gates_from_config(config)
    vectors = generate_target_vectors(target, config)
    candidates = evaluate_target_vectors(target, vectors[:5], gates, get_exploit_catalog())
    assert len(candidates) == 5
    assert target_summary(target)["target_id"] == "solend-whale-2022"