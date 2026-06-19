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
from klend_account_discovery import derive_reserve_pdas  # noqa: E402
from klend_tx import (  # noqa: E402
    ASSOCIATED_TOKEN_PROGRAM,
    FARMS_PROGRAM,
    SPL_TOKEN_PROGRAM,
    SYSVAR_INSTRUCTIONS,
    b58decode,
    b58encode,
    borrow_obligation_v2_probe_accounts,
    borrow_refresh_prelude_instructions,
    build_invoke_transaction,
    build_signed_collateral_deposit_transaction,
    build_signed_probe_transaction,
    deposit_collateral_and_obligation_v2_accounts,
    derive_associated_token_account,
    derive_vanilla_obligation,
    encode_compact_u16,
    load_keypair,
    probe_instruction_account_summary,
    probe_instruction_accounts,
    refresh_obligation_data,
    refresh_reserve_data,
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
    assert len(accounts) == 12


def test_flash_loan_probe_transaction_includes_borrow_and_repay():
    from solders.keypair import Keypair
    from solders.hash import Hash

    keypair = Keypair()
    blockhash = bytes([9] * 32)
    signed = build_signed_probe_transaction(
        keypair=keypair,
        probe_id="flash_loan_collateral_loop",
        recent_blockhash=blockhash,
    )
    assert len(signed) > 200


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


def test_refresh_reserve_live_probe_accounts_match_prelude():
    from klend_tx import refresh_reserve_probe_accounts

    accounts = refresh_reserve_probe_accounts()
    assert len(accounts) == 6
    assert accounts[0].is_writable is True


def test_build_signed_probe_transaction_refresh_reserve_live_single_ix(tmp_path: Path):
    from solders.keypair import Keypair

    keypair = Keypair()
    keypair_path = tmp_path / "key.json"
    keypair_path.write_text(json.dumps(list(bytes(keypair))))
    signing_key, _payer_pubkey = load_keypair(keypair_path)
    signed = build_signed_probe_transaction(
        keypair=signing_key,
        probe_id="refresh_reserve_live",
        recent_blockhash=bytes([9] * 32),
    )
    assert signed[0] == 1
    assert len(signed) > 64


def test_borrow_refresh_prelude_uses_refresh_discriminators():
    from solders.keypair import Keypair

    payer = Keypair().pubkey()
    instructions = borrow_refresh_prelude_instructions(payer)
    assert len(instructions) == 3
    assert bytes(instructions[0].data) == refresh_reserve_data()
    assert bytes(instructions[1].data) == refresh_reserve_data()
    assert bytes(instructions[2].data) == refresh_obligation_data()
    assert len(instructions[0].accounts) == 6
    assert len(instructions[2].accounts) == 3


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


def test_derive_reserve_pdas_match_klend_interface_seeds():
    sol_reserve = "d4A2prbA2whesmvHaL88BH6Ewn5N4bTSU2Ze8P6Bc4Q"
    pdas = derive_reserve_pdas(sol_reserve)
    assert len(pdas["collateral_mint"]) > 30
    assert pdas["collateral_mint"] != pdas["collateral_supply_vault"]


def test_deposit_collateral_v2_account_count():
    from solders.keypair import Keypair

    payer = Keypair().pubkey()
    from klend_tx import deposit_collateral_and_obligation_accounts

    accounts = deposit_collateral_and_obligation_accounts(payer, collateral_symbol="SOL")
    assert len(accounts) == 14
    assert accounts[0].pubkey == payer
    assert str(accounts[6].pubkey) == "GafNuUXj9rxGLn4y79dPu6MHSuPWeJR6UtTWuexpGh3U"
    assert str(accounts[7].pubkey) == "2UywZrUdyqs5vDchy7fKQJKau2RVyuzBev2XKGPDSiX1"
    assert str(accounts[8].pubkey) == "8NXMyRD91p3nof61BTkJvrfpGTASHygz1cUvc3HvwyGS"


def test_build_signed_collateral_deposit_transaction(tmp_path: Path):
    from solders.keypair import Keypair

    keypair = Keypair()
    keypair_path = tmp_path / "key.json"
    keypair_path.write_text(json.dumps(list(bytes(keypair))))
    signing_key, _ = load_keypair(keypair_path)
    signed = build_signed_collateral_deposit_transaction(
        keypair=signing_key,
        recent_blockhash=bytes([5] * 32),
        liquidity_amount=50_000_000,
    )
    assert len(signed) > 200


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
