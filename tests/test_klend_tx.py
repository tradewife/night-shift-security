"""Unit tests for KLend Solana transaction builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

from klend_tx import (  # noqa: E402
    b58decode,
    b58encode,
    build_invoke_transaction,
    build_signed_invoke_transaction,
    encode_compact_u16,
    load_keypair,
    probe_instruction_data,
)


def test_b58_roundtrip():
    raw = bytes(range(32))
    assert b58decode(b58encode(raw)) == raw


def test_compact_u16_small_and_large():
    assert encode_compact_u16(0) == b"\x00"
    assert encode_compact_u16(4) == b"\x04"
    assert encode_compact_u16(127) == b"\x7f"
    assert encode_compact_u16(128) == b"\x80\x01"


def test_probe_instruction_data_known_ids():
    assert probe_instruction_data("baseline_deploy") == b""
    assert probe_instruction_data("oracle_staleness_borrow") == bytes([0x00, 0xCA, 0xFE, 0x01])
    assert probe_instruction_data("unknown") == b"\xff"


def test_build_invoke_message_has_header_and_keys():
    payer = bytes([1] * 32)
    program = bytes([2] * 32)
    blockhash = bytes([3] * 32)
    data = probe_instruction_data("oracle_staleness_borrow")

    message = build_invoke_transaction(
        payer_pubkey=payer,
        program_pubkey=program,
        recent_blockhash=blockhash,
        instruction_data=data,
    )

    assert message[:3] == bytes([1, 0, 1])
    assert len(message) > 99


def test_build_signed_invoke_transaction_prefixes_signature_count(tmp_path: Path):
    from solders.keypair import Keypair

    keypair = Keypair()
    keypair_path = tmp_path / "key.json"
    keypair_path.write_text(json.dumps(list(bytes(keypair))))
    signing_key, payer_pubkey = load_keypair(keypair_path)
    program_pubkey = bytes([9] * 32)
    signed = build_signed_invoke_transaction(
        keypair=signing_key,
        program_pubkey=program_pubkey,
        recent_blockhash=bytes([7] * 32),
        instruction_data=b"\x01\x02",
    )
    assert signed[0] == 1
    assert len(signed) > 64