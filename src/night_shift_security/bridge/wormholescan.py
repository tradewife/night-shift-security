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
DEFAULT_CORPUS_REPORT_PATH = Path("data/security_results/wormhole/real_vaas/corpus_report.json")


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
    decimals: int = 0
    symbol: str = ""
    name: str = ""


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
    payload_id = payload[0]
    if payload_id == 2:
        if len(payload) != 100:
            raise ValueError("asset_meta_payload_malformed")
        return DecodedVAA(
            emitter_chain=int.from_bytes(body[8:10], "big"),
            emitter_address=body[10:42].hex(),
            sequence=int.from_bytes(body[42:50], "big"),
            payload_id=payload_id,
            amount=0,
            token_address=payload[1:33].hex(),
            token_chain=int.from_bytes(payload[33:35], "big"),
            to_address="",
            to_chain=0,
            raw_hex="0x" + raw.hex(),
            decimals=payload[35],
            symbol=payload[36:68].rstrip(b"\x00").decode(errors="replace"),
            name=payload[68:100].rstrip(b"\x00").decode(errors="replace"),
        )
    if len(payload) < 101:
        raise ValueError("payload_too_short")
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
        decoded = _decoded_operation(op)
        if decoded is None:
            continue
        if decoded.token_chain == 2 and decoded.to_chain == 2:
            return {
                "id": op.get("id") or "",
                "decoded": asdict(decoded),
                "source_chain": op.get("sourceChain") or {},
                "target_chain": op.get("targetChain") or {},
            }
    return None


def select_eth_wrapped_mint_vaa(operations: list[dict[str, Any]]) -> dict[str, Any] | None:
    for op in operations:
        selected = _selected_operation(op, route="eth_wrapped_mint")
        if selected:
            return selected
    return None


def select_asset_meta_vaa(operations: list[dict[str, Any]]) -> dict[str, Any] | None:
    for op in operations:
        selected = _selected_operation(op, route="asset_meta")
        if selected:
            return selected
    return None


def _selected_operation(op: dict[str, Any], *, route: str) -> dict[str, Any] | None:
    classified = classify_real_vaa_operation(op)
    if not classified or classified["route"] != route:
        return None
    decoded = _decoded_operation(op)
    if decoded is None:
        return None
    return {
        "id": op.get("id") or "",
        "decoded": asdict(decoded),
        "source_chain": op.get("sourceChain") or {},
        "target_chain": op.get("targetChain") or {},
    }


def _decoded_operation(op: dict[str, Any]) -> DecodedVAA | None:
    raw = ((op.get("vaa") or {}).get("raw")) if isinstance(op, dict) else None
    if not isinstance(raw, str):
        return None
    try:
        return decode_token_bridge_vaa(raw)
    except (ValueError, binascii.Error):
        return None


def classify_real_vaa_operation(op: dict[str, Any]) -> dict[str, Any] | None:
    decoded = _decoded_operation(op)
    if decoded is None:
        return None
    source_chain = decoded.emitter_chain
    route = "foreign_wrapped_mint"
    if decoded.payload_id == 2:
        route = "asset_meta"
    elif decoded.to_chain == 2 and decoded.token_chain == 2:
        route = "eth_native_release"
    elif decoded.to_chain == 2:
        route = "eth_wrapped_mint"
    elif decoded.token_chain == 2:
        route = "eth_native_lock_out"
    standardized = (op.get("content") or {}).get("standarizedProperties") or {}
    std_amount = str(standardized.get("amount") or "")
    amount_mismatch = bool(std_amount and std_amount.isdigit() and int(std_amount) != decoded.amount)
    return {
        "id": op.get("id") or "",
        "route": route,
        "emitter_chain": source_chain,
        "token_chain": decoded.token_chain,
        "to_chain": decoded.to_chain,
        "payload_id": decoded.payload_id,
        "amount": decoded.amount,
        "standardized_amount": std_amount,
        "amount_mismatch": amount_mismatch,
        "token_address": decoded.token_address,
        "to_address": decoded.to_address,
        "has_raw_vaa": True,
    }


def build_real_vaa_corpus_report(operations: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [e for op in operations if (e := classify_real_vaa_operation(op)) is not None]
    route_counts: dict[str, int] = {}
    for entry in entries:
        route = str(entry["route"])
        route_counts[route] = route_counts.get(route, 0) + 1
    interesting = [
        entry
        for entry in entries
        if entry["amount_mismatch"] or entry["route"] in {"eth_native_release", "eth_wrapped_mint"}
    ][:20]
    return {
        "operations_seen": len(operations),
        "decoded_token_bridge_vaas": len(entries),
        "route_counts": route_counts,
        "interesting": interesting,
        "selected_eth_native_release": next(
            (entry for entry in entries if entry["route"] == "eth_native_release"),
            None,
        ),
    }


def write_real_vaa_corpus_report(
    out_path: Path = DEFAULT_CORPUS_REPORT_PATH,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    report = build_real_vaa_corpus_report(fetch_operations(limit=limit))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return {
        "ok": True,
        "path": str(out_path),
        "decoded_token_bridge_vaas": report["decoded_token_bridge_vaas"],
        "route_counts": report["route_counts"],
    }


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
