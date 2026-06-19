"""Evaluate controlled benchmark challenges (positive/negative EVM + Solana)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from night_shift_security.impact.measured_oracle import (
    MEASURED_DELTA_THRESHOLD,
    NativeBalanceSlot,
    PoolSlot,
    PostState,
    PreState,
    TokenBalanceSlot,
    delta as evm_delta,
)
from night_shift_security.impact.solana_measured_oracle import (
    ReserveFieldSlot,
    SolanaMeasureState,
    TokenAccountSlot,
    delta as solana_delta,
)
from night_shift_security.orchestration.bounty_loop import (
    _is_catalog_anchor_finding,
    _is_novel_finding,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = REPO_ROOT / "benchmarks" / "expected" / "manifest.json"


@dataclass
class BenchmarkResult:
    challenge_id: str
    kind: str
    passed: bool
    detail: str
    measured_impact: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "kind": self.kind,
            "passed": self.passed,
            "detail": self.detail,
            "measured_impact": self.measured_impact,
        }


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST
    payload = json.loads(manifest_path.read_text())
    if payload.get("schema_version") != "benchmarks.v1":
        raise ValueError(f"unsupported manifest schema: {payload.get('schema_version')}")
    return payload


def _resolve_fixture(rel_path: str) -> Path:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return path


def _evm_state_from_dict(data: dict[str, Any], *, tx_hash: str = "") -> PreState | PostState:
    usdc = data["attacker_eoa_usdc"]
    native = data["attacker_eoa_native"]
    pool_slots = [
        PoolSlot(
            pool_id=str(slot["pool_id"]),
            sqrt_price_x96=str(slot["sqrt_price_x96"]),
            tick=int(slot["tick"]),
            block=int(slot.get("block", 0)),
        )
        for slot in data.get("pool_slots", [])
    ]
    pm = data.get("pool_manager_native")
    pool_manager = (
        NativeBalanceSlot(holder=str(pm["holder"]), wei=str(pm["wei"])) if pm else None
    )
    common = dict(
        read_at=str(data.get("read_at", "benchmark")),
        attacker_eoa_native=NativeBalanceSlot(
            holder=str(native["holder"]),
            wei=str(native["wei"]),
        ),
        attacker_eoa_usdc=TokenBalanceSlot(
            token=str(usdc["token"]),
            holder=str(usdc["holder"]),
            raw_units=str(usdc["raw_units"]),
            decimals=int(usdc.get("decimals", 6)),
        ),
        pool_manager_native=pool_manager,
        pool_slots=pool_slots,
        block=data.get("block", "latest"),
    )
    if tx_hash:
        return PostState(**common, tx_hash=tx_hash)
    return PreState(**common)


def _solana_state_from_dict(data: dict[str, Any]) -> SolanaMeasureState:
    reserve = data["reserve_fields"]
    return SolanaMeasureState(
        slot=int(data["slot"]),
        token_accounts=[
            TokenAccountSlot(
                pubkey=str(t["pubkey"]),
                mint=str(t.get("mint", "")),
                amount=str(t["amount"]),
                decimals=int(t.get("decimals", 6)),
            )
            for t in data.get("token_accounts", [])
        ],
        reserve_fields=ReserveFieldSlot(
            reserve_pubkey=str(reserve["reserve_pubkey"]),
            last_update_slot=str(reserve["last_update_slot"]),
            borrowed_amount_sf=str(reserve["borrowed_amount_sf"]),
            cumulative_borrow_rate=str(reserve["cumulative_borrow_rate"]),
            supply_vault_amount=str(reserve.get("supply_vault_amount", "0")),
        ),
        lamports=str(data.get("lamports", "0")),
    )


def _evaluate_evm_measured(fixture: dict[str, Any], expect_measured: bool) -> BenchmarkResult:
    challenge_id = str(fixture["challenge_id"])
    pre = _evm_state_from_dict(fixture["pre"])
    post = _evm_state_from_dict(fixture["post"], tx_hash=str(fixture.get("tx_hash", "")))
    diff = evm_delta(pre, post)
    measured = bool(diff.get("measured_impact"))
    passed = measured == expect_measured
    detail = (
        f"measured_impact={measured} expected={expect_measured} "
        f"usdc_delta={diff.get('usdc_delta_raw_units')} "
        f"threshold={MEASURED_DELTA_THRESHOLD}"
    )
    return BenchmarkResult(challenge_id, "evm_measured_delta", passed, detail, measured)


def _evaluate_solana_measured(fixture: dict[str, Any], expect_measured: bool) -> BenchmarkResult:
    challenge_id = str(fixture["challenge_id"])
    pre = _solana_state_from_dict(fixture["pre"])
    post = _solana_state_from_dict(fixture["post"])
    diff = solana_delta(pre, post)
    measured = bool(diff.get("measured_impact"))
    passed = measured == expect_measured
    detail = (
        f"measured_impact={measured} expected={expect_measured} "
        f"reason={diff.get('classification_reason')}"
    )
    return BenchmarkResult(challenge_id, "solana_measured_delta", passed, detail, measured)


def _evaluate_catalog_anchor(fixture: dict[str, Any]) -> BenchmarkResult:
    challenge_id = str(fixture["challenge_id"])
    entry = fixture["finding"]
    is_anchor = _is_catalog_anchor_finding(entry)
    is_novel = _is_novel_finding(entry)
    passed = is_anchor and not is_novel
    detail = f"catalog_anchor={is_anchor} novel={is_novel}"
    return BenchmarkResult(challenge_id, "catalog_anchor_negative_control", passed, detail)


def _evaluate_analogue_proposal(fixture: dict[str, Any]) -> BenchmarkResult:
    challenge_id = str(fixture["challenge_id"])
    meta = fixture.get("metadata") or {}
    trusted = meta.get("trusted") is True
    passed = not trusted
    detail = f"metadata.trusted={meta.get('trusted')}"
    return BenchmarkResult(challenge_id, "analogue_proposal_untrusted", passed, detail)


def evaluate_challenge(challenge: dict[str, Any]) -> BenchmarkResult:
    kind = str(challenge["kind"])
    fixture_path = _resolve_fixture(str(challenge["fixture"]))
    fixture = json.loads(fixture_path.read_text())
    fixture.setdefault("challenge_id", challenge["id"])

    if kind == "evm_positive":
        return _evaluate_evm_measured(fixture, expect_measured=True)
    if kind == "evm_negative":
        return _evaluate_evm_measured(fixture, expect_measured=False)
    if kind == "solana_positive":
        return _evaluate_solana_measured(fixture, expect_measured=True)
    if kind == "solana_negative":
        return _evaluate_solana_measured(fixture, expect_measured=False)
    if kind == "catalog_anchor":
        return _evaluate_catalog_anchor(fixture)
    if kind == "analogue_proposal":
        return _evaluate_analogue_proposal(fixture)
    raise ValueError(f"unknown benchmark kind: {kind}")


def evaluate_all(manifest_path: Path | None = None) -> list[BenchmarkResult]:
    manifest = load_manifest(manifest_path)
    return [evaluate_challenge(c) for c in manifest.get("challenges", [])]