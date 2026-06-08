"""Flash loan + oracle manipulation hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class FlashLoanOracleGenerator(BaseHypothesisGenerator):
    def __init__(self) -> None:
        super().__init__("flash_loan_oracle")


register_generator(FlashLoanOracleGenerator())