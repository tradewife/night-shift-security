"""Reentrancy hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class ReentrancyGenerator(BaseHypothesisGenerator):
    def __init__(self) -> None:
        super().__init__("reentrancy")


register_generator(ReentrancyGenerator())