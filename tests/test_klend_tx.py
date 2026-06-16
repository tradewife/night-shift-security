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
    ASSOCIATED_TOKEN_PROGRAM,
    FARMS_PROGRAM,
    SPL_TOKEN_PROGRAM,
    SYSVAR_INSTRUCTIONS,
    b58decode,
    b58encode,
    borrow_obligation_v2_probe_accounts,
    build_invoke_transaction,
    build_signed_probe_transaction,
    derive_associated_token_account,
    derive_vanilla_obligation,
    encode_compact_u16,
    load_keypair,
    probe_instruction_account_summary,
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


def test_borrow_obligation_v2_probe_accounts_are_source_ordered():
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey

    payer = Keypair().pubkey()
    accounts = borrow_obligation_v2_probe_accounts(payer)
    assert len(accounts) == 15
    assert accounts[0].pubkey == payer
    assert accounts[0].is_signer is True
    assert accounts[1].pubkey != payer
    assert accounts[1].is_writable is True
    assert accounts[9].is_writable is False
    assert accounts[10].pubkey == Pubkey.from_string(SPL_TOKEN_PROGRAM)
    assert accounts[11].pubkey == Pubkey.from_string(SYSVAR_INSTRUCTIONS)
    assert accounts[12].is_writable is False
    assert accounts[13].is_writable is False
    assert accounts[14].pubkey == Pubkey.from_string(FARMS_PROGRAM)


def test_probe_instruction_accounts_uses_source_order_for_borrow_probe():
    from solders.keypair import Keypair

    payer = Keypair().pubkey()
    accounts = probe_instruction_accounts("oracle_staleness_borrow", payer)
    assert len(accounts) == 15
    assert accounts[0].pubkey == payer


def test_probe_instruction_account_summary_names_borrow_roles():
    from solders.keypair import Keypair

    payer = Keypair().pubkey()
    summary = probe_instruction_account_summary("oracle_staleness_borrow", payer)
    assert summary.startswith("owner:")
    assert "obligation:" in summary
    assert "instruction_sysvar:Sysvar1n" in summary
    assert "farms_program:FarmsPZp" in summary


def test_derive_vanilla_obligation_and_ata_are_deterministic():
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey

    payer = Keypair().pubkey()
    market = "7u3HeHxYDLhnCoErrtycNokbQYbWGzLs6JSDqGAv5PfF"
    mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    obligation = derive_vanilla_obligation(payer, market)
    ata = derive_associated_token_account(payer, mint)
    assert obligation == derive_vanilla_obligation(payer, market)
    assert ata == derive_associated_token_account(payer, mint)
    assert obligation != payer
    assert ata != payer
    assert Pubkey.from_string(ASSOCIATED_TOKEN_PROGRAM) is not None


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
