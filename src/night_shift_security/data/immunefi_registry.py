"""Curated Immunefi bug bounty registry — aligned to Night Shift attack templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from night_shift_security.data.bounty_program import BountyProgram
from night_shift_security.data.target_config import LiveTarget


@dataclass(frozen=True)
class ImmunefiProgram:
    """A live Immunefi program we can probe with the engine."""

    slug: str
    name: str
    ecosystem: str
    max_bounty_usd: int
    product_types: tuple[str, ...]
    templates: tuple[str, ...]
    catalog_analogue: str = ""
    poc_required: bool = True
    kyc_required: bool = False
    live: bool = True
    primacy_of_impact: bool = False
    triaged: bool = False
    notes: str = ""

    @property
    def url(self) -> str:
        return f"https://immunefi.com/bug-bounty/{self.slug}/information/"


# Verified live on Immunefi (2026-06-09). 213 total programs on platform.
IMMUNEFI_PROGRAMS: tuple[ImmunefiProgram, ...] = (
    # --- Solana (engine strength: fixture + catalog analogues) ---
    ImmunefiProgram(
        slug="kamino",
        name="Kamino",
        ecosystem="solana",
        max_bounty_usd=1_500_000,
        product_types=("lending", "liquidity", "leverage"),
        templates=("flash_loan_oracle", "composability_risk", "reentrancy"),
        catalog_analogue="mango-markets-2022",
        kyc_required=True,
        notes="Triaged by Immunefi; lending+leverage — oracle/composability vectors.",
    ),
    ImmunefiProgram(
        slug="orca",
        name="Orca",
        ecosystem="solana",
        max_bounty_usd=500_000,
        product_types=("amm", "dex"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        notes="Whirlpools CLMM — composability/flash-loan analogue to Crema.",
    ),
    ImmunefiProgram(
        slug="raydium",
        name="Raydium",
        ecosystem="solana",
        max_bounty_usd=505_000,
        product_types=("amm", "dex"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        notes="CLMM + hybrid AMM — $3.2M paid historically on Immunefi.",
    ),
    ImmunefiProgram(
        slug="marinade",
        name="Marinade Finance",
        ecosystem="solana",
        max_bounty_usd=250_000,
        product_types=("staking", "defi"),
        templates=("governance_capture", "treasury_drain"),
        catalog_analogue="solend-whale-2022",
        notes="Liquid staking — governance/treasury stress via Solend analogue.",
    ),
    ImmunefiProgram(
        slug="wormhole",
        name="Wormhole",
        ecosystem="multichain",
        max_bounty_usd=1_000_000,
        product_types=("bridge", "crosschain"),
        templates=("access_control_escalation", "composability_risk"),
        catalog_analogue="nomad-bridge-2022",
        triaged=True,
        notes="Cross-chain messaging — live cap $1M (Immunefi Jun 2026); triage forks.",
    ),
    ImmunefiProgram(
        slug="jito",
        name="Jito",
        ecosystem="solana",
        max_bounty_usd=2_000_000,
        product_types=("mev", "staking", "defi"),
        templates=("access_control_escalation", "treasury_drain"),
        catalog_analogue="mango-markets-2022",
        kyc_required=True,
        notes="Solana MEV/staking — Tier-A Immunefi gap; validator depth TBD.",
    ),
    ImmunefiProgram(
        slug="layerzero",
        name="LayerZero",
        ecosystem="multichain",
        max_bounty_usd=15_000_000,
        product_types=("bridge", "crosschain", "messaging"),
        templates=("access_control_escalation", "composability_risk"),
        catalog_analogue="nomad-bridge-2022",
        primacy_of_impact=True,
        notes="Omnichain messaging — Nomad access-control analogue on EVM forks.",
    ),
    ImmunefiProgram(
        slug="gmx",
        name="GMX",
        ecosystem="evm",
        max_bounty_usd=5_000_000,
        product_types=("perps", "defi"),
        templates=("flash_loan_oracle", "composability_risk"),
        catalog_analogue="mango-markets-2022",
        notes="Perps/oracle — Mango oracle analogue.",
    ),
    ImmunefiProgram(
        slug="sky",
        name="Sky",
        ecosystem="evm",
        max_bounty_usd=10_000_000,
        product_types=("stablecoin", "lending", "governance"),
        templates=("governance_capture", "flash_loan_oracle"),
        catalog_analogue="beanstalk-2022",
        notes="Maker/Sky governance — Beanstalk analogue.",
    ),
    ImmunefiProgram(
        slug="onre",
        name="OnRe",
        ecosystem="solana",
        max_bounty_usd=500_000,
        product_types=("defi", "lending"),
        templates=("flash_loan_oracle", "composability_risk"),
        catalog_analogue="mango-markets-2022",
        notes="Solana DeFi — Mango oracle analogue.",
    ),
    ImmunefiProgram(
        slug="drift",
        name="Drift Protocol",
        ecosystem="solana",
        max_bounty_usd=500_000,
        product_types=("perps", "defi"),
        templates=("flash_loan_oracle", "composability_risk"),
        catalog_analogue="mango-markets-2022",
        notes="Solana perps — oracle/composability analogue.",
    ),
    ImmunefiProgram(
        slug="marginfi",
        name="marginfi",
        ecosystem="solana",
        max_bounty_usd=250_000,
        product_types=("lending", "defi"),
        templates=("flash_loan_oracle", "composability_risk"),
        catalog_analogue="mango-markets-2022",
        notes="Solana lending — flash-loan/oracle vectors.",
    ),
    ImmunefiProgram(
        slug="sanctum",
        name="Sanctum",
        ecosystem="solana",
        max_bounty_usd=250_000,
        product_types=("staking", "defi"),
        templates=("composability_risk", "treasury_drain"),
        catalog_analogue="solend-whale-2022",
        notes="Liquid staking router — composability stress.",
    ),
    ImmunefiProgram(
        slug="meteora",
        name="Meteora",
        ecosystem="solana",
        max_bounty_usd=250_000,
        product_types=("amm", "dex"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        notes="DLMM/AMM — CLMM analogue.",
    ),
    ImmunefiProgram(
        slug="pump",
        name="Pump.fun",
        ecosystem="solana",
        max_bounty_usd=250_000,
        product_types=("launchpad", "defi"),
        templates=("access_control_escalation", "treasury_drain"),
        catalog_analogue="mango-markets-2022",
        notes="Token launchpad — access-control vectors.",
    ),
    ImmunefiProgram(
        slug="uniswap",
        name="Uniswap",
        ecosystem="evm",
        max_bounty_usd=15_500_000,
        product_types=("amm", "dex"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        primacy_of_impact=True,
        notes="Uniswap v4 — Crema composability analogue; Cantina overlap.",
    ),
    ImmunefiProgram(
        slug="zest-protocol-v2",
        name="Zest Protocol V2",
        ecosystem="stacks",
        max_bounty_usd=100_000,
        product_types=("lending", "defi"),
        templates=("flash_loan_oracle", "access_control_escalation"),
        notes="Stacks lending — simulation-only for now (no Stacks harness).",
    ),
    # --- EVM (simulation + optional fork when RPC available) ---
    ImmunefiProgram(
        slug="beanstalk",
        name="Beanstalk",
        ecosystem="evm",
        max_bounty_usd=1_100_000,
        product_types=("governance", "defi"),
        templates=("governance_capture", "treasury_drain"),
        catalog_analogue="beanstalk-2022",
        notes="Direct catalog anchor — governance flash-loan attack.",
    ),
    ImmunefiProgram(
        slug="aave",
        name="Aave",
        ecosystem="evm",
        max_bounty_usd=1_000_000,
        product_types=("lending", "defi"),
        templates=("reentrancy", "flash_loan_oracle", "composability_risk"),
        catalog_analogue="euler-finance-2023",
        notes="Lending protocol — reentrancy/oracle vectors via Euler analogue.",
    ),
    ImmunefiProgram(
        slug="compoundfinance",
        name="Compound Finance",
        ecosystem="evm",
        max_bounty_usd=1_000_000,
        product_types=("lending", "defi"),
        templates=("reentrancy", "governance_capture"),
        catalog_analogue="beanstalk-2022",
        notes="Lending + governance surface.",
    ),
    ImmunefiProgram(
        slug="balancer",
        name="Balancer",
        ecosystem="evm",
        max_bounty_usd=1_000_000,
        product_types=("amm", "defi"),
        templates=("composability_risk", "flash_loan_oracle"),
        catalog_analogue="crema-finance-2022",
        notes="Weighted pools — composability/oracle stress.",
    ),
    ImmunefiProgram(
        slug="ens",
        name="ENS",
        ecosystem="evm",
        max_bounty_usd=250_000,
        product_types=("governance", "infrastructure"),
        templates=("governance_capture", "access_control_escalation"),
        catalog_analogue="tornado-governance-2023",
        notes="Governance infrastructure.",
    ),
    ImmunefiProgram(
        slug="ethena",
        name="Ethena",
        ecosystem="evm",
        max_bounty_usd=3_000_000,
        product_types=("stablecoin", "defi"),
        templates=("flash_loan_oracle", "treasury_drain"),
        catalog_analogue="mango-markets-2022",
        notes="Synthetic dollar — oracle manipulation vectors.",
    ),
)


def immunefi_to_bounty(program: ImmunefiProgram) -> BountyProgram:
    """Convert Immunefi program to unified BountyProgram."""
    return BountyProgram(
        platform="immunefi",
        slug=program.slug,
        name=program.name,
        ecosystem=program.ecosystem,
        max_bounty_usd=program.max_bounty_usd,
        product_types=program.product_types,
        templates=program.templates,
        catalog_analogue=program.catalog_analogue,
        poc_required=program.poc_required,
        kyc_required=program.kyc_required,
        live=program.live,
        primacy_of_impact=program.primacy_of_impact,
        triaged=program.triaged,
        immunefi_slug=program.slug,
        notes=program.notes,
    )


def list_programs(
    *,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    live_only: bool = True,
) -> list[ImmunefiProgram]:
    """Filter curated Immunefi programs."""
    out: list[ImmunefiProgram] = []
    for program in IMMUNEFI_PROGRAMS:
        if live_only and not program.live:
            continue
        if program.max_bounty_usd < min_max_bounty_usd:
            continue
        if ecosystem and program.ecosystem != ecosystem.lower():
            continue
        out.append(program)
    return sorted(out, key=lambda p: p.max_bounty_usd, reverse=True)


def program_to_live_target(program: ImmunefiProgram) -> LiveTarget:
    """Convert Immunefi program metadata to a LiveTarget for engine scans."""
    chain = "solana" if program.ecosystem == "solana" else "evm"
    rpc = "SOLANA_MAINNET_RPC_URL" if chain == "solana" else "ETHEREUM_RPC_URL"
    return LiveTarget(
        target_id=program.slug,
        protocol_name=program.name,
        chain=chain,
        templates=program.templates,
        rpc_env_var=rpc,
        exploit_id=program.catalog_analogue,
        immunefi_program=program.slug,
    )


def program_summary(program: ImmunefiProgram) -> dict[str, Any]:
    summary = {
        "slug": program.slug,
        "name": program.name,
        "ecosystem": program.ecosystem,
        "max_bounty_usd": program.max_bounty_usd,
        "templates": list(program.templates),
        "catalog_analogue": program.catalog_analogue,
        "url": program.url,
        "poc_required": program.poc_required,
        "kyc_required": program.kyc_required,
    }
    summary["platform"] = "immunefi"
    summary["deposit_required"] = False
    summary["cantina_id"] = None
    return summary