"""Access control escalation template — role bypass and privileged function exposure."""

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


class AccessControlEscalationTemplate(AttackTemplate):
    """
    Escalate privileges via misconfigured roles, zero-address roots, or exposed admin functions.

    Parameters:
    - target_role: role attacker attempts to acquire
    - bypass_role_check: exploit missing onlyRole modifier
    - use_zero_root: exploit uninitialized or zero merkle/admin root
    """

    @property
    def template_id(self) -> str:
        return "access_control_escalation"

    @property
    def description(self) -> str:
        return "Privilege escalation to admin/owner via access control misconfiguration"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "target_role": ["owner", "admin", "minter", "pauser"],
            "bypass_role_check": [False, True],
            "use_zero_root": [False, True],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        target_role = parameters["target_role"]
        bypass_check = parameters["bypass_role_check"]
        use_zero_root = parameters["use_zero_root"]

        role_exposed = state.privileged_function_exposed or bypass_check
        zero_root_vuln = use_zero_root and state.zero_root_vulnerable
        hierarchy_bypass = state.role_hierarchy_bypass and bypass_check

        can_escalate = (
            (role_exposed and bypass_check)
            or zero_root_vuln
            or hierarchy_bypass
            or (state.admin_role_compromised and target_role in ("owner", "admin"))
        )

        success = can_escalate and state.treasury_balance_usd > 0
        extracted = state.treasury_balance_usd * (0.5 if target_role == "pauser" else 1.0) if success else 0.0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("enumerate_roles", "attacker", {"target": target_role}),
        ]

        if success:
            if use_zero_root:
                steps.append(ReproductionStep("exploit_zero_root", "attacker", {}))
            if bypass_check:
                steps.append(ReproductionStep("call_privileged_without_role", "attacker", {"role": target_role}))
            steps.append(ReproductionStep("execute_privileged_action", "attacker", {"amount_usd": extracted}))
            violations.append(
                InvariantViolation(
                    invariant_id="least_privilege",
                    description="Privileged functions must enforce role-based access control",
                    expected=f"onlyRole({target_role}) enforced",
                    actual=f"attacker acquired {target_role} without authorization",
                )
            )

        severity = Severity.CRITICAL if success and extracted >= 10_000_000 else (
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
            capital_required_usd=0.0,
        )


register_template(AccessControlEscalationTemplate())