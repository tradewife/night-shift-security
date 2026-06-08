"""Versioned hypothesis → template parameter mappings.

Each template defines semantic hypothesis parameters (ParameterSpace) that map to
the execution keys expected by attack_templates/. MAPPING_VERSION is stamped on
every AttackHypothesis.metadata for auditability.
"""

from __future__ import annotations

from typing import Any, Callable

MAPPING_VERSION = "1.0"

# Documented mapping registry: template_id → forward/reverse callables + field docs.
MAPPING_REGISTRY: dict[str, dict[str, Any]] = {
    "governance_capture": {
        "hypothesis_fields": [
            "quorum_threshold",
            "participation_rate",
            "whale_concentration",
            "proposal_timing_window_blocks",
            "flash_loan_boost",
        ],
        "template_fields": ["voting_power_pct", "use_flash_loan", "bypass_timelock"],
        "rules": (
            "voting_power_pct = min(100, whale_concentration * participation_rate * 100); "
            "bypass_timelock = proposal_timing_window_blocks < 500 OR quorum_threshold < 0.15; "
            "use_flash_loan = whale_concentration < 0.35 AND participation_rate < 0.5"
        ),
    },
    "treasury_drain": {
        "hypothesis_fields": [
            "drain_fraction",
            "admin_compromise_likelihood",
            "multisig_weakness",
            "withdrawal_velocity",
        ],
        "template_fields": ["withdrawal_pct", "use_compromised_admin", "bypass_multisig"],
        "rules": (
            "withdrawal_pct = drain_fraction * 100; "
            "use_compromised_admin = admin_compromise_likelihood >= 0.5; "
            "bypass_multisig = multisig_weakness >= 0.6"
        ),
    },
    "flash_loan_oracle": {
        "hypothesis_fields": [
            "loan_fraction_of_ceiling",
            "price_skew_severity",
            "oracle_dependency_score",
        ],
        "template_fields": ["loan_amount_usd", "price_manipulation_pct", "use_single_oracle"],
        "rules": (
            "loan_amount_usd = loan_fraction_of_ceiling * 50_000_000; "
            "price_manipulation_pct = price_skew_severity * 50; "
            "use_single_oracle = oracle_dependency_score >= 0.55"
        ),
    },
    "reentrancy": {
        "hypothesis_fields": [
            "recursion_intensity",
            "callback_exploitability",
            "target_function_preference",
        ],
        "template_fields": ["recursion_depth", "target_function"],
        "rules": (
            "recursion_depth = round(2 + recursion_intensity * 13); "
            "target_function = target_function_preference (choice)"
        ),
    },
    "composability_risk": {
        "hypothesis_fields": [
            "chain_depth",
            "leverage_intensity",
            "callback_chain_likelihood",
        ],
        "template_fields": ["protocol_hops", "leverage_multiplier", "use_callback_chain"],
        "rules": (
            "protocol_hops = round(2 + chain_depth * 3); "
            "leverage_multiplier = 1.5 + leverage_intensity * 10.5; "
            "use_callback_chain = callback_chain_likelihood >= 0.5"
        ),
    },
    "upgradeability_risk": {
        "hypothesis_fields": [
            "upgrade_exploitability",
            "storage_collision_score",
            "initializer_gap_score",
            "upgrade_vector",
        ],
        "template_fields": ["upgrade_method", "storage_collision", "skip_initializer"],
        "rules": (
            "upgrade_method selected from upgrade_vector choice by exploitability tier; "
            "storage_collision = storage_collision_score >= 0.5; "
            "skip_initializer = initializer_gap_score >= 0.5"
        ),
    },
    "access_control_escalation": {
        "hypothesis_fields": [
            "privilege_escalation_pressure",
            "role_bypass_severity",
            "zero_root_exploitability",
            "target_role_preference",
        ],
        "template_fields": ["target_role", "bypass_role_check", "use_zero_root"],
        "rules": (
            "target_role = target_role_preference (choice); "
            "bypass_role_check = role_bypass_severity >= 0.5; "
            "use_zero_root = zero_root_exploitability >= 0.5"
        ),
    },
}


def get_mapping_version(template_id: str) -> str:
    if template_id not in MAPPING_REGISTRY:
        raise KeyError(f"No mapping registered for template: {template_id}")
    return MAPPING_VERSION


def hypothesis_to_template_params(template_id: str, params: dict[str, Any]) -> dict[str, Any]:
    mapper = _FORWARD_MAPPERS.get(template_id)
    if mapper is None:
        raise KeyError(f"No forward mapping for template: {template_id}")
    return mapper(params)


def template_to_hypothesis_params(template_id: str, params: dict[str, Any]) -> dict[str, Any]:
    mapper = _REVERSE_MAPPERS.get(template_id)
    if mapper is None:
        raise KeyError(f"No reverse mapping for template: {template_id}")
    return mapper(params)


def _governance_forward(params: dict[str, Any]) -> dict[str, Any]:
    whale = float(params["whale_concentration"])
    participation = float(params["participation_rate"])
    voting_power_pct = round(min(100.0, whale * participation * 100.0), 4)
    timing_blocks = int(params["proposal_timing_window_blocks"])
    bypass_timelock = timing_blocks < 500 or float(params["quorum_threshold"]) < 0.15
    use_flash_loan = whale < 0.35 and participation < 0.5
    return {
        "voting_power_pct": voting_power_pct,
        "use_flash_loan": use_flash_loan,
        "bypass_timelock": bypass_timelock,
    }


def _governance_reverse(params: dict[str, Any]) -> dict[str, Any]:
    voting = float(params.get("voting_power_pct", 0.0))
    use_flash = bool(params.get("use_flash_loan", False))
    bypass = bool(params.get("bypass_timelock", False))
    return {
        "quorum_threshold": round(min(0.40, max(0.05, voting / 100.0)), 4),
        "participation_rate": round(min(0.90, max(0.10, voting / 67.0)), 4),
        "whale_concentration": round(min(0.85, max(0.20, voting / 60.0)), 4),
        "proposal_timing_window_blocks": 250 if bypass else 2000,
        "flash_loan_boost": 0.30 if use_flash else 0.0,
    }


def _treasury_forward(params: dict[str, Any]) -> dict[str, Any]:
    drain_fraction = float(params["drain_fraction"])
    return {
        "withdrawal_pct": round(drain_fraction * 100.0, 4),
        "use_compromised_admin": float(params["admin_compromise_likelihood"]) >= 0.5,
        "bypass_multisig": float(params["multisig_weakness"]) >= 0.6,
    }


def _treasury_reverse(params: dict[str, Any]) -> dict[str, Any]:
    withdrawal = float(params.get("withdrawal_pct", 50.0))
    use_admin = bool(params.get("use_compromised_admin", False))
    bypass = bool(params.get("bypass_multisig", False))
    return {
        "drain_fraction": round(withdrawal / 100.0, 4),
        "admin_compromise_likelihood": 0.8 if use_admin else 0.2,
        "multisig_weakness": 0.75 if bypass else 0.25,
        "withdrawal_velocity": round(withdrawal / 100.0, 4),
    }


def _flash_loan_forward(params: dict[str, Any]) -> dict[str, Any]:
    loan_fraction = float(params["loan_fraction_of_ceiling"])
    skew = float(params["price_skew_severity"])
    oracle_dep = float(params["oracle_dependency_score"])
    return {
        "loan_amount_usd": int(round(loan_fraction * 50_000_000)),
        "price_manipulation_pct": round(skew * 50.0, 4),
        "use_single_oracle": oracle_dep >= 0.55,
    }


def _flash_loan_reverse(params: dict[str, Any]) -> dict[str, Any]:
    loan = float(params.get("loan_amount_usd", 5_000_000))
    manipulation = float(params.get("price_manipulation_pct", 25.0))
    single = bool(params.get("use_single_oracle", False))
    return {
        "loan_fraction_of_ceiling": round(min(1.0, max(0.02, loan / 50_000_000)), 4),
        "price_skew_severity": round(min(2.0, max(0.1, manipulation / 50.0)), 4),
        "oracle_dependency_score": 0.75 if single else 0.35,
    }


def _reentrancy_forward(params: dict[str, Any]) -> dict[str, Any]:
    intensity = float(params["recursion_intensity"])
    return {
        "recursion_depth": max(2, min(15, round(2 + intensity * 13))),
        "target_function": params["target_function_preference"],
    }


def _reentrancy_reverse(params: dict[str, Any]) -> dict[str, Any]:
    depth = int(params.get("recursion_depth", 3))
    target = params.get("target_function", "withdraw")
    return {
        "recursion_intensity": round(min(1.0, max(0.0, (depth - 2) / 13.0)), 4),
        "callback_exploitability": round(min(1.0, depth / 10.0), 4),
        "target_function_preference": target,
    }


def _composability_forward(params: dict[str, Any]) -> dict[str, Any]:
    depth = float(params["chain_depth"])
    leverage = float(params["leverage_intensity"])
    callback = float(params["callback_chain_likelihood"])
    return {
        "protocol_hops": max(2, min(5, round(2 + depth * 3))),
        "leverage_multiplier": round(1.5 + leverage * 10.5, 4),
        "use_callback_chain": callback >= 0.5,
    }


def _composability_reverse(params: dict[str, Any]) -> dict[str, Any]:
    hops = int(params.get("protocol_hops", 3))
    leverage = float(params.get("leverage_multiplier", 5.0))
    callbacks = bool(params.get("use_callback_chain", False))
    return {
        "chain_depth": round(min(1.0, max(0.0, (hops - 2) / 3.0)), 4),
        "leverage_intensity": round(min(1.0, max(0.0, (leverage - 1.5) / 10.5)), 4),
        "callback_chain_likelihood": 0.75 if callbacks else 0.25,
    }


_UPGRADE_METHODS = ("direct_admin", "storage_collision", "uninitialized_proxy")


def _upgrade_forward(params: dict[str, Any]) -> dict[str, Any]:
    exploitability = float(params["upgrade_exploitability"])
    vector = params["upgrade_vector"]
    if exploitability >= 0.66:
        method = vector
    elif exploitability >= 0.33:
        method = vector if vector != "uninitialized_proxy" else "storage_collision"
    else:
        method = "direct_admin"
    return {
        "upgrade_method": method,
        "storage_collision": float(params["storage_collision_score"]) >= 0.5,
        "skip_initializer": float(params["initializer_gap_score"]) >= 0.5,
    }


def _upgrade_reverse(params: dict[str, Any]) -> dict[str, Any]:
    method = params.get("upgrade_method", "direct_admin")
    collision = bool(params.get("storage_collision", False))
    skip_init = bool(params.get("skip_initializer", False))
    exploitability = {
        "direct_admin": 0.4,
        "storage_collision": 0.7,
        "uninitialized_proxy": 0.85,
    }.get(method, 0.5)
    return {
        "upgrade_exploitability": exploitability,
        "storage_collision_score": 0.75 if collision else 0.25,
        "initializer_gap_score": 0.75 if skip_init else 0.25,
        "upgrade_vector": method if method in _UPGRADE_METHODS else "direct_admin",
    }


def _access_control_forward(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_role": params["target_role_preference"],
        "bypass_role_check": float(params["role_bypass_severity"]) >= 0.5,
        "use_zero_root": float(params["zero_root_exploitability"]) >= 0.5,
    }


def _access_control_reverse(params: dict[str, Any]) -> dict[str, Any]:
    role = params.get("target_role", "admin")
    bypass = bool(params.get("bypass_role_check", False))
    zero_root = bool(params.get("use_zero_root", False))
    return {
        "privilege_escalation_pressure": 0.7 if bypass else 0.3,
        "role_bypass_severity": 0.75 if bypass else 0.25,
        "zero_root_exploitability": 0.75 if zero_root else 0.25,
        "target_role_preference": role,
    }


_FORWARD_MAPPERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "governance_capture": _governance_forward,
    "treasury_drain": _treasury_forward,
    "flash_loan_oracle": _flash_loan_forward,
    "reentrancy": _reentrancy_forward,
    "composability_risk": _composability_forward,
    "upgradeability_risk": _upgrade_forward,
    "access_control_escalation": _access_control_forward,
}

_REVERSE_MAPPERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "governance_capture": _governance_reverse,
    "treasury_drain": _treasury_reverse,
    "flash_loan_oracle": _flash_loan_reverse,
    "reentrancy": _reentrancy_reverse,
    "composability_risk": _composability_reverse,
    "upgradeability_risk": _upgrade_reverse,
    "access_control_escalation": _access_control_reverse,
}