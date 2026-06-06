"""Upgradeability risk template — proxy storage collision and unprotected upgrades."""

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


class UpgradeabilityRiskTemplate(AttackTemplate):
    """
    Exploit upgradeable proxy patterns: unprotected initialize, storage collision, malicious impl.

    Parameters:
    - upgrade_method: how attacker gains upgrade authority
    - storage_collision: exploit overlapping storage slots between proxy and impl
    - skip_initializer: call initialize on uninitialized proxy
    """

    @property
    def template_id(self) -> str:
        return "upgradeability_risk"

    @property
    def description(self) -> str:
        return "Proxy upgrade or storage collision hijacks implementation logic"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "upgrade_method": ["direct_admin", "storage_collision", "uninitialized_proxy"],
            "storage_collision": [False, True],
            "skip_initializer": [False, True],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        method = parameters["upgrade_method"]
        collision = parameters["storage_collision"]
        skip_init = parameters["skip_initializer"]

        proxy_vulnerable = state.upgradeable_proxy
        admin_weak = state.admin_role_compromised or state.proxy_admin_unprotected
        uninitialized = state.proxy_initialized is False

        can_upgrade = False
        if method == "direct_admin" and proxy_vulnerable and admin_weak:
            can_upgrade = True
        elif method == "storage_collision" and proxy_vulnerable and collision and state.storage_collision_risk:
            can_upgrade = True
        elif method == "uninitialized_proxy" and proxy_vulnerable and skip_init and uninitialized:
            can_upgrade = True

        success = can_upgrade and state.treasury_balance_usd > 0
        extracted = state.treasury_balance_usd if success else 0.0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("identify_proxy", "attacker", {"upgradeable": state.upgradeable_proxy}),
        ]

        if success:
            if method == "storage_collision":
                steps.append(ReproductionStep("craft_malicious_impl", "attacker", {"collision": True}))
            elif method == "uninitialized_proxy":
                steps.append(ReproductionStep("call_initialize", "attacker", {"become_admin": True}))
            else:
                steps.append(ReproductionStep("upgrade_to_malicious_impl", "attacker", {}))
            steps.append(ReproductionStep("drain_via_new_logic", "attacker", {"amount_usd": extracted}))
            violations.append(
                InvariantViolation(
                    invariant_id="immutable_core_logic",
                    description="Core protocol logic must not be replaceable without governance",
                    expected="timelocked upgrade with audit",
                    actual=f"upgrade via {method}",
                )
            )

        severity = Severity.CRITICAL if success and extracted >= 5_000_000 else (
            Severity.HIGH if success else Severity.LOW
        )

        return AttackResult(
            vector=AttackVector(template_id=self.template_id, parameters=parameters, target_id=state.protocol_id),
            success=success,
            severity=severity,
            economic_impact_usd=extracted,
            invariant_violations=violations,
            reproduction_steps=steps,
            capital_required_usd=5_000.0 if success else 0.0,
        )


register_template(UpgradeabilityRiskTemplate())