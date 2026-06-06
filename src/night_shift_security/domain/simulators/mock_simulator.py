"""Mock simulator — in-memory ContractState execution (default backend)."""

from night_shift_security.data.schemas import AttackResult, AttackVector, ContractState
from night_shift_security.domain.attack_templates.base import get_template
from night_shift_security.domain.simulators.base import AttackSimulator, SimulatorBackend


class MockSimulator(AttackSimulator):
    """Execute attacks via Python templates against ContractState."""

    @property
    def backend(self) -> SimulatorBackend:
        return SimulatorBackend.MOCK

    def is_available(self) -> bool:
        return True

    def execute(self, vector: AttackVector, state: ContractState) -> AttackResult:
        template = get_template(vector.template_id)
        result = template.execute(state, vector.parameters)
        result.vector = vector
        return result