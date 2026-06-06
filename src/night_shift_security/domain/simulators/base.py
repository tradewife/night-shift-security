"""Attack simulator abstraction — mock and Foundry backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from night_shift_security.data.schemas import AttackResult, AttackVector, ContractState


class SimulatorBackend(str, Enum):
    MOCK = "mock"
    FOUNDRY = "foundry"


@dataclass
class SimulatorCapabilities:
    backend: SimulatorBackend
    fork_available: bool
    forge_installed: bool


class AttackSimulator(ABC):
    """Execute attack vectors against contract state via a simulation backend."""

    @property
    @abstractmethod
    def backend(self) -> SimulatorBackend:
        ...

    @abstractmethod
    def execute(
        self,
        vector: AttackVector,
        state: ContractState,
    ) -> AttackResult:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...