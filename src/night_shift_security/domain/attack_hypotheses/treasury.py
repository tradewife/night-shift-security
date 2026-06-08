"""Treasury drain hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class TreasuryDrainGenerator(BaseHypothesisGenerator):
    """Parameterized generator for treasury_drain attack hypotheses."""

    def __init__(self) -> None:
        super().__init__("treasury_drain")


register_generator(TreasuryDrainGenerator())