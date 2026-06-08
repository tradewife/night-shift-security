"""Hypothesis Generation Layer — parameterized, composable attack hypotheses."""

from night_shift_security.domain.attack_hypotheses.base import (
    AttackHypothesis,
    HypothesisGenerator,
    ParameterSpace,
    attack_vector_to_hypothesis,
    get_generator,
    hypothesis_to_attack_vector,
    list_generators,
    register_generator,
    sample_parameters,
    validate_hypothesis,
    validate_parameters,
)
from night_shift_security.domain.attack_hypotheses.llm_expansion import LLMExpansionOrchestrator
from night_shift_security.domain.attack_hypotheses.llm_provider import (
    LLMProvider,
    MockLLMProvider,
    create_llm_provider,
)
from night_shift_security.domain.attack_hypotheses.mapping import MAPPING_VERSION, MAPPING_REGISTRY

# Register concrete generators on import.
import night_shift_security.domain.attack_hypotheses.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_hypotheses.composability_risk  # noqa: F401
import night_shift_security.domain.attack_hypotheses.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_hypotheses.governance  # noqa: F401
import night_shift_security.domain.attack_hypotheses.reentrancy  # noqa: F401
import night_shift_security.domain.attack_hypotheses.treasury  # noqa: F401
import night_shift_security.domain.attack_hypotheses.upgradeability_risk  # noqa: F401

__all__ = [
    "AttackHypothesis",
    "HypothesisGenerator",
    "ParameterSpace",
    "LLMExpansionOrchestrator",
    "LLMProvider",
    "MockLLMProvider",
    "create_llm_provider",
    "MAPPING_VERSION",
    "MAPPING_REGISTRY",
    "attack_vector_to_hypothesis",
    "get_generator",
    "hypothesis_to_attack_vector",
    "list_generators",
    "register_generator",
    "sample_parameters",
    "validate_hypothesis",
    "validate_parameters",
]