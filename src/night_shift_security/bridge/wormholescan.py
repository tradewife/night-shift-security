"""Wormholescan helpers for signed VAA replay probes."""

from __future__ import annotations

import base64
import binascii
import json
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

WORMHOLESCAN_BASE_URL = "https://api.wormholescan.io/api/v1"
DEFAULT_REAL_VAA_PATH = Path("data/security_results/wormhole/real_vaas/latest_eth_native_release.json")


@dataclass(frozen=True)
class DecodedVAA:
    emitter_chain: int
    emitter_address: str
    sequence: int
    payload_id: int
    amount: int
    token_chain: int
    token_address: str
    to_chain: int
    to_address: str
    raw_hex: str


def _vaa_body(raw: bytes) -> bytes:
    if len(raw) < 6:
        raise ValueError("vaa_too_short")
    signature_count = raw[5]
    body_offset = 6 + 66 * signature_count
    if len(raw) <= body_offset + 51:
        raise ValueError("vaa_body_too_short")
    return raw[body_offset:]


def decode_token_bridge_vaa(raw_b64: str) -> DecodedVAA:
    raw = base64.b64decode(raw_b64)
    body = _vaa_body(raw)
    payload = body[51:]
    if len(payload) < 101:
        raise ValueError("payload_too_short")
    payload_id = payload[0]
    if payload_id not in (1, 3):
        raise ValueError(f"unsupported_payload_id:{payload_id}")
    return DecodedVAA(
        emitter_chain=int.from_bytes(body[8:10], "big"),
        emitter_address=body[10:42].hex(),
        sequence=int.from_bytes(body[42:50], "big"),
        payload_id=payload_id,
        amount=int.from_bytes(payload[1:33], "big"),
        token_address=payload[33:65].hex(),
        token_chain=int.from_bytes(payload[65:67], "big"),
        to_address=payload[67:99].hex(),
        to_chain=int.from_bytes(payload[99:101], "big"),
        raw_hex="0x" + raw.hex(),
    )


def fetch_operations(limit: int = 100, base_url: str = WORMHOLESCAN_BASE_URL) -> list[dict[str, Any]]:
    url = f"{base_url}/operations?limit={int(limit)}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        payload = json.loads(resp.read().decode())
    operations = payload.get("operations") if isinstance(payload, dict) else None
    return operations if isinstance(operations, list) else []


def select_eth_native_release_vaa(operations: list[dict[str, Any]]) -> dict[str, Any] | None:
    for op in operations:
        raw = ((op.get("vaa") or {}).get("raw")) if isinstance(op, dict) else None
        if not isinstance(raw, str):
            continue
        try:
            decoded = decode_token_bridge_vaa(raw)
        except (ValueError, binascii.Error):
            continue
        if decoded.token_chain == 2 and decoded.to_chain == 2:
            return {
                "id": op.get("id") or "",
                "decoded": asdict(decoded),
                "source_chain": op.get("sourceChain") or {},
                "target_chain": op.get("targetChain") or {},
            }
    return None


def write_latest_eth_native_release_vaa(
    out_path: Path = DEFAULT_REAL_VAA_PATH,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    selected = select_eth_native_release_vaa(fetch_operations(limit=limit))
    if not selected:
        return {"ok": False, "reason": "no_matching_vaa", "path": str(out_path)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ok": True, **selected}
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return {"ok": True, "path": str(out_path), "id": selected["id"]}
