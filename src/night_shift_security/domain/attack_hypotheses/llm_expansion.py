"""LLM-assisted hypothesis expansion — proposal-only, never trusted for validation."""

from __future__ import annotations

from typing import Any

from night_shift_security.domain.attack_hypotheses.base import (
    AttackHypothesis,
    BaseHypothesisGenerator,
    get_generator,
    validate_hypothesis,
)


class LLMExpansionOrchestrator:
    """
    Thin orchestrator for LLM-proposed hypothesis variants.

    Strict contract:
    - Output is untrusted proposal only (metadata.trusted = False).
    - Never participates in validation, scoring, or gate decisions.
    - All proposals must still pass deterministic ParameterSpace validation.
    """

    def __init__(self, enabled: bool = False, fallback: str = "parametric") -> None:
        self.enabled = enabled
        self.fallback = fallback

    def propose_variants(
        self,
        seed: AttackHypothesis,
        n: int = 3,
    ) -> list[AttackHypothesis]:
        """
        Propose variants from a seed hypothesis.

        v1 stub: deterministic mutation stand-in when LLM is disabled.
        When enabled, this hook would call an external LLM — still proposal-only.
        """
        generator = get_generator(seed.template)
        if generator is None:
            return []

        if self.enabled and self.fallback != "parametric":
            return []

        proposals: list[AttackHypothesis] = []
        current = seed
        for _ in range(n):
            if self.fallback == "parametric":
                variant = generator.mutate(current)
            else:
                return proposals
            variant.metadata["generation_method"] = "llm_proposal"
            variant.metadata["trusted"] = False
            variant.metadata["llm_expansion"] = {
                "enabled": self.enabled,
                "fallback": self.fallback,
                "seed_id": seed.hypothesis_id,
                "note": (
                    "parametric_fallback"
                    if not self.enabled or self.fallback == "parametric"
                    else "llm_proposal_pending"
                ),
            }
            valid, _ = validate_hypothesis(variant)
            if valid:
                proposals.append(variant)
            current = variant
        return proposals

    def expand_batch(
        self,
        seeds: list[AttackHypothesis],
        variants_per_seed: int = 2,
    ) -> list[AttackHypothesis]:
        expanded: list[AttackHypothesis] = []
        for seed in seeds:
            expanded.extend(self.propose_variants(seed, n=variants_per_seed))
        return expanded