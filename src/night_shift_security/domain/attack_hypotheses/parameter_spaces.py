"""Declarative parameter spaces for all seven attack templates."""

from typing import Any

ParameterSpace = dict[str, dict[str, Any]]

GOVERNANCE_CAPTURE_SPACE: ParameterSpace = {
    "quorum_threshold": {
        "type": "float",
        "range": [0.05, 0.40],
        "distribution": "uniform",
    },
    "participation_rate": {
        "type": "float",
        "range": [0.10, 0.90],
        "distribution": "uniform",
    },
    "whale_concentration": {
        "type": "float",
        "range": [0.20, 0.85],
        "distribution": "uniform",
    },
    "proposal_timing_window_blocks": {
        "type": "int",
        "range": [100, 5000],
    },
    "flash_loan_boost": {
        "type": "float",
        "range": [0.0, 0.35],
        "distribution": "uniform",
    },
}

TREASURY_DRAIN_SPACE: ParameterSpace = {
    "drain_fraction": {
        "type": "float",
        "range": [0.25, 1.0],
        "distribution": "uniform",
    },
    "admin_compromise_likelihood": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "multisig_weakness": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "withdrawal_velocity": {
        "type": "float",
        "range": [0.10, 1.0],
        "distribution": "uniform",
    },
}

FLASH_LOAN_ORACLE_SPACE: ParameterSpace = {
    "loan_fraction_of_ceiling": {
        "type": "float",
        "range": [0.02, 1.0],
        "distribution": "uniform",
    },
    "price_skew_severity": {
        "type": "float",
        "range": [0.1, 2.0],
        "distribution": "uniform",
    },
    "oracle_dependency_score": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
}

REENTRANCY_SPACE: ParameterSpace = {
    "recursion_intensity": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "callback_exploitability": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "target_function_preference": {
        "type": "choice",
        "choices": ["withdraw", "claim", "redeem"],
    },
}

COMPOSABILITY_RISK_SPACE: ParameterSpace = {
    "chain_depth": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "leverage_intensity": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "callback_chain_likelihood": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
}

UPGRADEABILITY_RISK_SPACE: ParameterSpace = {
    "upgrade_exploitability": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "storage_collision_score": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "initializer_gap_score": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "upgrade_vector": {
        "type": "choice",
        "choices": ["direct_admin", "storage_collision", "uninitialized_proxy"],
    },
}

ACCESS_CONTROL_ESCALATION_SPACE: ParameterSpace = {
    "privilege_escalation_pressure": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "role_bypass_severity": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "zero_root_exploitability": {
        "type": "float",
        "range": [0.0, 1.0],
        "distribution": "uniform",
    },
    "target_role_preference": {
        "type": "choice",
        "choices": ["owner", "admin", "minter", "pauser"],
    },
}

ALL_PARAMETER_SPACES: dict[str, ParameterSpace] = {
    "governance_capture": GOVERNANCE_CAPTURE_SPACE,
    "treasury_drain": TREASURY_DRAIN_SPACE,
    "flash_loan_oracle": FLASH_LOAN_ORACLE_SPACE,
    "reentrancy": REENTRANCY_SPACE,
    "composability_risk": COMPOSABILITY_RISK_SPACE,
    "upgradeability_risk": UPGRADEABILITY_RISK_SPACE,
    "access_control_escalation": ACCESS_CONTROL_ESCALATION_SPACE,
}