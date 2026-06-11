"""Curated Cantina bug bounty registry — https://cantina.xyz/opportunities"""

from __future__ import annotations

from night_shift_security.data.bounty_program import (
    BountyProgram,
    list_bounty_programs,
    program_summary,
    program_to_live_target,
)

# Verified live on Cantina (2026-06-11). Curated for NSS template + catalogue coverage.
CANTINA_PROGRAMS: tuple[BountyProgram, ...] = (
    BountyProgram(
        platform="cantina",
        slug="uniswap",
        name="Uniswap",
        ecosystem="evm",
        max_bounty_usd=15_500_000,
        product_types=("amm", "dex"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        cantina_id="f9df94db-c7b1-434b-bb06-d1360abdd1be",
        deposit_required=True,
        notes="Cantina — composability/flash-loan analogue to Crema.",
    ),
    BountyProgram(
        platform="cantina",
        slug="reserve-protocol",
        name="Reserve Protocol",
        ecosystem="evm",
        max_bounty_usd=10_000_000,
        product_types=("stablecoin", "governance"),
        templates=("governance_capture", "treasury_drain"),
        catalog_analogue="beanstalk-2022",
        cantina_id="3709ca85-4050-407e-9b36-51f5d5ea9b00",
        deposit_required=True,
        notes="Cantina — governance flash-loan analogue to Beanstalk.",
    ),
    BountyProgram(
        platform="cantina",
        slug="euler",
        name="Euler",
        ecosystem="evm",
        max_bounty_usd=7_500_000,
        product_types=("lending", "defi"),
        templates=("reentrancy", "flash_loan_oracle", "composability_risk"),
        catalog_analogue="euler-finance-2023",
        cantina_id="4d285eee-602e-440a-845e-25e155cec26a",
        deposit_required=True,
        notes="Cantina — direct euler-finance-2023 catalogue anchor; fork harness.",
    ),
    BountyProgram(
        platform="cantina",
        slug="polymarket",
        name="Polymarket",
        ecosystem="evm",
        max_bounty_usd=5_000_000,
        product_types=("prediction", "defi"),
        templates=("governance_capture", "flash_loan_oracle"),
        catalog_analogue="mango-markets-2022",
        cantina_id="ff945ca2-2a6e-4b83-b1b6-7a0cd3b94bea",
        deposit_required=True,
        notes="Cantina — oracle/governance stress via Mango analogue.",
    ),
    BountyProgram(
        platform="cantina",
        slug="coinbase",
        name="Coinbase",
        ecosystem="evm",
        max_bounty_usd=5_000_000,
        product_types=("cex", "infrastructure"),
        templates=("access_control_escalation", "treasury_drain"),
        catalog_analogue="nomad-bridge-2022",
        cantina_id="55316f42-3c5e-4746-9bd0-0f18dcbc344b",
        notes="Cantina — access control analogue to Nomad.",
    ),
    BountyProgram(
        platform="cantina",
        slug="morpho",
        name="Morpho",
        ecosystem="evm",
        max_bounty_usd=2_500_000,
        product_types=("lending", "defi"),
        templates=("reentrancy", "flash_loan_oracle", "composability_risk"),
        catalog_analogue="euler-finance-2023",
        cantina_id="35a5f0a1-2ffd-432c-8f3b-77d169add8c3",
        notes="Cantina — lending composability via Euler analogue.",
    ),
    BountyProgram(
        platform="cantina",
        slug="pendle",
        name="Pendle Finance",
        ecosystem="evm",
        max_bounty_usd=2_000_000,
        product_types=("yield", "defi"),
        templates=("flash_loan_oracle", "composability_risk"),
        catalog_analogue="mango-markets-2022",
        cantina_id="fb1f1c54-0cb9-4201-8791-fb1e78e6e600",
        deposit_required=True,
        notes="Cantina — yield/oracle vectors via Mango analogue.",
    ),
)


def list_programs(
    *,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    live_only: bool = True,
) -> list[BountyProgram]:
    return list_bounty_programs(
        CANTINA_PROGRAMS,
        platform="cantina",
        ecosystem=ecosystem,
        min_max_bounty_usd=min_max_bounty_usd,
        live_only=live_only,
    )


__all__ = [
    "BountyProgram",
    "CANTINA_PROGRAMS",
    "list_programs",
    "program_summary",
    "program_to_live_target",
]