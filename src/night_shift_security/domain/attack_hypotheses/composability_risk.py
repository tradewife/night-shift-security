"""Composability risk hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class ComposabilityRiskGenerator(BaseHypothesisGenerator):
    def __init__(self) -> None:
        super().__init__("composability_risk")


register_generator(ComposabilityRiskGenerator())