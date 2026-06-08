"""Lightweight ranking signals for hypothesis prioritization."""

from __future__ import annotations

from typing import Any

from night_shift_security.data.schemas import AttackVector

_TEMPLATE_EVIDENCE_WEIGHTS: dict[str, float] = {
    "governance_capture": 0.85,
    "treasury_drain": 0.90,
    "flash_loan_oracle": 0.88,
    "reentrancy": 0.75,
    "composability_risk": 0.80,
    "upgradeability_risk": 0.82,
    "access_control_escalation": 0.78,
}

_GRID_CENTROIDS: dict[str, dict[str, float]] = {
    "governance_capture": {
        "voting_power_pct": 40.0,
        "use_flash_loan": 0.5,
        "bypass_timelock": 0.5,
    },
    "treasury_drain": {
        "withdrawal_pct": 62.5,
        "use_compromised_admin": 0.5,
        "bypass_multisig": 0.5,
    },
    "flash_loan_oracle": {
        "loan_amount_usd": 25_000_000.0,
        "price_manipulation_pct": 50.0,
        "use_single_oracle": 0.5,
    },
    "reentrancy": {
        "recursion_depth": 8.0,
        "target_function": 1.0,
    },
    "composability_risk": {
        "protocol_hops": 3.5,
        "leverage_multiplier": 6.0,
        "use_callback_chain": 0.5,
    },
    "upgradeability_risk": {
        "upgrade_method": 1.0,
        "storage_collision": 0.5,
        "skip_initializer": 0.5,
    },
    "access_control_escalation": {
        "target_role": 1.0,
        "bypass_role_check": 0.5,
        "use_zero_root": 0.5,
    },
}

_TARGET_FUNCTION_INDEX = {"withdraw": 0.0, "claim": 1.0, "redeem": 2.0}
_ROLE_INDEX = {"owner": 0.0, "admin": 1.0, "minter": 2.0, "pauser": 3.0}
_UPGRADE_METHOD_INDEX = {
    "direct_admin": 0.0,
    "storage_collision": 1.0,
    "uninitialized_proxy": 2.0,
}


def _bool_as_float(value: Any) -> float:
    return 1.0 if bool(value) else 0.0


def _choice_as_float(template_id: str, key: str, value: Any) -> float:
    if key == "target_function":
        return _TARGET_FUNCTION_INDEX.get(str(value), 1.0) / 2.0
    if key == "target_role":
        return _ROLE_INDEX.get(str(value), 1.0) / 3.0
    if key in ("upgrade_vector", "upgrade_method"):
        return _UPGRADE_METHOD_INDEX.get(str(value), 1.0) / 2.0
    return 0.5


def _numeric_deviation(value: float, centroid: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return min(1.0, abs(value - centroid) / scale)


def compute_impact_proxy(template_id: str, parameters: dict[str, Any]) -> float:
    """Heuristic economic/governance impact potential from template parameters."""
    if template_id == "governance_capture":
        voting = float(parameters.get("voting_power_pct", 0.0))
        flash = 0.15 if parameters.get("use_flash_loan") else 0.0
        timelock = 0.10 if parameters.get("bypass_timelock") else 0.0
        return min(1.0, voting / 100.0 + flash + timelock)
    if template_id == "treasury_drain":
        return min(1.0, float(parameters.get("withdrawal_pct", 0.0)) / 100.0)
    if template_id == "flash_loan_oracle":
        loan = float(parameters.get("loan_amount_usd", 0.0))
        skew = float(parameters.get("price_manipulation_pct", 0.0))
        return min(1.0, (loan / 50_000_000.0) * 0.7 + (skew / 100.0) * 0.3)
    if template_id == "reentrancy":
        depth = float(parameters.get("recursion_depth", 1.0))
        return min(1.0, depth / 15.0)
    if template_id == "composability_risk":
        hops = float(parameters.get("protocol_hops", 1.0))
        leverage = float(parameters.get("leverage_multiplier", 1.0))
        return min(1.0, (hops / 5.0) * 0.5 + (leverage / 12.0) * 0.5)
    if template_id == "upgradeability_risk":
        method = str(parameters.get("upgrade_method", ""))
        base = _UPGRADE_METHOD_INDEX.get(method, 1.0) / 2.0
        collision = 0.2 if parameters.get("storage_collision") else 0.0
        initializer = 0.2 if parameters.get("skip_initializer") else 0.0
        return min(1.0, base * 0.6 + collision + initializer)
    if template_id == "access_control_escalation":
        role = str(parameters.get("target_role", "admin"))
        zero_root = 0.25 if parameters.get("use_zero_root") else 0.0
        bypass = 0.15 if parameters.get("bypass_role_check") else 0.0
        return min(1.0, _ROLE_INDEX.get(role, 1.0) / 3.0 + zero_root + bypass)
    return 0.5


def compute_novelty_score(template_id: str, parameters: dict[str, Any]) -> float:
    """Deviation from template centroid — higher means less obvious / more novel."""
    centroids = _GRID_CENTROIDS.get(template_id, {})
    if not centroids:
        return 0.5

    deviations: list[float] = []
    for key, centroid in centroids.items():
        if key not in parameters:
            continue
        value = parameters[key]
        if isinstance(value, bool):
            deviations.append(_numeric_deviation(_bool_as_float(value), centroid, 1.0))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            scale = max(abs(centroid), 1.0)
            deviations.append(_numeric_deviation(float(value), float(centroid), scale))
        else:
            deviations.append(
                _numeric_deviation(_choice_as_float(template_id, key, value), centroid, 1.0)
            )

    if not deviations:
        return 0.5
    return round(sum(deviations) / len(deviations), 4)


def compute_testability_score(template_id: str, parameters: dict[str, Any]) -> float:
    """How straightforward this vector is to evaluate in simulation."""
    required_keys = list(_GRID_CENTROIDS.get(template_id, {}).keys())
    if not required_keys:
        return 0.5

    present = sum(1 for key in required_keys if key in parameters)
    completeness = present / len(required_keys)
    impact = compute_impact_proxy(template_id, parameters)
    # Moderate-impact vectors are easiest to interpret in rapid validation.
    moderation = 1.0 - abs(impact - 0.55) * 1.2
    return round(max(0.0, min(1.0, completeness * 0.6 + moderation * 0.4)), 4)


def compute_evidence_potential(
    template_id: str,
    parameters: dict[str, Any],
    *,
    impact: float | None = None,
    novelty: float | None = None,
) -> float:
    """Heuristic likelihood of reaching higher evidence grades."""
    impact_score = impact if impact is not None else compute_impact_proxy(template_id, parameters)
    novelty_score = novelty if novelty is not None else compute_novelty_score(template_id, parameters)
    template_weight = _TEMPLATE_EVIDENCE_WEIGHTS.get(template_id, 0.5)
    return round(
        min(1.0, template_weight * 0.45 + impact_score * 0.35 + novelty_score * 0.20),
        4,
    )


def compute_priority_score(
    impact: float,
    novelty: float,
    testability: float,
) -> float:
    return round(0.40 * impact + 0.35 * novelty + 0.25 * testability, 4)


def ranking_signals_for_vector(vector: AttackVector) -> dict[str, float]:
    """Compute all ranking signals for an attack vector."""
    impact = compute_impact_proxy(vector.template_id, vector.parameters)
    novelty = compute_novelty_score(vector.template_id, vector.parameters)
    testability = compute_testability_score(vector.template_id, vector.parameters)
    evidence_potential = compute_evidence_potential(
        vector.template_id,
        vector.parameters,
        impact=impact,
        novelty=novelty,
    )
    priority = compute_priority_score(impact, novelty, testability)
    return {
        "impact_proxy": impact,
        "novelty_score": novelty,
        "testability_score": testability,
        "evidence_potential": evidence_potential,
        "priority_score": priority,
    }


def attach_ranking_signals(vector: AttackVector) -> AttackVector:
    """Attach ranking metadata to a vector (idempotent)."""
    metadata = dict(vector.metadata or {})
    if "priority_score" in metadata:
        return vector
    metadata.update(ranking_signals_for_vector(vector))
    return AttackVector(
        template_id=vector.template_id,
        parameters=vector.parameters,
        target_id=vector.target_id,
        label=vector.label,
        metadata=metadata,
    )