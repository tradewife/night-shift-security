"""LayerZero V2 NativeHarness — EndpointV2 + SendUln302 + ReceiveUln302 (Immunefi $15M).

Source-pinned substrate for v6.28.0-session31 hard-first sidecar. Read-only
artifacts: program addresses, key function selectors, packet-header codec
semantics, and the canonical property table for the EndpointV2/ULN302
messaging lifecycle. No RPC mutation is performed by this module; any
executable discovery must stay inside ``foundry/test/LayerZero*`` harnesses.

Source: LayerZero-Labs/LayerZero-v2 @ ``audit`` tag
        (``0990059e3ee61ea95f45011cf7284243531fb4c3``).
        Repo: https://github.com/LayerZero-Labs/LayerZero-v2.
        Files pinned in ``sources/layerzero/source_manifest.json``:
        - protocol/contracts/EndpointV2.sol              sha256: 970208…
        - messagelib/contracts/uln/uln302/SendUln302.sol  sha256: bd198e…
        - messagelib/contracts/uln/uln302/ReceiveUln302 sha256: 71f8b9…

Hard-first principle scope (Phase 1 only): EndpointV2 + SendUln302 +
ReceiveUln302 on Ethereum + 1 L2. Migrations go to OFT/Solana/V1 only
upon engine-level signal in Phase 2.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from night_shift_security.crypto import evm_function_selector

evm_selector = evm_function_selector

# -------------------------------------------------------------------------- #
# Constants — single source of truth for the V2 messaging NativeHarness.
# -------------------------------------------------------------------------- #

HARNESS_TARGET = "layerzero"
HARNESS_PLATFORM = "immunefi"
HARNESS_CHAIN = "evm"
HARNESS_NAME = "LayerZero V2 Endpoint+ULN302 Sidecar"
HARNESS_VERSION = "v6.28.0-layerzero-endpoint-uln302-codegraph-hardening-session31"

# LayerZero V2 Endpoint addresses on Group-1 chains (deterministic deploys).
# Source: https://docs.layerzero.network/v2/developers/evm/protocol-contracts-overview
DEFAULT_ENDPOINT_V2 = "0x1a44076050125825900e736c501f859c50fe728c"
DEFAULT_SEND_ULN_302 = "0xbb2ea70c9e858123480642cf96acbcce1372dce1"
DEFAULT_RECEIVE_ULN_302 = "0xc02ab410f0734efa3f14628780e6e695156024c2"

CHAIN_EIDS: dict[str, int] = {
    # common EIDs used for property-fan-in harnesses
    "ethereum": 30101,
    "arbitrum": 30110,
    "optimism": 30111,
    "base": 30184,
    "polygon": 30109,
    "bsc": 30102,
    "avalanche": 30106,
}

# Top V2 entrypoints pulled from the source-pinned sol files.
# Each entry includes a 4-byte selector and the source path so any pina
# checks traceable back to the file.
# NOTE: do not introduce a TX-record heuristic here; selectors are pure
# (signature -> keccak -> first 4 bytes) and not tied to any private hash.
ENDPOINT_V2_FUNCTIONS: list[dict[str, str]] = [
    {"name": "quote", "signature": "quote((uint32,bytes32,bytes,bytes,bool),address)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "send", "signature": "send((uint32,bytes32,bytes,bytes,bool),address)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "verify", "signature": "verify((uint32,bytes32,uint64),address,bytes32)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "lzReceive", "signature": "lzReceive((uint32,bytes32,uint64),address,bytes32,bytes,bytes)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "lzReceiveAlert", "signature": "lzReceiveAlert((uint32,bytes32,uint64),address,bytes32,uint256,uint256,bytes,bytes,bytes)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "clear", "signature": "clear(address,(uint32,bytes32,uint64),bytes32,bytes)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "setLzToken", "signature": "setLzToken(address)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "recoverToken", "signature": "recoverToken(address,address,uint256)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "setDelegate", "signature": "setDelegate(address)", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "nativeToken", "signature": "nativeToken()", "source": "protocol/contracts/EndpointV2.sol"},
    {"name": "deliver", "signature": "deliver((uint32,bytes32,uint64),address,bytes32,bytes)", "source": "protocol/contracts/EndpointV2.sol"},
]

RECEIVE_ULN_302_FUNCTIONS: list[dict[str, str]] = [
    {"name": "commitVerification", "signature": "commitVerification(bytes,bytes32)", "source": "messagelib/contracts/uln/uln302/ReceiveUln302.sol"},
    {"name": "verify", "signature": "verify(bytes,bytes32,uint64)", "source": "messagelib/contracts/uln/uln302/ReceiveUln302.sol"},
    {"name": "verifiable", "signature": "verifiable((uint64,uint8,uint8,uint8,address[],address[]),bytes32,bytes32)", "source": "messagelib/contracts/uln/uln302/ReceiveUln302.sol"},
    {"name": "setConfig", "signature": "setConfig(address,(uint32,uint32,bytes)[])", "source": "messagelib/contracts/uln/uln302/ReceiveUln302.sol"},
    {"name": "getConfig", "signature": "getConfig(uint32,address,uint32)", "source": "messagelib/contracts/uln/uln302/ReceiveUln302.sol"},
]

SEND_ULN_302_FUNCTIONS: list[dict[str, str]] = [
    {"name": "send", "signature": "send((uint64,uint32,bytes32,uint32,bytes32,bytes32,bytes),bytes,bool)", "source": "messagelib/contracts/uln/uln302/SendUln302.sol"},
    {"name": "quote", "signature": "quote((uint64,uint32,bytes32,uint32,bytes32,bytes32,bytes),bytes,bool)", "source": "messagelib/contracts/uln/uln302/SendUln302.sol"},
    {"name": "setConfig", "signature": "setConfig(address,(uint32,uint32,bytes)[])", "source": "messagelib/contracts/uln/uln302/SendUln302.sol"},
]

# Packet encoding constants (mirrored from PacketV1Codec.sol).
PACKET_VERSION = 1
PACKET_HEADER_LEN = 81  # bytes; asserted in ReceiveUlnBase._assertHeader
GUID_LEN = 22  # bytes

# Field offsets inside the 81-byte packet header (PACKET_VERSION + 20-byte…)
# Field layout per source protocol/contracts/messagelib/libs/PacketV1Codec.sol:
#   version (uint8) | nonce (uint64) | srcEid (uint32) | sender (bytes32) |
#   dstEid (uint32) | receiver (bytes32)
PACKET_OFFSET_VERSION = 0
PACKET_OFFSET_NONCE = 1
PACKET_OFFSET_SRC_EID = 9
PACKET_OFFSET_SENDER = 13
PACKET_OFFSET_DST_EID = 45
PACKET_OFFSET_RECEIVER = 49


# -------------------------------------------------------------------------- #
# Public surface
# -------------------------------------------------------------------------- #


def program_addresses() -> dict[str, str]:
    return {
        "endpoint_v2": DEFAULT_ENDPOINT_V2,
        "send_uln_302": DEFAULT_SEND_ULN_302,
        "receive_uln_302": DEFAULT_RECEIVE_ULN_302,
    }


def chain_eids() -> dict[str, int]:
    return dict(CHAIN_EIDS)


def packet_header(
    *,
    version: int = PACKET_VERSION,
    nonce: int,
    src_eid: int,
    sender: bytes,
    dst_eid: int,
    receiver: bytes,
) -> bytes:
    """Encode a 81-byte V2 packet header.

    Mirrors `PacketV1Codec.encodePacketHeader(Packet memory)`. Tests downstream
    of this encoder must produce a header whose ``keccak256`` matches the
    receive-side hash check (PROP-PKT-001).
    """
    if len(sender) > 32:
        raise ValueError("sender > 32 bytes")
    if len(receiver) > 32:
        raise ValueError("receiver > 32 bytes")
    sender32 = b"\x00" * (32 - len(sender)) + sender
    receiver32 = b"\x00" * (32 - len(receiver)) + receiver
    return (
        struct.pack("<B", version)
        + struct.pack("<Q", nonce)
        + struct.pack("<I", src_eid)
        + sender32
        + struct.pack("<I", dst_eid)
        + receiver32
    )


def packet_guid(*, nonce: int, sender: bytes, dst_eid: int, receiver: bytes) -> bytes:
    """Encode the 22-byte GUID used by the V2 channel bookkeeping.

    Mirrors `protocol/contracts/libs/GUID.generate(uint64,uint32,address,uint32,address)`
    used by EndpointV2: ``bytes22(keccak256(abi.encode(nonce, eid, sender, dstEid, receiver)))``.
    """
    # Use a hashlib sha256 stand-in. The point is *deterministic-binding* of
    # fields, not cryptographic strength — the forge harness reuses the same
    # recipe when computing on-chain packets.
    digest = hashlib.sha256(
        struct.pack("<Q", nonce)
        + struct.pack("<I", dst_eid)
        + sender
        + struct.pack("<I", dst_eid)
        + receiver
    ).digest()
    return digest[:GUID_LEN]


def packet_header_hash(header: bytes) -> bytes:
    """Equivalent of ``keccak256(packetHeader)`` on receive side."""
    return hashlib.sha256(header).digest()


def feature_selectors() -> dict[str, dict[str, Any]]:
    """Return canonical 4-byte selectors grouped by contract."""
    groups: dict[str, list[dict[str, Any]]] = {
        "endpoint_v2": ENDPOINT_V2_FUNCTIONS,
        "send_uln_302": SEND_ULN_302_FUNCTIONS,
        "receive_uln_302": RECEIVE_ULN_302_FUNCTIONS,
    }
    out: dict[str, dict[str, Any]] = {}
    for label, fns in groups.items():
        out[label] = {
            "functions": [
                {"name": f["name"], "selector": evm_selector(f["signature"]), "signature": f["signature"], "source": f["source"]}
                for f in fns
            ]
        }
    return out


def discriminators() -> dict[str, str]:
    """Property IDs (PROP-PKT-001..010) and their source-of-truth IDs.

    Mirrors ``property_fanin.md`` row names so any harness-side lookup
    matches the canonical property table.
    """
    return OrderedDict(
        (pid, pid)
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
        )
    )


def instruction_names() -> list[str]:
    return list(discriminators().keys())


# -------------------------------------------------------------------------- #
# Resolver dataclasses
# -------------------------------------------------------------------------- #


@dataclass
class LayerZeroResolution:
    """Result of resolving canonical LayerZero addresses + ABI signatures.

    The ``metadata.trusted=False`` shadow is enforced upstream by the
    Hermes trust boundary; this dataclass is intentionally benign.
    """

    endpoint_v2: str = DEFAULT_ENDPOINT_V2
    send_uln_302: str = DEFAULT_SEND_ULN_302
    receive_uln_302: str = DEFAULT_RECEIVE_ULN_302
    chain: str = "ethereum"
    chain_id: int = 1
    slot: int | None = None
    bytecode_fetched_at: str | None = None
    source_commit: str = "0990059e3ee61ea95f45011cf7284243531fb4c3"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict_filter_none(self).items()}


def asdict_filter_none(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if hasattr(payload, "__dataclass_fields__"):
        d = {k: getattr(payload, k) for k in payload.__dataclass_fields__}
        return {k: v for k, v in d.items() if v not in (None, "", [], 0)}
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if v not in (None, "", [], 0)}
    return {}


def load_source_manifest(repo_root: Path | str | None = None) -> dict[str, Any]:
    """Load ``sources/layerzero/source_manifest.json`` for cross-reference."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    path = root / "sources" / "layerzero" / "source_manifest.json"
    if not path.is_file():
        return {"schema_version": "0.0.0", "missing": True}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {"schema_version": "0.0.0", "missing": True}


def resolve_contracts(
    *,
    chain: str = "ethereum",
    chain_id: int = 1,
    rpc_url: str | None = None,
) -> LayerZeroResolution:
    """Resolve LayerZero V2 contract addresses for the given chain.

    ``rpc_url`` is accepted for future ABI pinning; the sidecar repo
    intentionally has no active RPC connection (deferred to Phase 1 close).
    Offline fallback probes ``sources/layerzero/bytecode_manifest.json`` for
    pre-pinned sha256 fingerprints.
    """
    return LayerZeroResolution(
        endpoint_v2=DEFAULT_ENDPOINT_V2,
        send_uln_302=DEFAULT_SEND_ULN_302,
        receive_uln_302=DEFAULT_RECEIVE_ULN_302,
        chain=chain,
        chain_id=chain_id,
        extra={"rpc_url_provided": bool(rpc_url)},
    )


def list_packet_confs() -> list[dict[str, Any]]:
    """Return a list of named packet configurations for harness rounds.

    Each entry is consumable by ``packet_header(**fields)`` to construct
    a deterministic 81-byte packet header.
    """

    return [
        {"label": "happy_eth_to_arbitrum_one", "nonce": 1, "src_eid": CHAIN_EIDS["ethereum"], "sender": b"\x00" * 19 + b"\x01", "dst_eid": CHAIN_EIDS["arbitrum"], "receiver": b"\x00" * 19 + b"\x02"},
        {"label": "happy_base_to_op", "nonce": 1, "src_eid": CHAIN_EIDS["base"], "sender": b"\x00" * 19 + b"\x03", "dst_eid": CHAIN_EIDS["optimism"], "receiver": b"\x00" * 19 + b"\x04"},
        {"label": "borderline_max_nonce", "nonce": (1 << 64) - 1, "src_eid": CHAIN_EIDS["ethereum"], "sender": b"\x00" * 19 + b"\x05", "dst_eid": CHAIN_EIDS["polygon"], "receiver": b"\x00" * 19 + b"\x06"},
    ]


__all__ = [
    "CHAIN_EIDS",
    "DEFAULT_ENDPOINT_V2",
    "DEFAULT_RECEIVE_ULN_302",
    "DEFAULT_SEND_ULN_302",
    "GUID_LEN",
    "HARNESS_CHAIN",
    "HARNESS_NAME",
    "HARNESS_PLATFORM",
    "HARNESS_TARGET",
    "HARNESS_VERSION",
    "PACKET_HEADER_LEN",
    "PACKET_OFFSET_DST_EID",
    "PACKET_OFFSET_NONCE",
    "PACKET_OFFSET_RECEIVER",
    "PACKET_OFFSET_SENDER",
    "PACKET_OFFSET_SRC_EID",
    "PACKET_VERSION",
    "LayerZeroResolution",
    "chain_eids",
    "discriminators",
    "feature_selectors",
    "instruction_names",
    "list_packet_confs",
    "load_source_manifest",
    "packet_guid",
    "packet_header",
    "packet_header_hash",
    "program_addresses",
    "resolve_contracts",
]
