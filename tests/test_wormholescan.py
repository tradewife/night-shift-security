"""Tests for Wormholescan signed VAA helpers."""

import base64
import json

import night_shift_security.bridge.wormholescan as wormholescan
from night_shift_security.bridge.wormholescan import (
    build_real_vaa_corpus_report,
    classify_real_vaa_operation,
    decode_token_bridge_vaa,
    fetch_operation_pages,
    fetch_operations,
    select_asset_meta_vaa,
    select_eth_native_release_vaa,
    select_eth_wrapped_mint_vaa,
    write_latest_asset_meta_vaa,
    write_latest_eth_wrapped_mint_vaa,
)


def _raw_vaa_b64(payload: bytes) -> str:
    body = (
        (123).to_bytes(4, "big")
        + (7).to_bytes(4, "big")
        + (1).to_bytes(2, "big")
        + bytes.fromhex("ec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5")
        + (1402175).to_bytes(8, "big")
        + bytes([15])
    )
    raw = bytes([1]) + (6).to_bytes(4, "big") + bytes([0]) + body + payload
    return base64.b64encode(raw).decode()


def _sample_raw_vaa_b64() -> str:
    payload = (
        bytes([1])
        + (13844500000000).to_bytes(32, "big")
        + bytes.fromhex("00000000000000000000000055296f69f40ea6d20e478533c15a6b08b654e758")
        + (2).to_bytes(2, "big")
        + bytes.fromhex("0000000000000000000000000000000000000000000000000000000000a77acc")
        + (2).to_bytes(2, "big")
        + (0).to_bytes(32, "big")
    )
    return _raw_vaa_b64(payload)


def _sample_wrapped_mint_vaa_b64() -> str:
    payload = (
        bytes([1])
        + (12345).to_bytes(32, "big")
        + bytes.fromhex("00000000000000000000000000000000000000000000000000000000000000aa")
        + (4).to_bytes(2, "big")
        + bytes.fromhex("0000000000000000000000000000000000000000000000000000000000a77acc")
        + (2).to_bytes(2, "big")
        + (0).to_bytes(32, "big")
    )
    return _raw_vaa_b64(payload)


def _sample_asset_meta_vaa_b64() -> str:
    payload = (
        bytes([2])
        + bytes.fromhex("00000000000000000000000000000000000000000000000000000000000000aa")
        + (4).to_bytes(2, "big")
        + bytes([18])
        + b"TST".ljust(32, b"\x00")
        + b"Test Token".ljust(32, b"\x00")
    )
    return _raw_vaa_b64(payload)


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


def test_select_eth_wrapped_mint_vaa_filters_operations():
    selected = select_eth_wrapped_mint_vaa(
        [{"id": "wrapped", "vaa": {"raw": _sample_wrapped_mint_vaa_b64()}}]
    )
    assert selected is not None
    assert selected["id"] == "wrapped"
    assert selected["decoded"]["token_chain"] == 4
    assert selected["decoded"]["to_chain"] == 2


def test_select_asset_meta_vaa_filters_operations():
    selected = select_asset_meta_vaa([{"id": "asset-meta", "vaa": {"raw": _sample_asset_meta_vaa_b64()}}])
    assert selected is not None
    assert selected["id"] == "asset-meta"
    assert selected["decoded"]["payload_id"] == 2
    assert selected["decoded"]["symbol"] == "TST"


def test_classify_real_vaa_operation_marks_eth_native_release():
    entry = classify_real_vaa_operation({"id": "match", "vaa": {"raw": _sample_raw_vaa_b64()}})
    assert entry is not None
    assert entry["route"] == "eth_native_release"
    assert entry["amount"] == 13844500000000
    assert entry["amount_mismatch"] is False


def test_build_real_vaa_corpus_report_summarizes_routes():
    report = build_real_vaa_corpus_report(
        [
            {"id": "ignored", "vaa": {"raw": "not-base64"}},
            {"id": "match", "vaa": {"raw": _sample_raw_vaa_b64()}},
        ]
    )
    assert report["operations_seen"] == 2
    assert report["decoded_token_bridge_vaas"] == 1
    assert report["route_counts"] == {"eth_native_release": 1}
    assert report["selected_eth_native_release"]["id"] == "match"


def test_build_real_vaa_corpus_report_includes_asset_meta_and_wrapped_mint():
    report = build_real_vaa_corpus_report(
        [
            {"id": "wrapped", "vaa": {"raw": _sample_wrapped_mint_vaa_b64()}},
            {"id": "asset-meta", "vaa": {"raw": _sample_asset_meta_vaa_b64()}},
        ]
    )
    assert report["decoded_token_bridge_vaas"] == 2
    assert report["route_counts"] == {"eth_wrapped_mint": 1, "asset_meta": 1}


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


def test_fetch_operations_uses_documented_page_params(monkeypatch):
    urls: list[str] = []

    def fake_urlopen(url: str, timeout: int):
        urls.append(url)
        assert timeout == 20
        return _FakeResponse({"operations": [{"id": "op"}]})

    monkeypatch.setattr(wormholescan.urllib.request, "urlopen", fake_urlopen)

    operations = fetch_operations(base_url="https://scan.test/api/v1", page=3, page_size=25, address="abc")

    assert operations == [{"id": "op"}]
    assert urls == ["https://scan.test/api/v1/operations?page=3&pageSize=25&address=abc"]


def test_fetch_operation_pages_deduplicates_and_stops_on_empty(monkeypatch):
    pages = [
        [{"id": "a", "vaa": {"raw": _sample_raw_vaa_b64()}}, {"id": "b"}],
        [{"id": "b"}, {"id": "c", "vaa": {"raw": _sample_wrapped_mint_vaa_b64()}}],
        [],
    ]
    seen_pages: list[int | None] = []

    def fake_fetch_operations(**kwargs):
        seen_pages.append(kwargs.get("page"))
        return pages[int(kwargs["page"])]

    monkeypatch.setattr(wormholescan, "fetch_operations", fake_fetch_operations)

    operations = fetch_operation_pages(pages=5, page_size=2)
    report = build_real_vaa_corpus_report(operations)

    assert [op["id"] for op in operations] == ["a", "b", "c"]
    assert seen_pages == [0, 1, 2]
    assert report["route_counts"] == {"eth_native_release": 1, "eth_wrapped_mint": 1}


def test_write_latest_route_vaas_use_paged_fetch(monkeypatch, tmp_path):
    def fake_fetch_operation_pages(**_kwargs):
        return [
            {"id": "wrapped", "vaa": {"raw": _sample_wrapped_mint_vaa_b64()}},
            {"id": "asset-meta", "vaa": {"raw": _sample_asset_meta_vaa_b64()}},
        ]

    monkeypatch.setattr(wormholescan, "fetch_operation_pages", fake_fetch_operation_pages)

    wrapped_path = tmp_path / "wrapped.json"
    asset_path = tmp_path / "asset.json"
    wrapped_result = write_latest_eth_wrapped_mint_vaa(wrapped_path, pages=2)
    asset_result = write_latest_asset_meta_vaa(asset_path, pages=2)

    assert wrapped_result["id"] == "wrapped"
    assert asset_result["id"] == "asset-meta"
    assert json.loads(wrapped_path.read_text())["decoded"]["to_chain"] == 2
    assert json.loads(asset_path.read_text())["decoded"]["symbol"] == "TST"
