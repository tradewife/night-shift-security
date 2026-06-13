"""Unit tests for KLend Solana transaction builder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

from klend_probes import probe_account_specs  # noqa: E402
from klend_tx import (  # noqa: E402
    b58decode,
    b58encode,
    build_invoke_transaction,
    build_signed_probe_transaction,
    encode_compact_u16,
    load_keypair,
    probe_instruction_accounts,
)


def test_b58_roundtrip():
    raw = bytes(range(32))
    assert b58decode(b58encode(raw)) == raw


def test_compact_u16_small_and_large():
    assert encode_compact_u16(0) == b"\x00"
    assert encode_compact_u16(4) == b"\x04"
    assert encode_compact_u16(127) == b"\x7f"
    assert encode_compact_u16(128) == b"\x80\x01"


def test_probe_account_specs_include_programs():
    specs = probe_account_specs("oracle_staleness_borrow")
    roles = {s.role for s in specs}
    assert "oracle" in roles
    assert "vault_program" in roles
    assert len(specs) >= 4


def test_probe_instruction_accounts_includes_payer_and_extras():
    from solders.keypair import Keypair

    payer = Keypair().pubkey()
    accounts = probe_instruction_accounts("flash_loan_collateral_loop", payer)
    assert accounts[0].pubkey == payer
    assert accounts[0].is_signer is True
    assert len(accounts) == 1 + len(probe_account_specs("flash_loan_collateral_loop"))


def test_build_invoke_message_has_header_and_keys():
    payer = bytes([1] * 32)
    program = bytes([2] * 32)
    blockhash = bytes([3] * 32)
    data = bytes([0x00, 0xCA, 0xFE, 0x01])

    message = build_invoke_transaction(
        payer_pubkey=payer,
        program_pubkey=program,
        recent_blockhash=blockhash,
        instruction_data=data,
    )

    assert message[:3] == bytes([1, 0, 1])
    assert len(message) > 99


def test_build_signed_probe_transaction_prefixes_signature_count(tmp_path: Path):
    from solders.keypair import Keypair

    keypair = Keypair()
    keypair_path = tmp_path / "key.json"
    keypair_path.write_text(json.dumps(list(bytes(keypair))))
    signing_key, _payer_pubkey = load_keypair(keypair_path)
    signed = build_signed_probe_transaction(
        keypair=signing_key,
        probe_id="oracle_staleness_borrow",
        recent_blockhash=bytes([7] * 32),
    )
    assert signed[0] == 1
    assert len(signed) > 64