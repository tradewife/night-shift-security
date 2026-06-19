"""Concrete candidate sequence template — native-harness depth pass (Phase 10)."""

from typing import Any

from night_shift_security.data.schemas import (
    AttackResult,
    AttackVector,
    ContractState,
    ReproductionStep,
    Severity,
)
from night_shift_security.domain.attack_templates.base import AttackTemplate, register_template


class ConcreteSequenceTemplate(AttackTemplate):
    """Evaluate semantic-map entrypoints as hunt probes (not synthetic success)."""

    @property
    def template_id(self) -> str:
        return "concrete_sequence"

    @property
    def description(self) -> str:
        return "Concrete candidate instruction/call sequence from semantic recon"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "sequence_kind": ["instruction", "call"],
            "candidate_id": [""],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        kind = str(parameters.get("sequence_kind") or "instruction")
        candidate_id = str(parameters.get("candidate_id") or "")
        steps = parameters.get("steps") if isinstance(parameters.get("steps"), list) else []

        repro: list[ReproductionStep] = []
        if kind == "instruction":
            repro.append(
                ReproductionStep(
                    "invoke_instruction",
                    "attacker",
                    {
                        "discriminator": parameters.get("discriminator", ""),
                        "program_id": parameters.get("program_id", ""),
                        "candidate_id": candidate_id,
                        "steps": steps,
                    },
                )
            )
        else:
            repro.append(
                ReproductionStep(
                    "invoke_call",
                    "attacker",
                    {
                        "selector": parameters.get("selector", ""),
                        "contract": parameters.get("contract", ""),
                        "candidate_id": candidate_id,
                        "steps": steps,
                    },
                )
            )

        return AttackResult(
            vector=AttackVector(
                template_id=self.template_id,
                parameters=parameters,
                target_id=state.protocol_id,
            ),
            success=False,
            severity=Severity.LOW,
            economic_impact_usd=0.0,
            invariant_violations=[],
            reproduction_steps=repro,
            capital_required_usd=0.0,
        )


register_template(ConcreteSequenceTemplate())