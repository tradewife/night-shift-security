"""Attack template base class — mirrors RTP StrategyPlugin pattern."""

from abc import ABC, abstractmethod
from typing import Any

from night_shift_security.data.schemas import AttackResult, AttackVector, ContractState


class AttackTemplate(ABC):
    """Base class for attack vector templates.

    Subclasses define a searchable parameter space and execution logic.
    """

    @property
    @abstractmethod
    def template_id(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @abstractmethod
    def param_grid(self) -> dict[str, list[Any]]:
        """Return searchable parameter grid for Stage 1 hypothesis generation."""
        ...

    @abstractmethod
    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        """Execute attack against a contract state. Returns AttackResult."""
        ...

    def realism_score(self, parameters: dict[str, Any], state: ContractState) -> float:
        """Score how feasible this attack is for a motivated attacker (0–1)."""
        capital = self._estimate_capital(parameters, state)
        if capital <= 0:
            return 1.0
        if capital > 10_000_000:
            return 0.2
        if capital > 1_000_000:
            return 0.5
        return 0.8

    def _estimate_capital(self, parameters: dict[str, Any], state: ContractState) -> float:
        voting_pct = parameters.get("voting_power_pct", 0.0)
        if voting_pct > 0 and state.total_voting_power > 0:
            return state.treasury_balance_usd * (voting_pct / 100.0) * 0.1
        return 0.0


_REGISTRY: dict[str, AttackTemplate] = {}


def register_template(template: AttackTemplate) -> None:
    _REGISTRY[template.template_id] = template


def get_template(template_id: str) -> AttackTemplate:
    if template_id not in _REGISTRY:
        raise KeyError(f"Unknown attack template: {template_id}")
    return _REGISTRY[template_id]


def list_templates() -> list[str]:
    return list(_REGISTRY.keys())