"""Governance capture attack template — MVP attack class #1."""

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


class GovernanceCaptureTemplate(AttackTemplate):
    """
    Attempt to capture governance and drain treasury via proposal + execution.

    Parameterized attack conditions:
    - voting_power_pct: attacker voting power as % of total
    - use_flash_loan: borrow voting power temporarily
    - bypass_timelock: exploit short execution window
    """

    @property
    def template_id(self) -> str:
        return "governance_capture"

    @property
    def description(self) -> str:
        return "Governance proposal to transfer treasury funds with threshold/timelock bypass"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "voting_power_pct": [10.0, 25.0, 33.0, 40.0, 51.0, 67.0],
            "use_flash_loan": [False, True],
            "bypass_timelock": [False, True],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        voting_pct = parameters["voting_power_pct"]
        use_flash_loan = parameters["use_flash_loan"]
        bypass_timelock = parameters["bypass_timelock"]

        effective_voting = voting_pct
        if use_flash_loan and state.flash_loan_available:
            effective_voting = min(voting_pct + 30.0, 100.0)

        attacker_power = state.attacker_voting_power
        if effective_voting > 0:
            attacker_power = state.total_voting_power * (effective_voting / 100.0)

        votes_needed = state.total_voting_power * (state.proposal_threshold_pct / 100.0)
        has_votes = attacker_power >= votes_needed

        governance_window_weak = (
            state.timelock_hours < 48.0
            or state.execution_delay_hours < 1.0
            or bypass_timelock
        )

        success = has_votes and governance_window_weak and state.treasury_balance_usd > 0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("acquire_voting_power", "attacker", {"pct": effective_voting}),
            ReproductionStep("submit_proposal", "attacker", {"target": "treasury_drain"}),
            ReproductionStep("vote", "attacker", {"votes": attacker_power}),
        ]

        if success:
            steps.append(ReproductionStep("execute_proposal", "attacker", {"amount_usd": state.treasury_balance_usd}))
            violations.append(
                InvariantViolation(
                    invariant_id="treasury_non_decreasing",
                    description="Treasury balance must not decrease without authorized governance",
                    expected=f">= ${state.treasury_balance_usd:,.0f}",
                    actual="$0",
                )
            )
            if has_votes and effective_voting < state.quorum_pct:
                violations.append(
                    InvariantViolation(
                        invariant_id="quorum_requirement",
                        description="Proposals must meet quorum",
                        expected=f">= {state.quorum_pct}%",
                        actual=f"{effective_voting}%",
                    )
                )

        severity = Severity.CRITICAL if success and state.treasury_balance_usd >= 10_000_000 else (
            Severity.HIGH if success else Severity.LOW
        )

        capital = self._estimate_capital(parameters, state)
        if use_flash_loan and state.flash_loan_available:
            capital = min(capital, 500_000.0)

        return AttackResult(
            vector=AttackVector(template_id=self.template_id, parameters=parameters, target_id=state.protocol_id),
            success=success,
            severity=severity,
            economic_impact_usd=state.treasury_balance_usd if success else 0.0,
            invariant_violations=violations,
            reproduction_steps=steps,
            capital_required_usd=capital,
            notes="Flash loan voting" if use_flash_loan and state.flash_loan_available else "",
        )

    def realism_score(self, parameters: dict[str, Any], state: ContractState) -> float:
        base = super().realism_score(parameters, state)
        if parameters.get("use_flash_loan") and not state.flash_loan_available:
            return base * 0.1
        if parameters.get("bypass_timelock") and state.timelock_hours >= 48:
            return base * 0.3
        return base


_template = GovernanceCaptureTemplate()
register_template(_template)