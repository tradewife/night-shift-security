"""KLend harness depth probes — oracle/borrow invariant seeds (Block A depth)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

KLEND_PROGRAM = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
KVAULT_PROGRAM = "KvauGMspG5k6rtzrqqn7WNn3oZdyKqLKwK2XWQ8FLjd"
ORACLE_PROGRAM = "HFn8GnPADiny6XqUoWE8uRPPxb29ikn4yTuPa9MF2fWJ"


@dataclass(frozen=True)
class KlendProbe:
    probe_id: str
    invariant_id: str
    description: str
    impact_lamports: int
    impact_usd: float
    param_overrides: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Non-catalogue probe matrix — fixture/live harness emits DELTA_LAMPORTS per probe.
KLEND_PROBES: tuple[KlendProbe, ...] = (
    KlendProbe(
        probe_id="oracle_staleness_borrow",
        invariant_id="oracle_staleness_bound",
        description="Stale oracle price enables undercollateralized borrow",
        impact_lamports=50_000_000_000,
        impact_usd=7_500_000.0,
        param_overrides={"oracle_staleness_slots": 120, "borrow_utilization": 0.85},
    ),
    KlendProbe(
        probe_id="flash_loan_collateral_loop",
        invariant_id="flash_loan_atomicity",
        description="Flash loan + thin-pair oracle manipulation loop",
        impact_lamports=80_000_000_000,
        impact_usd=12_000_000.0,
        param_overrides={"flash_loan_usd": 5_000_000, "oracle_manipulable": True},
    ),
    KlendProbe(
        probe_id="reserve_isolation_drain",
        invariant_id="reserve_isolation",
        description="Mispriced collateral drains isolated reserve liquidity",
        impact_lamports=33_333_333_333,
        impact_usd=5_000_000.0,
        param_overrides={"reserve_isolation_bypass": True},
    ),
    KlendProbe(
        probe_id="liquidation_solvency_gap",
        invariant_id="liquidation_solvency",
        description="Liquidation path leaves protocol under-reserved",
        impact_lamports=40_000_000_000,
        impact_usd=6_000_000.0,
        param_overrides={"liquidation_discount": 0.12},
    ),
)


def get_probe(probe_id: str) -> KlendProbe | None:
    for probe in KLEND_PROBES:
        if probe.probe_id == probe_id:
            return probe
    return None


def list_probes() -> list[dict[str, Any]]:
    return [p.to_dict() for p in KLEND_PROBES]