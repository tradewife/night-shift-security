"""KLend harness depth probes — oracle/borrow invariant seeds (Block A depth)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

KLEND_PROGRAM = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
KVAULT_PROGRAM = "KvauGMspG5k6rtzrqqn7WNn3oZdyKqLKwK2XWQ8FLjd"
ORACLE_PROGRAM = "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


@dataclass(frozen=True)
class ProbeAccountSpec:
    pubkey: str
    is_signer: bool = False
    is_writable: bool = False
    role: str = ""


@dataclass(frozen=True)
class KlendProbe:
    probe_id: str
    invariant_id: str
    description: str
    impact_lamports: int
    impact_usd: float
    param_overrides: dict[str, Any]
    instruction_prefix: bytes
    extra_accounts: tuple[ProbeAccountSpec, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["instruction_prefix"] = self.instruction_prefix.hex()
        return payload


# Non-catalogue probe matrix — fixture/live harness emits measured deltas per probe.
KLEND_PROBES: tuple[KlendProbe, ...] = (
    KlendProbe(
        probe_id="oracle_staleness_borrow",
        invariant_id="oracle_staleness_bound",
        description="Stale oracle price enables undercollateralized borrow",
        impact_lamports=50_000_000_000,
        impact_usd=7_500_000.0,
        param_overrides={"oracle_staleness_slots": 120, "borrow_utilization": 0.85},
        instruction_prefix=bytes([0x00, 0xCA, 0xFE, 0x01]),
        extra_accounts=(
            ProbeAccountSpec(ORACLE_PROGRAM, role="oracle"),
            ProbeAccountSpec(KLEND_PROGRAM, role="lending_market_program"),
            ProbeAccountSpec(KVAULT_PROGRAM, role="vault_program"),
            ProbeAccountSpec(SYSTEM_PROGRAM, role="system_program"),
        ),
    ),
    KlendProbe(
        probe_id="flash_loan_collateral_loop",
        invariant_id="flash_loan_atomicity",
        description="Flash loan + thin-pair oracle manipulation loop",
        impact_lamports=80_000_000_000,
        impact_usd=12_000_000.0,
        param_overrides={"flash_loan_usd": 5_000_000, "oracle_manipulable": True},
        instruction_prefix=bytes([0x00, 0xCA, 0xFE, 0x02]),
        extra_accounts=(
            ProbeAccountSpec(KLEND_PROGRAM, role="lending_market_program"),
            ProbeAccountSpec(KVAULT_PROGRAM, role="vault_program"),
            ProbeAccountSpec(ORACLE_PROGRAM, role="oracle"),
            ProbeAccountSpec(SPL_TOKEN_PROGRAM, role="spl_token"),
            ProbeAccountSpec(SYSTEM_PROGRAM, role="system_program"),
        ),
    ),
    KlendProbe(
        probe_id="reserve_isolation_drain",
        invariant_id="reserve_isolation",
        description="Mispriced collateral drains isolated reserve liquidity",
        impact_lamports=33_333_333_333,
        impact_usd=5_000_000.0,
        param_overrides={"reserve_isolation_bypass": True},
        instruction_prefix=bytes([0x00, 0xCA, 0xFE, 0x03]),
        extra_accounts=(
            ProbeAccountSpec(KLEND_PROGRAM, role="lending_market_program"),
            ProbeAccountSpec(KVAULT_PROGRAM, is_writable=True, role="vault_program"),
            ProbeAccountSpec(ORACLE_PROGRAM, role="oracle"),
            ProbeAccountSpec(SYSTEM_PROGRAM, role="system_program"),
        ),
    ),
    KlendProbe(
        probe_id="liquidation_solvency_gap",
        invariant_id="liquidation_solvency",
        description="Liquidation path leaves protocol under-reserved",
        impact_lamports=40_000_000_000,
        impact_usd=6_000_000.0,
        param_overrides={"liquidation_discount": 0.12},
        instruction_prefix=bytes([0x00, 0xCA, 0xFE, 0x04]),
        extra_accounts=(
            ProbeAccountSpec(KLEND_PROGRAM, role="lending_market_program"),
            ProbeAccountSpec(KVAULT_PROGRAM, role="vault_program"),
            ProbeAccountSpec(ORACLE_PROGRAM, role="oracle"),
            ProbeAccountSpec(SYSTEM_PROGRAM, role="system_program"),
        ),
    ),
)


def get_probe(probe_id: str) -> KlendProbe | None:
    for probe in KLEND_PROBES:
        if probe.probe_id == probe_id:
            return probe
    return None


def probe_instruction_data(probe_id: str) -> bytes:
    probe = get_probe(probe_id)
    if probe:
        return probe.instruction_prefix
    if probe_id == "baseline_deploy":
        return b""
    return b"\xff"


def probe_account_specs(probe_id: str) -> tuple[ProbeAccountSpec, ...]:
    probe = get_probe(probe_id)
    return probe.extra_accounts if probe else ()


def probe_accounts_summary(probe_id: str) -> str:
    return ",".join(
        f"{spec.role}:{spec.pubkey[:8]}"
        for spec in probe_account_specs(probe_id)
    )


def list_probes() -> list[dict[str, Any]]:
    return [p.to_dict() for p in KLEND_PROBES]