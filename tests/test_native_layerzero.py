"""Tests for the LayerZero V2 (Endpoint+ULN302) native harness (v6.28 sidecar)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from night_shift_security.native import layerzero
from night_shift_security.crypto import evm_function_selector, keccak256


def test_harness_metadata_constants() -> None:
    assert layerzero.HARNESS_TARGET == "layerzero"
    assert layerzero.HARNESS_PLATFORM == "immunefi"
    assert layerzero.HARNESS_CHAIN == "evm"
    assert layerzero.HARNESS_NAME.startswith("LayerZero")
    assert layerzero.HARNESS_VERSION.startswith("v6.28")


def test_program_addresses_match_bounty_scope() -> None:
    """EndpointV2 + ULN302 Send/Receive addresses pinned by Immunefi bounty."""
    addrs = layerzero.program_addresses()
    assert addrs["endpoint_v2"] == "0x1a44076050125825900e736c501f859c50fe728c"
    assert addrs["send_uln_302"] == "0xbb2ea70c9e858123480642cf96acbcce1372dce1"
    assert addrs["receive_uln_302"] == "0xc02ab410f0734efa3f14628780e6e695156024c2"


def test_chain_eids_table_complete() -> None:
    eids = layerzero.chain_eids()
    # at minimum, the canonical Group-1 chains used in v6.27 Phase 1
    for k in ("ethereum", "arbitrum", "optimism", "base", "polygon"):
        assert k in eids
        assert eids[k] > 0


def test_feature_selectors_match_first_four_bytes_keccak() -> None:
    """Cross-verify with raw keccak256 to detect typos in signatures."""
    feats = layerzero.feature_selectors()
    # EndpointV2.send selector sanity check — independent keccak computation
    raw_sig = "send((uint32,bytes32,bytes,bytes,bool),address)"
    expected = "0x" + keccak256(raw_sig.encode()).hex()[:8]
    endpoint_send = next(f for f in feats["endpoint_v2"]["functions"] if f["name"] == "send")
    assert endpoint_send["selector"] == expected

    # ReceiveUln302.commitVerification signature is the dedicated attack surface
    raw_sig = "commitVerification(bytes,bytes32)"
    expected = "0x" + keccak256(raw_sig.encode()).hex()[:8]
    recv_commit = next(f for f in feats["receive_uln_302"]["functions"] if f["name"] == "commitVerification")
    assert recv_commit["selector"] == expected


def test_packet_header_is_81_bytes() -> None:
    """PROP-PKT-001 binding: header length must be 81 bytes per source assertion."""
    hdr = layerzero.packet_header(
        nonce=1,
        src_eid=layerzero.CHAIN_EIDS["ethereum"],
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    assert len(hdr) == 81


def test_packet_header_version_byte_first() -> None:
    """Version byte is the first byte by source convention."""
    hdr = layerzero.packet_header(
        nonce=1,
        src_eid=layerzero.CHAIN_EIDS["ethereum"],
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    assert hdr[0] == layerzero.PACKET_VERSION


def test_packet_header_hash_deterministic() -> None:
    """PROP-PKT-001: same fields produce same hash; different nonce changes hash."""
    a = layerzero.packet_header(
        nonce=1,
        src_eid=layerzero.CHAIN_EIDS["ethereum"],
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    b = layerzero.packet_header(
        nonce=2,  # mutated nonce
        src_eid=layerzero.CHAIN_EIDS["ethereum"],
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    assert a != b
    # same tuple converges on same hash
    a2 = layerzero.packet_header(
        nonce=1,
        src_eid=layerzero.CHAIN_EIDS["ethereum"],
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    assert layerzero.packet_header_hash(a) == layerzero.packet_header_hash(a2)


def test_packet_guid_is_22_bytes() -> None:
    """GUID length per source `protocol/contracts/libs/GUID.sol`."""
    g = layerzero.packet_guid(
        nonce=1,
        sender=b"\x01" * 20,
        dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
        receiver=b"\x02" * 20,
    )
    assert len(g) == layerzero.GUID_LEN


def test_packet_header_rejects_oversized_sender() -> None:
    """Sender must fit in a 32-byte left-padded slot."""
    with pytest.raises(ValueError):
        layerzero.packet_header(
            nonce=1,
            src_eid=layerzero.CHAIN_EIDS["ethereum"],
            sender=b"\x01" * 33,
            dst_eid=layerzero.CHAIN_EIDS["arbitrum"],
            receiver=b"\x02" * 20,
        )


def test_resolve_contracts_offline_fallback() -> None:
    """No RPC: resolver must still produce canonical addresses."""
    res = layerzero.resolve_contracts(chain="ethereum", chain_id=1)
    assert res.endpoint_v2 == layerzero.DEFAULT_ENDPOINT_V2
    assert res.send_uln_302 == layerzero.DEFAULT_SEND_ULN_302
    assert res.receive_uln_302 == layerzero.DEFAULT_RECEIVE_ULN_302
    assert res.chain_id == 1


def test_resolve_contracts_with_rpc_url_stores_metadata() -> None:
    res = layerzero.resolve_contracts(chain="arbitrum", chain_id=42161, rpc_url="https://example.com")
    assert res.extra.get("rpc_url_provided") is True
    assert res.chain_id == 42161


def test_load_source_manifest_if_present() -> None:
    """If the sidecar source manifest exists, parsing must succeed (no schema errors)."""
    manifest = layerzero.load_source_manifest()
    if not manifest.get("missing"):
        # If the manifest was written, must be a structured dict
        assert isinstance(manifest, dict)
        # Schema check: must contain the ``contracts_in_scope`` block
        if "contracts_in_scope" in manifest:
            assert isinstance(manifest["contracts_in_scope"], list)
            assert len(manifest["contracts_in_scope"]) >= 3


def test_discriminators_returns_property_ids() -> None:
    """Discriminators map must align with the property_fanin.md row names."""
    disc = layerzero.discriminators()
    for pid in (
        "PROP-PKT-001",
        "PROP-PKT-002",
        "PROP-PKT-003",
        "PROP-PKT-004",
        "PROP-PKT-005",
        "PROP-PKT-006",
        "PROP-PKT-007",
        "PROP-PKT-008",
        "PROP-PKT-009",
        "PROP-PKT-010",
    ):
        assert pid in disc
        assert disc[pid] == pid


def test_packet_confs_named_for_harness() -> None:
    confs = layerzero.list_packet_confs()
    labels = [c["label"] for c in confs]
    assert "happy_eth_to_arbitrum_one" in labels
    # All packets encode to 81-byte headers
    for conf in confs:
        hdr = layerzero.packet_header(
            nonce=conf["nonce"],
            src_eid=conf["src_eid"],
            sender=conf["sender"],
            dst_eid=conf["dst_eid"],
            receiver=conf["receiver"],
        )
        assert len(hdr) == 81


def test_no_fixture_markers_in_module() -> None:
    """Cross-check against kamino/marginfi sentinel — no fixture markers."""
    source = Path(layerzero.__file__).read_text()
    assert "HARNESS_MODE:fixture" not in source


def test_address_format_for_evm() -> None:
    """Endpoint + ULN302 addresses are 20-byte lowercase hex strings."""
    for addr in layerzero.program_addresses().values():
        assert addr.startswith("0x") and len(addr) == 42
        int(addr, 16)  # parses cleanly


def test_harness_version_matches_session_round() -> None:
    """Sentinel: harness version must match the current session-31 round."""
    assert "session31" in layerzero.HARNESS_VERSION
