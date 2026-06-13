"""Task verifier — balance-delta ground truth for operator exploit confirmation."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class VerifierResult:
    passed: bool
    balance_before_wei: int
    balance_after_wei: int
    delta_wei: int
    threshold_wei: int
    method: str  # forge_output | catalog_exempt | disabled | solana_stub

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_threshold_lamports(config: dict[str, Any] | None) -> int:
    cfg = config or {}
    raw = cfg.get("threshold_lamports", "100000000")
    if isinstance(raw, int):
        return raw
    return int(str(raw).replace("_", "").strip())


def parse_threshold_wei(config: dict[str, Any] | None) -> int:
    cfg = config or {}
    raw = cfg.get("threshold_wei", "100000000000000000")
    if isinstance(raw, int):
        return raw
    return int(str(raw).strip())


def _parse_int_field(output: str, name: str) -> int | None:
    match = re.search(rf"{name}:(-?\d+)", output)
    if match:
        return int(match.group(1))
    return None


def verify_from_forge_output(
    output: str,
    config: dict[str, Any] | None = None,
    *,
    catalog_exempt: bool = False,
) -> VerifierResult:
    """
    Parse forge stdout/stderr for balance delta signals.

    PoCs may emit BALANCE_BEFORE/BALANCE_AFTER/DELTA_WEI console logs.
    Catalogue anchors are exempt when required_for_novel is set on the caller.
    """
    cfg = config or {}
    if not cfg.get("enabled", True):
        return VerifierResult(
            passed=True,
            balance_before_wei=0,
            balance_after_wei=0,
            delta_wei=0,
            threshold_wei=parse_threshold_wei(cfg),
            method="disabled",
        )

    threshold = parse_threshold_wei(cfg)

    if catalog_exempt and cfg.get("required_for_novel", True):
        return VerifierResult(
            passed=True,
            balance_before_wei=0,
            balance_after_wei=0,
            delta_wei=0,
            threshold_wei=threshold,
            method="catalog_exempt",
        )

    delta = _parse_int_field(output, "DELTA_WEI")
    before = _parse_int_field(output, "BALANCE_BEFORE")
    after = _parse_int_field(output, "BALANCE_AFTER")

    if delta is None and before is not None and after is not None:
        delta = after - before

    if delta is None:
        return VerifierResult(
            passed=False,
            balance_before_wei=before or 0,
            balance_after_wei=after or 0,
            delta_wei=0,
            threshold_wei=threshold,
            method="forge_output",
        )

    return VerifierResult(
        passed=delta >= threshold,
        balance_before_wei=before or 0,
        balance_after_wei=after or 0,
        delta_wei=delta,
        threshold_wei=threshold,
        method="forge_output",
    )


def verify_from_solana_output(
    output: str,
    config: dict[str, Any] | None = None,
    *,
    catalog_exempt: bool = False,
) -> VerifierResult:
    """Parse Solana harness output for lamport delta (DELTA_LAMPORTS or BALANCE_*)."""
    cfg = config or {}
    if not cfg.get("enabled", True):
        return VerifierResult(
            passed=True,
            balance_before_wei=0,
            balance_after_wei=0,
            delta_wei=0,
            threshold_wei=parse_threshold_lamports(cfg),
            method="disabled",
        )

    threshold = parse_threshold_lamports(cfg)
    if catalog_exempt and cfg.get("required_for_novel", True):
        return VerifierResult(
            passed=True,
            balance_before_wei=0,
            balance_after_wei=0,
            delta_wei=0,
            threshold_wei=threshold,
            method="catalog_exempt",
        )

    delta = _parse_int_field(output, "DELTA_LAMPORTS")
    before = _parse_int_field(output, "BALANCE_BEFORE")
    after = _parse_int_field(output, "BALANCE_AFTER")
    if delta is None and before is not None and after is not None:
        delta = after - before

    if delta is None:
        return VerifierResult(
            passed=False,
            balance_before_wei=before or 0,
            balance_after_wei=after or 0,
            delta_wei=0,
            threshold_wei=threshold,
            method="solana_output",
        )

    return VerifierResult(
        passed=delta >= threshold,
        balance_before_wei=before or 0,
        balance_after_wei=after or 0,
        delta_wei=delta,
        threshold_wei=threshold,
        method="solana_output",
    )


def apply_verifier_to_solana_entry(
    entry: dict[str, Any],
    verifier: VerifierResult,
    *,
    required_for_novel: bool,
    is_catalog_anchor: bool,
) -> dict[str, Any]:
    entry["balance_verified"] = verifier.passed
    entry["balance_delta_lamports"] = verifier.delta_wei
    entry["balance_threshold_lamports"] = verifier.threshold_wei
    entry["verifier_method"] = verifier.method

    if (
        entry.get("solana_reproduced")
        and required_for_novel
        and not is_catalog_anchor
        and not verifier.passed
    ):
        entry["solana_reproduced"] = False
        entry["verifier_note"] = "novel_solana_requires_lamport_delta"

    return entry


def apply_verifier_to_fork_entry(
    entry: dict[str, Any],
    verifier: VerifierResult,
    *,
    required_for_novel: bool,
    is_catalog_anchor: bool,
) -> dict[str, Any]:
    """Attach verifier fields and optionally downgrade fork_reproduced for novel paths."""
    entry["balance_verified"] = verifier.passed
    entry["balance_delta_wei"] = verifier.delta_wei
    entry["balance_threshold_wei"] = verifier.threshold_wei
    entry["verifier_method"] = verifier.method

    if (
        entry.get("fork_reproduced")
        and required_for_novel
        and not is_catalog_anchor
        and not verifier.passed
    ):
        entry["fork_reproduced"] = False
        entry["verifier_note"] = "novel_fork_requires_balance_delta"

    return entry


def _fork_verifier_applies(fork_evidence: dict[str, Any]) -> bool:
    """Verifier gate applies only when an EVM fork run recorded verifier fields."""
    if not fork_evidence:
        return False
    if fork_evidence.get("method") == "evm_fork":
        return True
    return "balance_verified" in fork_evidence


def _solana_verifier_applies(solana_evidence: dict[str, Any]) -> bool:
    if not solana_evidence:
        return False
    method = solana_evidence.get("method", "")
    if method in ("solana_validator", "solana_klend_harness"):
        return True
    return "balance_verified" in solana_evidence


def candidate_requires_balance_verifier(candidate: Any) -> bool:
    if getattr(candidate, "catalog_analogue", False):
        return False
    if getattr(candidate, "fork_reproduced", False):
        return _fork_verifier_applies(getattr(candidate, "fork_evidence", None) or {})
    if getattr(candidate, "solana_reproduced", False):
        return _solana_verifier_applies(getattr(candidate, "solana_evidence", None) or {})
    return False


def candidate_balance_verified(candidate: Any) -> bool:
    """True when fork/solana evidence records a passing verifier."""
    if not candidate_requires_balance_verifier(candidate):
        return True
    fork_ev = getattr(candidate, "fork_evidence", None) or {}
    sol_ev = getattr(candidate, "solana_evidence", None) or {}
    if fork_ev.get("balance_verified") is True:
        return True
    if sol_ev.get("balance_verified") is True:
        return True
    return False


def finding_balance_verified(finding: Any) -> bool:
    if getattr(finding, "catalog_analogue", False):
        return True
    fork_ev = getattr(finding, "fork_evidence", None) or {}
    sol_ev = getattr(finding, "solana_evidence", None) or {}
    fork_applies = getattr(finding, "fork_reproduced", False) and _fork_verifier_applies(fork_ev)
    sol_applies = getattr(finding, "solana_reproduced", False) and _solana_verifier_applies(sol_ev)
    if not fork_applies and not sol_applies:
        return True
    if fork_applies and not fork_ev.get("balance_verified"):
        return False
    if sol_applies and not sol_ev.get("balance_verified"):
        return False
    return True