"""Reentrancy attack template — recursive external calls before state update."""

from typing import Any

from night_shift_security.data.schemas import (
    AttackResult,
    AttackVector,
    ContractState,
    InvariantViolation,
    ReproductionStep,
    Severity,
)
from night_shift_security.domain.attack_templates.base import AttackTemplate, register_template


class ReentrancyTemplate(AttackTemplate):
    """
    Exploit missing reentrancy guard or state-update ordering flaw.

    Parameters:
    - recursion_depth: number of nested reentrant calls
    - target_function: which vulnerable entrypoint to recurse through
    """

    @property
    def template_id(self) -> str:
        return "reentrancy"

    @property
    def description(self) -> str:
        return "Reentrant call before state update drains contract balance"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "recursion_depth": [2, 3, 5, 10],
            "target_function": ["withdraw", "claim", "redeem"],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        depth = parameters["recursion_depth"]
        target_fn = parameters["target_function"]

        guard_absent = not state.reentrancy_guard
        callback_possible = state.callback_enabled or state.external_call_before_state_update
        vulnerable = guard_absent or state.external_call_before_state_update

        success = vulnerable and callback_possible and depth >= 2 and state.treasury_balance_usd > 0

        per_call = state.treasury_balance_usd / max(depth, 1)
        extracted = min(per_call * depth * 0.8, state.treasury_balance_usd) if success else 0.0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("deploy_attacker_contract", "attacker", {"callback": True}),
            ReproductionStep(f"call_{target_fn}", "attacker", {"depth": depth}),
        ]

        if success:
            for i in range(min(depth, 3)):
                steps.append(ReproductionStep("reentrant_callback", "attacker", {"iteration": i + 1}))
            violations.append(
                InvariantViolation(
                    invariant_id="checks_effects_interactions",
                    description="State must be updated before external calls (CEI pattern)",
                    expected="balance decremented before transfer",
                    actual=f"{depth} reentrant calls before state update",
                )
            )

        severity = Severity.CRITICAL if success and extracted >= 5_000_000 else (
            Severity.HIGH if success and extracted >= 500_000 else (
                Severity.MEDIUM if success else Severity.LOW
            )
        )

        return AttackResult(
            vector=AttackVector(template_id=self.template_id, parameters=parameters, target_id=state.protocol_id),
            success=success,
            severity=severity,
            economic_impact_usd=extracted,
            invariant_violations=violations,
            reproduction_steps=steps,
            capital_required_usd=10_000.0 if success else 0.0,
        )


register_template(ReentrancyTemplate())