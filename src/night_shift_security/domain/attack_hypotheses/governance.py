"""Governance capture hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class GovernanceCaptureGenerator(BaseHypothesisGenerator):
    """Parameterized generator for governance_capture attack hypotheses."""

    def __init__(self) -> None:
        super().__init__("governance_capture")


register_generator(GovernanceCaptureGenerator())