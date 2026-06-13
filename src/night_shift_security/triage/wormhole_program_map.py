"""Map live Wormhole EVM/Solana program IDs — Block B (not Nomad proxy analogue)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Official mainnet addresses — wormhole.com/docs/products/reference/contract-addresses/
WORMHOLE_CANONICAL: dict[str, dict[str, str]] = {
    "core": {
        "ethereum": "0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B",
        "solana": "worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth",
        "arbitrum": "0xa5f208e072434bC67592E4C49C1B991BA79BCA46",
        "base": "0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6",
        "polygon": "0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7",
    },
    "token_bridge": {
        "ethereum": "0x3ee18B2214AFF97000D974cf647E7C347E8fa585",
        "solana": "wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb",
    },
    "executor": {
        "ethereum": "0x84EEe8dBa37C36947397E1E11251cA9A06Fc6F8a",
        "solana": "execXUrAsMnqMmTHj5m7N1YQgsDz3cwGLYCYyuDRciV",
    },
    "settlement_router": {
        "ethereum": "0x70287c79ee41C5D1df8259Cd68Ba0890cd389c47",
        "solana": "28topqjtJzMnPaGFmmZk68tzGmj9W9aMntaEK3QkgtRe",
    },
}

_EVM_ADDR = re.compile(r"0x[a-fA-F0-9]{40}")
_SOL_ADDR = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}")
_DECLARE_ID = re.compile(
    r'declare_id!\s*\(\s*["\']([1-9A-HJ-NP-Za-km-z]{32,44})["\']\s*\)'
)
_PROGRAM_ID = re.compile(
    r'program_id\s*[=:]\s*["\']([1-9A-HJ-NP-Za-km-z]{32,44})["\']',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DiscoveredProgram:
    address: str
    chain: str
    source_file: str
    signal: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_repo_for_program_ids(repo_root: Path) -> list[DiscoveredProgram]:
    """Heuristic scan for Wormhole-relevant program/contract IDs in a cloned repo."""
    root = repo_root.resolve()
    if not root.is_dir():
        return []

    discovered: list[DiscoveredProgram] = []
    seen: set[tuple[str, str]] = set()

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".rs", ".sol", ".ts", ".js", ".go", ".md", ".toml"}:
            continue
        rel = str(path.relative_to(root))
        if any(part in {".git", "node_modules", "target", "dist"} for part in path.parts):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue

        lowered = rel.lower()
        wormhole_context = any(
            kw in lowered or kw in text.lower()
            for kw in ("wormhole", "token_bridge", "core_bridge", "executor", "portal")
        )
        if not wormhole_context:
            continue

        for match in _DECLARE_ID.finditer(text):
            addr = match.group(1)
            key = (addr, rel)
            if key not in seen:
                seen.add(key)
                discovered.append(
                    DiscoveredProgram(addr, "solana", rel, "declare_id!")
                )

        for match in _PROGRAM_ID.finditer(text):
            addr = match.group(1)
            key = (addr, rel)
            if key not in seen:
                seen.add(key)
                discovered.append(
                    DiscoveredProgram(addr, "solana", rel, "program_id")
                )

        for match in _EVM_ADDR.finditer(text):
            addr = match.group(0)
            key = (addr.lower(), rel)
            if key not in seen:
                seen.add(key)
                discovered.append(
                    DiscoveredProgram(addr, "evm", rel, "hex_address")
                )

        for match in _SOL_ADDR.finditer(text):
            addr = match.group(0)
            if len(addr) < 32:
                continue
            key = (addr, rel)
            if key not in seen and addr not in {p.address for p in discovered}:
                seen.add(key)
                discovered.append(
                    DiscoveredProgram(addr, "solana", rel, "base58")
                )

    return discovered


def build_wormhole_map(
    *,
    repo_root: Path | None = None,
    canonical: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    canon = canonical or WORMHOLE_CANONICAL
    scanned: list[dict[str, Any]] = []
    if repo_root and repo_root.is_dir():
        scanned = [p.to_dict() for p in scan_repo_for_program_ids(repo_root)]

    canonical_flat = {
        f"{component}_{chain}": addr
        for component, chains in canon.items()
        for chain, addr in chains.items()
    }

    return {
        "target_id": "wormhole",
        "catalog_analogue": "nomad-bridge-2022",
        "note": "Live Wormhole program IDs — not Nomad proxy; catalogue used for zero-RPC validation only",
        "canonical": canon,
        "canonical_flat": canonical_flat,
        "discovered": scanned,
        "discovered_count": len(scanned),
        "primary_programs": {
            "core_ethereum": canon["core"]["ethereum"],
            "core_solana": canon["core"]["solana"],
            "token_bridge_ethereum": canon["token_bridge"]["ethereum"],
            "token_bridge_solana": canon["token_bridge"]["solana"],
        },
    }


def write_wormhole_recon(
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Write sources/wormhole/recon.json with live program map + invariants."""
    program_map = build_wormhole_map(repo_root=repo_root)
    payload = {
        "target_id": "wormhole",
        "protocol_name": "Wormhole",
        "chain": "multichain",
        "recon_version": "1.0",
        "catalog_analogue": "nomad-bridge-2022",
        "programs": program_map["primary_programs"],
        "program_map": program_map,
        "invariants": [
            {
                "id": "guardian_set_integrity",
                "description": "Only authorized guardian signatures may attest VAAs",
            },
            {
                "id": "emitter_sequence_monotonic",
                "description": "Cross-chain message sequences must not replay or skip",
            },
            {
                "id": "token_bridge_accounting",
                "description": "Bridged assets must be fully backed on source chain",
            },
            {
                "id": "executor_authorization",
                "description": "Executor may only fulfill signed, unconsumed VAAs",
            },
            {
                "id": "access_control_escalation_bound",
                "description": "Admin/owner paths must not grant unilateral bridge drain",
            },
        ],
        "threat_model": {
            "primary_surfaces": [
                "access_control_escalation",
                "composability_risk",
                "message_replay",
            ],
            "assumptions": [
                "Nomad proxy analogue is validation-only — novel work targets core/token_bridge",
                "Solana CPI surfaces differ from EVM proxy patterns",
                "No mainnet destructive probing without human gate",
            ],
            "exclude_analogue": "nomad-bridge-2022-proxy",
        },
        "state_hints": {
            "max_bounty_usd": 5_000_000,
            "chains": ["ethereum", "solana", "arbitrum", "base", "polygon"],
            "product_type": "bridge",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload