"""Treasury drain attack template — direct unauthorized withdrawal."""

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


class TreasuryDrainTemplate(AttackTemplate):
    """
    Drain treasury via compromised admin, weak withdrawal limits, or multisig bypass.

    Parameters:
    - withdrawal_pct: fraction of treasury to extract
    - use_compromised_admin: attacker has admin role
    - bypass_multisig: exploit threshold-1 multisig or missing signer checks
    """

    @property
    def template_id(self) -> str:
        return "treasury_drain"

    @property
    def description(self) -> str:
        return "Unauthorized treasury withdrawal via access control weakness"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "withdrawal_pct": [25.0, 50.0, 75.0, 100.0],
            "use_compromised_admin": [False, True],
            "bypass_multisig": [False, True],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        withdrawal_pct = parameters["withdrawal_pct"]
        use_admin = parameters["use_compromised_admin"]
        bypass_multisig = parameters["bypass_multisig"]

        has_access = (
            (use_admin and state.admin_role_compromised)
            or (bypass_multisig and state.multisig_threshold <= 1)
        )

        drain_amount = state.treasury_balance_usd * (withdrawal_pct / 100.0)
        within_limit = (
            state.withdrawal_limit_usd <= 0
            or drain_amount <= state.withdrawal_limit_usd
            or bypass_multisig
        )

        success = has_access and within_limit and drain_amount > 0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("identify_treasury", "attacker", {"balance_usd": state.treasury_balance_usd}),
        ]

        if use_admin:
            steps.append(ReproductionStep("use_admin_role", "attacker", {"compromised": state.admin_role_compromised}))
        if bypass_multisig:
            steps.append(ReproductionStep("bypass_multisig", "attacker", {"threshold": state.multisig_threshold}))

        if success:
            steps.append(ReproductionStep("withdraw", "attacker", {"amount_usd": drain_amount}))
            violations.append(
                InvariantViolation(
                    invariant_id="authorized_withdrawal_only",
                    description="Treasury withdrawals require proper authorization",
                    expected="multisig + rate limit enforced",
                    actual=f"withdrew ${drain_amount:,.0f} without authorization",
                )
            )

        severity = Severity.CRITICAL if success and drain_amount >= 10_000_000 else (
            Severity.HIGH if success and drain_amount >= 1_000_000 else (
                Severity.MEDIUM if success else Severity.LOW
            )
        )

        return AttackResult(
            vector=AttackVector(template_id=self.template_id, parameters=parameters, target_id=state.protocol_id),
            success=success,
            severity=severity,
            economic_impact_usd=drain_amount if success else 0.0,
            invariant_violations=violations,
            reproduction_steps=steps,
            capital_required_usd=0.0,
        )


register_template(TreasuryDrainTemplate())