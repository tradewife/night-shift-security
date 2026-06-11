"""Unified bounty program metadata — Immunefi, Cantina, and future platforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from night_shift_security.data.target_config import LiveTarget

Platform = Literal["immunefi", "cantina"]


@dataclass(frozen=True)
class BountyProgram:
    """A live bug bounty program NSS can probe with catalogue analogues."""

    platform: Platform
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
    notes: str = ""
    cantina_id: str = ""
    deposit_required: bool = False

    @property
    def url(self) -> str:
        if self.platform == "cantina" and self.cantina_id:
            return f"https://cantina.xyz/bounties/{self.cantina_id}"
        return f"https://immunefi.com/bug-bounty/{self.slug}/information/"


def program_to_live_target(program: BountyProgram) -> LiveTarget:
    """Convert bounty program metadata to a LiveTarget for engine scans."""
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


def program_summary(program: BountyProgram) -> dict[str, Any]:
    return {
        "platform": program.platform,
        "slug": program.slug,
        "name": program.name,
        "ecosystem": program.ecosystem,
        "max_bounty_usd": program.max_bounty_usd,
        "templates": list(program.templates),
        "catalog_analogue": program.catalog_analogue,
        "url": program.url,
        "poc_required": program.poc_required,
        "kyc_required": program.kyc_required,
        "deposit_required": program.deposit_required,
        "cantina_id": program.cantina_id or None,
    }


def list_bounty_programs(
    programs: tuple[BountyProgram, ...],
    *,
    platform: Platform | None = None,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    live_only: bool = True,
) -> list[BountyProgram]:
    out: list[BountyProgram] = []
    for program in programs:
        if live_only and not program.live:
            continue
        if platform and program.platform != platform:
            continue
        if program.max_bounty_usd < min_max_bounty_usd:
            continue
        if ecosystem and program.ecosystem != ecosystem.lower():
            continue
        out.append(program)
    return sorted(out, key=lambda p: p.max_bounty_usd, reverse=True)