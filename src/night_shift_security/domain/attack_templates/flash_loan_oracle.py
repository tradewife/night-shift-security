"""Flash loan + oracle manipulation attack template."""

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


class FlashLoanOracleTemplate(AttackTemplate):
    """
    Flash loan capital + oracle price manipulation to extract protocol value.

    Parameters:
    - loan_amount_usd: flash loan size
    - price_manipulation_pct: oracle price skew from true price
    - use_single_oracle: exploit single-oracle dependency (no TWAP/median)
    """

    @property
    def template_id(self) -> str:
        return "flash_loan_oracle"

    @property
    def description(self) -> str:
        return "Flash loan combined with oracle price manipulation"

    def param_grid(self) -> dict[str, list[Any]]:
        return {
            "loan_amount_usd": [1_000_000, 5_000_000, 10_000_000, 50_000_000],
            "price_manipulation_pct": [10.0, 25.0, 50.0, 100.0],
            "use_single_oracle": [True, False],
        }

    def execute(self, state: ContractState, parameters: dict[str, Any]) -> AttackResult:
        loan = parameters["loan_amount_usd"]
        manipulation_pct = parameters["price_manipulation_pct"]
        single_oracle = parameters["use_single_oracle"]

        loan_feasible = state.flash_loan_available and loan <= state.max_flash_loan_usd
        oracle_vulnerable = state.oracle_manipulable and (single_oracle or manipulation_pct >= 50.0)
        liquidity_sufficient = loan <= state.collateral_liquidity_usd * 0.5

        manipulated_price = state.true_price_usd * (1 + manipulation_pct / 100.0)
        price_deviation = abs(manipulated_price - state.oracle_price_usd) / max(state.true_price_usd, 0.01) * 100

        can_manipulate = oracle_vulnerable and price_deviation >= manipulation_pct * 0.5
        success = loan_feasible and can_manipulate and liquidity_sufficient

        extracted = min(loan * (manipulation_pct / 100.0) * 0.3, state.treasury_balance_usd) if success else 0.0

        violations: list[InvariantViolation] = []
        steps: list[ReproductionStep] = [
            ReproductionStep("flash_loan", "attacker", {"amount_usd": loan}),
            ReproductionStep("manipulate_oracle", "attacker", {"skew_pct": manipulation_pct}),
        ]

        if success:
            steps.append(ReproductionStep("borrow_overcollateralized", "attacker", {}))
            steps.append(ReproductionStep("extract_profit", "attacker", {"amount_usd": extracted}))
            violations.append(
                InvariantViolation(
                    invariant_id="oracle_price_integrity",
                    description="Oracle price must reflect true market price within tolerance",
                    expected=f"~${state.true_price_usd:.4f}",
                    actual=f"manipulated to ${manipulated_price:.4f}",
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
            capital_required_usd=loan * 0.01 if loan_feasible else loan,
        )

    def realism_score(self, parameters: dict[str, Any], state: ContractState) -> float:
        base = super().realism_score(parameters, state)
        if not state.flash_loan_available:
            return base * 0.1
        if parameters["loan_amount_usd"] > state.max_flash_loan_usd:
            return base * 0.2
        return base


register_template(FlashLoanOracleTemplate())