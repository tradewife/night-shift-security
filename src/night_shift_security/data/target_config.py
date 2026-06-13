"""Live-target configuration — point the engine at a specific protocol."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.recon import merge_recon_into_target_config
from night_shift_security.data.schemas import ContractState, ExploitRecord


@dataclass(frozen=True)
class LiveTarget:
    """A fork-friendly protocol target for scoped research runs."""

    target_id: str
    protocol_name: str
    chain: str
    templates: tuple[str, ...]
    rpc_env_var: str
    exploit_id: str = ""
    immunefi_program: str = ""
    chain_id: int = 1
    block_number: int = 0
    slot: int = 0
    contract_address: str = ""
    program_id: str = ""
    state_overrides: dict[str, Any] = field(default_factory=dict)


def _coerce_target(raw: dict[str, Any]) -> LiveTarget:
    templates = raw.get("templates") or []
    if isinstance(templates, str):
        templates = [templates]
    return LiveTarget(
        target_id=str(raw["target_id"]),
        protocol_name=str(raw.get("protocol_name", raw["target_id"])),
        chain=str(raw.get("chain", "evm")).lower(),
        templates=tuple(str(t) for t in templates),
        rpc_env_var=str(raw.get("rpc_env_var", "ETHEREUM_RPC_URL")),
        exploit_id=str(raw.get("exploit_id", "")),
        immunefi_program=str(raw.get("immunefi_program", "")),
        chain_id=int(raw.get("chain_id", 1)),
        block_number=int(raw.get("block_number", 0)),
        slot=int(raw.get("slot", 0)),
        contract_address=str(raw.get("contract_address", "")),
        program_id=str(raw.get("program_id", "")),
        state_overrides=dict(raw.get("state_overrides", {})),
    )


def load_live_target(config: dict[str, Any]) -> LiveTarget | None:
    """Load an enabled live target from pipeline config."""
    section = config.get("target") or {}
    if not section.get("enabled"):
        return None

    if section.get("config_path"):
        path = Path(str(section["config_path"]))
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / "config" / "targets" / path.name
        with open(path) as f:
            section = {**json.load(f), "enabled": True}

    if not section.get("target_id"):
        return None
    section = merge_recon_into_target_config(section)
    return _coerce_target(section)


_CONTRACT_STATE_KEYS = frozenset(f.name for f in fields(ContractState))


def _contract_state_data(base: ContractState, overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge overrides into ContractState, dropping recon/metadata-only keys."""
    merged = {**base.__dict__, **overrides}
    merged.pop("metadata", None)
    return {k: v for k, v in merged.items() if k in _CONTRACT_STATE_KEYS}


def resolve_target_exploit(target: LiveTarget, catalog: list[ExploitRecord] | None = None) -> ExploitRecord | None:
    """Return catalog exploit record linked to this target, if any."""
    if not target.exploit_id:
        return None
    catalog = catalog or get_exploit_catalog()
    for exploit in catalog:
        if exploit.exploit_id == target.exploit_id:
            return exploit
    return None


def resolve_target_states(
    target: LiveTarget,
    catalog: list[ExploitRecord] | None = None,
) -> list[ContractState]:
    """
    Contract states for target-scoped evaluation.

    Uses catalog exploit state when exploit_id is set; otherwise builds a generic
    state from state_overrides with protocol_id = target_id.
    """
    exploit = resolve_target_exploit(target, catalog)
    if exploit is not None:
        state = exploit.state
        if target.state_overrides:
            data = _contract_state_data(state, target.state_overrides)
            data["protocol_id"] = target.target_id
            return [ContractState(**data)]
        return [ContractState(**{**state.__dict__, "protocol_id": target.target_id})]

    base = ContractState(protocol_id=target.target_id)
    if target.state_overrides:
        return [ContractState(**_contract_state_data(base, target.state_overrides))]
    return [base]


def scoped_template_ids(target: LiveTarget, config: dict[str, Any]) -> list[str]:
    """Template list for a target run — intersection of config.templates and target.templates."""
    config_templates = list(config.get("templates", []))
    target_templates = list(target.templates) if target.templates else config_templates
    if config_templates:
        return [t for t in target_templates if t in config_templates]
    return target_templates


def target_fork_ids(target: LiveTarget) -> list[str]:
    """Fork validation target ids to prioritize for this live target."""
    if target.exploit_id:
        return [target.exploit_id]
    return [target.target_id]


def target_summary(target: LiveTarget) -> dict[str, Any]:
    """Serializable summary for run reports."""
    return {
        "target_id": target.target_id,
        "protocol_name": target.protocol_name,
        "chain": target.chain,
        "exploit_id": target.exploit_id,
        "templates": list(target.templates),
        "immunefi_program": target.immunefi_program,
        "block_number": target.block_number,
        "slot": target.slot,
        "contract_address": target.contract_address,
        "program_id": target.program_id,
    }