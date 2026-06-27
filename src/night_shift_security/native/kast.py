"""KAST / M0 Solana M Extensions sidecar harness helpers.

This is a lightweight static-first companion to the full Crucible campaign.
It provides:

- pinned program / variant metadata
- source-manifest and IDL loading
- variant feature validation matching `programs/m_ext/src/lib.rs`
- variant-specific discriminator lookup from exported IDLs
- simple accounting helpers for scaled-ui and crank fee/yield conservation
"""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

HARNESS_TARGET = "kast"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "solana"
HARNESS_NAME = "KAST M0 Solana M Extensions"
HARNESS_VERSION = "v6.27.0-session28"

M_EXT_PROGRAM = "3C865D264L4NkAm78zfnDzQJJvXuU3fMjRUvRxyPi5da"
EXT_SWAP_PROGRAM = "MSwapi3WhNKMUGm9YrxGhypgUEt7wYQH3ZgG32XoWzH"
EARN_PROGRAM = "mz2vDzjbQDUDXBH6FPF5s4odCJ4y8YLE5QWaZ8XdZ9Z"
WM_EXTENSION = "wMXX1K1nca5W4pZr1piETe78gcAVVrEFi9f4g46uXko"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
INDEX_SCALE_U64 = 1_000_000_000_000
ONE_HUNDRED_PERCENT_U64 = 10_000

YIELD_FEATURES: tuple[str, ...] = ("scaled-ui", "no-yield", "crank")

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = _REPO_ROOT / "sources" / "kast" / "source_manifest.json"
DEFAULT_IDL_DIR = _REPO_ROOT / "sources" / "kast" / "idls"
DEFAULT_DEPLOY_DIR = _REPO_ROOT / "sources" / "kast" / "target" / "deploy"
DEFAULT_TYPES_DIR = _REPO_ROOT / "sources" / "kast" / "types"


@dataclass(frozen=True)
class VariantBuild:
    name: str
    program_id: str
    features: tuple[str, ...]
    so_path: Path
    idl_path: Path
    types_path: Path
    primary_surface: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "program_id": self.program_id,
            "features": list(self.features),
            "so_path": str(self.so_path),
            "idl_path": str(self.idl_path),
            "types_path": str(self.types_path),
            "primary_surface": self.primary_surface,
        }


@dataclass(frozen=True)
class YieldBreakdown:
    before: int
    after: int
    gross_yield: int
    fee_bps: int
    fee_amount: int
    distributable: int

    def to_dict(self) -> dict[str, int]:
        return {
            "before": self.before,
            "after": self.after,
            "gross_yield": self.gross_yield,
            "fee_bps": self.fee_bps,
            "fee_amount": self.fee_amount,
            "distributable": self.distributable,
        }


@dataclass(frozen=True)
class SyncOutcome:
    previous_ext_index: int
    previous_m_index: int
    current_m_index: int
    new_ext_index: int
    vault_initialized: bool


@dataclass(frozen=True)
class CrankClaimOutcome:
    snapshot_balance: int
    last_claim_index: int
    global_index: int
    rewards: int
    fee_bps: int
    fee_amount: int
    distributable: int


@dataclass(frozen=True)
class EarnerState:
    user: str
    user_token_account: str
    earn_manager: str
    last_claim_index: int
    last_claim_timestamp: int
    recipient_token_account: str | None = None


def _variant_builds() -> dict[str, VariantBuild]:
    return {
        "ext_swap_migrate": VariantBuild(
            name="ext_swap_migrate",
            program_id=EXT_SWAP_PROGRAM,
            features=("migrate",),
            so_path=DEFAULT_DEPLOY_DIR / "ext_swap.so",
            idl_path=DEFAULT_IDL_DIR / "ext_swap.json",
            types_path=DEFAULT_TYPES_DIR / "ext_swap.ts",
            primary_surface="whitelisted 1:1 extension swap router",
        ),
        "m_ext_scaled_ui": VariantBuild(
            name="m_ext_scaled_ui",
            program_id=M_EXT_PROGRAM,
            features=("scaled-ui",),
            so_path=DEFAULT_DEPLOY_DIR / "m_ext_scaled_ui.so",
            idl_path=DEFAULT_IDL_DIR / "m_ext_scaled_ui.json",
            types_path=DEFAULT_TYPES_DIR / "m_ext_scaled_ui.ts",
            primary_surface="scaled-ui rebasing and fee accounting",
        ),
        "m_ext_no_yield": VariantBuild(
            name="m_ext_no_yield",
            program_id=M_EXT_PROGRAM,
            features=("no-yield",),
            so_path=DEFAULT_DEPLOY_DIR / "m_ext_no_yield.so",
            idl_path=DEFAULT_IDL_DIR / "m_ext_no_yield.json",
            types_path=DEFAULT_TYPES_DIR / "m_ext_no_yield.ts",
            primary_surface="non-rebasing fee claim accounting",
        ),
        "m_ext_crank": VariantBuild(
            name="m_ext_crank",
            program_id=M_EXT_PROGRAM,
            features=("crank",),
            so_path=DEFAULT_DEPLOY_DIR / "m_ext_crank.so",
            idl_path=DEFAULT_IDL_DIR / "m_ext_crank.json",
            types_path=DEFAULT_TYPES_DIR / "m_ext_crank.ts",
            primary_surface="earn manager / earner lifecycle and claim ordering",
        ),
        "m_ext_no_yield_migrate": VariantBuild(
            name="m_ext_no_yield_migrate",
            program_id=M_EXT_PROGRAM,
            features=("no-yield", "migrate"),
            so_path=DEFAULT_DEPLOY_DIR / "m_ext_no_yield_migrate.so",
            idl_path=DEFAULT_IDL_DIR / "m_ext_no_yield_migrate.json",
            types_path=DEFAULT_TYPES_DIR / "m_ext_no_yield_migrate.ts",
            primary_surface="migration path for no-yield v1 to v2",
        ),
    }


VARIANT_BUILDS = _variant_builds()


def program_ids() -> dict[str, str]:
    return {
        "m_ext": M_EXT_PROGRAM,
        "ext_swap": EXT_SWAP_PROGRAM,
        "earn_program": EARN_PROGRAM,
        "wm_extension": WM_EXTENSION,
        "system": SYSTEM_PROGRAM,
    }


def variant_builds() -> dict[str, VariantBuild]:
    return dict(VARIANT_BUILDS)


def load_manifest(path: Path | str | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else DEFAULT_MANIFEST_PATH
    if not manifest_path.is_file():
        return {
            "target": HARNESS_TARGET,
            "name": HARNESS_NAME,
            "source_path_defaulted": True,
            "programs": program_ids(),
        }
    try:
        payload = json.loads(manifest_path.read_text())
    except (OSError, ValueError):
        return {
            "target": HARNESS_TARGET,
            "name": HARNESS_NAME,
            "source_path_defaulted": True,
            "programs": program_ids(),
        }
    payload["source_path_defaulted"] = False
    return payload


def validate_feature_flags(features: Iterable[str]) -> str:
    feature_set = set(features)
    yield_enabled = [name for name in YIELD_FEATURES if name in feature_set]
    if not yield_enabled:
        raise ValueError("no_yield_feature_enabled")
    if len(yield_enabled) > 1:
        raise ValueError("multiple_yield_features_enabled")
    if "migrate" in feature_set and "crank" in feature_set and "wm" not in feature_set:
        raise ValueError("invalid_crank_migrate_without_wm")
    return yield_enabled[0]


def load_idl(variant: str = "m_ext_no_yield", base_dir: Path | str | None = None) -> dict[str, Any]:
    if variant not in VARIANT_BUILDS:
        raise KeyError(f"unknown_variant:{variant}")
    root = Path(base_dir) if base_dir is not None else DEFAULT_IDL_DIR
    idl_path = root / VARIANT_BUILDS[variant].idl_path.name
    try:
        return json.loads(idl_path.read_text())
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"idl_unavailable:{variant}") from exc


def instruction_names(variant: str = "m_ext_no_yield") -> list[str]:
    return [instr["name"] for instr in load_idl(variant).get("instructions", [])]


def discriminators(variant: str = "m_ext_no_yield") -> OrderedDict[str, str]:
    idl = load_idl(variant)
    result: OrderedDict[str, str] = OrderedDict()
    for instr in idl.get("instructions", []):
        disc = instr.get("discriminator")
        if not isinstance(disc, list) or len(disc) != 8:
            continue
        result[instr["name"]] = "0x" + "".join(f"{b:02x}" for b in disc)
    return result


def union_instruction_names() -> list[str]:
    names: set[str] = set()
    for variant in VARIANT_BUILDS:
        names.update(instruction_names(variant))
    return sorted(names)


def compute_scaled_ui_yield(before: int, after: int, fee_bps: int) -> YieldBreakdown:
    if before < 0 or after < 0:
        raise ValueError("negative_balance")
    if not 0 <= fee_bps <= 10_000:
        raise ValueError("fee_bps_out_of_range")
    if after < before:
        raise ValueError("negative_gross_yield")
    gross = after - before
    fee = gross * fee_bps // 10_000
    distributable = gross - fee
    return YieldBreakdown(
        before=before,
        after=after,
        gross_yield=gross,
        fee_bps=fee_bps,
        fee_amount=fee,
        distributable=distributable,
    )


def compute_crank_claim(claimable_yield: int, fee_bps: int) -> YieldBreakdown:
    if claimable_yield < 0:
        raise ValueError("negative_claimable_yield")
    return compute_scaled_ui_yield(0, claimable_yield, fee_bps)


def pending_yield_conserved(*amounts: int) -> bool:
    return sum(amounts) >= 0


def amount_to_principal_down(amount: int, index: int) -> int:
    if amount < 0 or index <= 0:
        raise ValueError("invalid_amount_or_index")
    if index == INDEX_SCALE_U64:
        return amount
    return amount * INDEX_SCALE_U64 // index


def principal_to_amount_down(principal: int, index: int) -> int:
    if principal < 0 or index <= 0:
        raise ValueError("invalid_principal_or_index")
    if index == INDEX_SCALE_U64:
        return principal
    return principal * index // INDEX_SCALE_U64


def principal_to_amount_up(principal: int, index: int) -> int:
    if principal < 0 or index <= 0:
        raise ValueError("invalid_principal_or_index")
    if index == INDEX_SCALE_U64:
        return principal
    numer = principal * index
    return (numer + INDEX_SCALE_U64 - 1) // INDEX_SCALE_U64


def compute_sync_outcome(
    previous_ext_index: int,
    previous_m_index: int,
    current_m_index: int,
    *,
    vault_initialized: bool = True,
) -> SyncOutcome:
    if min(previous_ext_index, previous_m_index, current_m_index) <= 0:
        raise ValueError("non_positive_index")
    new_ext_index = previous_ext_index
    if vault_initialized:
        new_ext_index = previous_ext_index * current_m_index // previous_m_index
    return SyncOutcome(
        previous_ext_index=previous_ext_index,
        previous_m_index=previous_m_index,
        current_m_index=current_m_index,
        new_ext_index=new_ext_index,
        vault_initialized=vault_initialized,
    )


def compute_crank_claim_outcome(
    *,
    snapshot_balance: int,
    last_claim_index: int,
    global_index: int,
    fee_bps: int,
    ext_supply: int | None = None,
    ext_collateral: int | None = None,
    manager_active: bool = True,
) -> CrankClaimOutcome:
    if snapshot_balance < 0:
        raise ValueError("negative_snapshot_balance")
    if min(last_claim_index, global_index) <= 0:
        raise ValueError("non_positive_index")
    if not 0 <= fee_bps <= ONE_HUNDRED_PERCENT_U64:
        raise ValueError("fee_bps_out_of_range")
    if last_claim_index >= global_index:
        raise ValueError("already_claimed_or_frozen")
    rewards = (snapshot_balance * global_index) // last_claim_index - snapshot_balance
    if rewards < 0:
        raise ValueError("negative_rewards")
    if ext_supply is not None and ext_collateral is not None and ext_supply + rewards > ext_collateral:
        raise ValueError("insufficient_collateral")
    fee = rewards * fee_bps // ONE_HUNDRED_PERCENT_U64 if manager_active else 0
    distributable = rewards - fee
    return CrankClaimOutcome(
        snapshot_balance=snapshot_balance,
        last_claim_index=last_claim_index,
        global_index=global_index,
        rewards=rewards,
        fee_bps=fee_bps,
        fee_amount=fee,
        distributable=distributable,
    )


def compute_claim_fees_principal(
    *,
    vault_principal: int,
    ext_supply_principal: int,
    ext_index: int,
    m_index: int,
) -> int:
    if min(vault_principal, ext_supply_principal, ext_index, m_index) < 0:
        raise ValueError("negative_input")
    required_m = principal_to_amount_up(ext_supply_principal, ext_index)
    vault_m = principal_to_amount_down(vault_principal, m_index)
    excess = vault_m - required_m
    if excess <= 0:
        return 0
    return amount_to_principal_down(excess, ext_index)


def transfer_earner_state(state: EarnerState, to_earn_manager: str) -> EarnerState:
    if not to_earn_manager:
        raise ValueError("missing_to_earn_manager")
    return EarnerState(
        user=state.user,
        user_token_account=state.user_token_account,
        earn_manager=to_earn_manager,
        last_claim_index=state.last_claim_index,
        last_claim_timestamp=state.last_claim_timestamp,
        recipient_token_account=state.recipient_token_account,
    )


def set_recipient_state(state: EarnerState, recipient_token_account: str | None) -> EarnerState:
    return EarnerState(
        user=state.user,
        user_token_account=state.user_token_account,
        earn_manager=state.earn_manager,
        last_claim_index=state.last_claim_index,
        last_claim_timestamp=state.last_claim_timestamp,
        recipient_token_account=recipient_token_account,
    )


def detect_authority_role_collisions(roles: dict[str, str | None]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for role, actor in roles.items():
        if not actor:
            continue
        grouped.setdefault(actor, []).append(role)
    return {actor: assigned for actor, assigned in grouped.items() if len(assigned) > 1}


__all__ = [
    "amount_to_principal_down",
    "compute_claim_fees_principal",
    "compute_crank_claim_outcome",
    "DEFAULT_DEPLOY_DIR",
    "DEFAULT_IDL_DIR",
    "DEFAULT_MANIFEST_PATH",
    "DEFAULT_TYPES_DIR",
    "EARN_PROGRAM",
    "EarnerState",
    "EXT_SWAP_PROGRAM",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "HARNESS_VERSION",
    "INDEX_SCALE_U64",
    "M_EXT_PROGRAM",
    "ONE_HUNDRED_PERCENT_U64",
    "CrankClaimOutcome",
    "SyncOutcome",
    "SYSTEM_PROGRAM",
    "VARIANT_BUILDS",
    "VariantBuild",
    "WM_EXTENSION",
    "YIELD_FEATURES",
    "YieldBreakdown",
    "compute_crank_claim",
    "compute_sync_outcome",
    "compute_scaled_ui_yield",
    "detect_authority_role_collisions",
    "discriminators",
    "instruction_names",
    "load_idl",
    "load_manifest",
    "pending_yield_conserved",
    "principal_to_amount_down",
    "principal_to_amount_up",
    "program_ids",
    "set_recipient_state",
    "transfer_earner_state",
    "union_instruction_names",
    "validate_feature_flags",
    "variant_builds",
]
