"""Composability risk template — cross-protocol collateral and callback chains."""

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


class ComposabilityRiskTemplate(AttackTemplate):
    """
    Exploit dangerous interactions across protocols sharing collateral or oracles.

    Parameters:
    - protocol_hops: number of cross-protocol calls in attack chain
    - leverage_multiplier: collateral inflation factor via composability
    - use_callback_chain: attacker triggers callbacks across protocol boundaries
    """

    @property
    def template_id(self) -> str:
        return "composability_risk"

    @property
    def description(self) -> str:
        return "Cross-protocol composability chain drains shared liquidity or collateral"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "protocol_hops": [2, 3, 4],
            "leverage_multiplier": [2.0, 5.0, 10.0],
            "use_callback_chain": [False, True],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        hops = parameters["protocol_hops"]
        leverage = parameters["leverage_multiplier"]
        use_callbacks = parameters["use_callback_chain"]

        has_composability = state.cross_protocol_enabled and state.shared_liquidity_usd > 0
        callback_viable = use_callbacks and state.callback_enabled
        collateral_weak = state.collateral_dependency_count >= 2

        inflated_collateral = state.collateral_liquidity_usd * leverage
        borrow_capacity = min(inflated_collateral, state.treasury_balance_usd * 0.5)

        success = (
            has_composability
            and collateral_weak
            and hops >= 2
            and (callback_viable or not use_callbacks)
            and borrow_capacity > 100_000
        )

        extracted = min(borrow_capacity * 0.6, state.treasury_balance_usd) if success else 0.0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("map_protocol_graph", "attacker", {"hops": hops}),
        ]

        if success:
            for i in range(min(hops, 3)):
                steps.append(
                    ReproductionStep(
                        "cross_protocol_call",
                        "attacker",
                        {"hop": i + 1, "protocol": f"dependency_{i}"},
                    )
                )
            if use_callbacks:
                steps.append(ReproductionStep("trigger_callback_chain", "attacker", {}))
            steps.append(ReproductionStep("extract_value", "attacker", {"amount_usd": extracted}))
            violations.append(
                InvariantViolation(
                    invariant_id="isolated_protocol_risk",
                    description="Protocol collateral must not be manipulable via external composability",
                    expected="bounded cross-protocol exposure",
                    actual=f"{hops}-hop chain with {leverage}x leverage inflated collateral",
                )
            )

        severity = Severity.CRITICAL if success and extracted >= 10_000_000 else (
            Severity.HIGH if success and extracted >= 1_000_000 else (
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
            capital_required_usd=state.shared_liquidity_usd * 0.05 if success else 0.0,
        )


register_template(ComposabilityRiskTemplate())