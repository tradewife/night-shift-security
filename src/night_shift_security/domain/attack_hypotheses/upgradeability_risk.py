"""Upgradeability risk hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class UpgradeabilityRiskGenerator(BaseHypothesisGenerator):
    def __init__(self) -> None:
        super().__init__("upgradeability_risk")


register_generator(UpgradeabilityRiskGenerator())