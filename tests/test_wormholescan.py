"""Tests for Wormholescan signed VAA helpers."""

import base64

from night_shift_security.bridge.wormholescan import (
    decode_token_bridge_vaa,
    select_eth_native_release_vaa,
)


def _sample_raw_vaa_b64() -> str:
    body = (
        (123).to_bytes(4, "big")
        + (7).to_bytes(4, "big")
        + (1).to_bytes(2, "big")
        + bytes.fromhex("ec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5")
        + (1402175).to_bytes(8, "big")
        + bytes([15])
    )
    payload = (
        bytes([1])
        + (13844500000000).to_bytes(32, "big")
        + bytes.fromhex("00000000000000000000000055296f69f40ea6d20e478533c15a6b08b654e758")
        + (2).to_bytes(2, "big")
        + bytes.fromhex("0000000000000000000000000000000000000000000000000000000000a77acc")
        + (2).to_bytes(2, "big")
        + (0).to_bytes(32, "big")
    )
    raw = bytes([1]) + (6).to_bytes(4, "big") + bytes([0]) + body + payload
    return base64.b64encode(raw).decode()


def test_decode_token_bridge_vaa_extracts_native_eth_release():
    decoded = decode_token_bridge_vaa(_sample_raw_vaa_b64())
    assert decoded.emitter_chain == 1
    assert decoded.payload_id == 1
    assert decoded.amount == 13844500000000
    assert decoded.token_chain == 2
    assert decoded.to_chain == 2
    assert decoded.raw_hex.startswith("0x01")


def test_select_eth_native_release_vaa_filters_operations():
    selected = select_eth_native_release_vaa(
        [
            {"id": "ignored", "vaa": {"raw": "not-base64"}},
            {"id": "match", "vaa": {"raw": _sample_raw_vaa_b64()}},
        ]
    )
    assert selected is not None
    assert selected["id"] == "match"
    assert selected["decoded"]["token_chain"] == 2
