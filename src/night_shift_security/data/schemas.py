"""Core data types for attack vectors, results, and findings."""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _hashable_param_value(value: Any) -> Any:
    """Normalize parameter values so vector keys can be stored in sets."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    if isinstance(value, tuple):
        return json.dumps(list(value), sort_keys=True, default=str)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def attack_vector_key(
    template_id: str,
    target_id: str,
    parameters: dict[str, Any],
) -> tuple:
    items = tuple(
        sorted((k, _hashable_param_value(v)) for k, v in parameters.items())
    )
    return (template_id, target_id, items)


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackVector:
    """A parameterized attack hypothesis to evaluate."""

    template_id: str
    parameters: dict[str, Any]
    target_id: str = ""
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple:
        return attack_vector_key(self.template_id, self.target_id, self.parameters)


@dataclass
class InvariantViolation:
    """A broken protocol invariant."""

    invariant_id: str
    description: str
    expected: str
    actual: str


@dataclass
class ReproductionStep:
    """One step in an attack reproduction sequence."""

    action: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttackResult:
    """Outcome of executing an attack vector against a target state."""

    vector: AttackVector
    success: bool
    severity: Severity
    economic_impact_usd: float
    invariant_violations: list[InvariantViolation] = field(default_factory=list)
    reproduction_steps: list[ReproductionStep] = field(default_factory=list)
    capital_required_usd: float = 0.0
    notes: str = ""


@dataclass
class ContractState:
    """Simplified on-chain state for mock simulation."""

    protocol_id: str
    treasury_balance_usd: float = 0.0
    total_voting_power: float = 0.0
    attacker_voting_power: float = 0.0
    proposal_threshold_pct: float = 100.0
    timelock_hours: float = 48.0
    execution_delay_hours: float = 24.0
    quorum_pct: float = 100.0
    flash_loan_available: bool = False
    oracle_manipulable: bool = False
    reentrancy_guard: bool = True
    admin_role_compromised: bool = False
    withdrawal_limit_usd: float = 0.0
    multisig_threshold: int = 1
    collateral_liquidity_usd: float = 0.0
    oracle_price_usd: float = 1.0
    true_price_usd: float = 1.0
    max_flash_loan_usd: float = 0.0
    external_call_before_state_update: bool = False
    callback_enabled: bool = False
    cross_protocol_enabled: bool = False
    shared_liquidity_usd: float = 0.0
    collateral_dependency_count: int = 0
    upgradeable_proxy: bool = False
    proxy_admin_unprotected: bool = False
    proxy_initialized: bool = True
    storage_collision_risk: bool = False
    privileged_function_exposed: bool = False
    zero_root_vulnerable: bool = False
    role_hierarchy_bypass: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExploitRecord:
    """Ground-truth historical exploit for rediscovery validation."""

    exploit_id: str
    name: str
    protocol: str
    year: int
    category: str
    template_id: str
    known_parameters: dict[str, Any]
    state: ContractState
    expected_severity: Severity
    loss_usd: float
    description: str = ""


@dataclass
class AttackCandidateResult:
    """Aggregated evaluation of one attack vector (mirrors RTP CandidateResult)."""

    vector: AttackVector
    success_rate: float
    mean_severity_score: float
    mean_economic_impact_usd: float
    reproducibility: float
    generality: float
    realism_score: float
    invariant_violation_count: int
    severity_score: float
    rejected: bool = False
    rejection_reason: str = ""
    replay_matches: int = 0
    replay_total: int = 0
    mc_reproducibility: float = 0.0
    mc_impact_p50_usd: float = 0.0
    mc_impact_p95_usd: float = 0.0
    mc_simulations: int = 0
    foundry_confirmed: bool = False
    fork_confirmed: bool = False
    fork_reproduced: bool = False
    fork_target_id: str = ""
    fork_block_number: int = 0
    fork_evidence: dict[str, Any] = field(default_factory=dict)
    solana_confirmed: bool = False
    solana_reproduced: bool = False
    solana_target_id: str = ""
    solana_slot: int = 0
    solana_evidence: dict[str, Any] = field(default_factory=dict)
    severity_score_base: float = 0.0
    simulator_backend: str = "mock"
    pbo: float = 0.0
    cpcv_verdict: str = ""
    catalog_exploit_id: str = ""
    axis_scores: dict[str, float] = field(default_factory=dict)
    axis_survival_rate: float = 0.0
    evidence_grade: int = 0
    evidence_grade_label: str = "none"
    reproduction_tier: str = "simulation"
    deployed_viable: bool = False
    catalog_analogue: bool = False
    submission_readiness: str = "draft"
    results: list[AttackResult] = field(default_factory=list)


@dataclass
class Finding:
    """High-confidence vulnerability that passed all security gates."""

    finding_id: str
    template_id: str
    target_id: str
    severity: Severity
    severity_score: float
    economic_impact_usd: float
    capital_required_usd: float
    reproducibility: float
    parameters: dict[str, Any]
    invariant_violations: list[InvariantViolation]
    reproduction_steps: list[ReproductionStep]
    mitigations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    rediscovered_exploit_id: str = ""
    disclosure_status: str = ""
    fork_reproduced: bool = False
    fork_block_number: int = 0
    fork_evidence: dict[str, Any] = field(default_factory=dict)
    solana_confirmed: bool = False
    solana_reproduced: bool = False
    solana_slot: int = 0
    solana_evidence: dict[str, Any] = field(default_factory=dict)
    severity_score_base: float = 0.0
    axis_scores: dict[str, float] = field(default_factory=dict)
    axis_survival_rate: float = 0.0
    evidence_grade: int = 0
    evidence_grade_label: str = "none"
    hypothesis_id: str = ""
    parent_ids: list[str] = field(default_factory=list)
    lineage: list[str] = field(default_factory=list)
    generation_method: str = ""
    priority_score: float = 0.0
    novelty_score: float = 0.0
    reproduction_tier: str = "simulation"
    deployed_viable: bool = False
    catalog_analogue: bool = False
    submission_readiness: str = "draft"