"""Access control escalation hypothesis generator."""

from night_shift_security.domain.attack_hypotheses.base import BaseHypothesisGenerator, register_generator


class AccessControlEscalationGenerator(BaseHypothesisGenerator):
    def __init__(self) -> None:
        super().__init__("access_control_escalation")


register_generator(AccessControlEscalationGenerator())