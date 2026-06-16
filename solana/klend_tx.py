"""Solana legacy transaction builder for KLend CPI probe invokes."""

from __future__ import annotations

import json
from pathlib import Path

from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from klend_probes import KLEND_PROGRAM, probe_account_specs, probe_instruction_data
from klend_account_discovery import load_klend_accounts

FARMS_PROGRAM = "FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr"
SYSVAR_INSTRUCTIONS = "Sysvar1nstructions1111111111111111111111111"
SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
ASSOCIATED_TOKEN_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
SYSVAR_RENT = "SysvarRent111111111111111111111111111111111"

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    enc = ""
    while num > 0:
        num, rem = divmod(num, 58)
        enc = _B58_ALPHABET[rem] + enc
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
    return _B58_ALPHABET[0] * pad + (enc or _B58_ALPHABET[0])


def b58decode(value: str) -> bytes:
    num = 0
    for char in value:
        num = num * 58 + _B58_ALPHABET.index(char)
    combined = num.to_bytes((num.bit_length() + 7) // 8, "big") if num else b""
    pad = 0
    for char in value:
        if char == _B58_ALPHABET[0]:
            pad += 1
        else:
            break
    return b"\x00" * pad + combined


def encode_compact_u16(value: int) -> bytes:
    if value < 0x80:
        return bytes([value])
    if value < 0x4000:
        return bytes([(value & 0x7F) | 0x80, value >> 7])
    return bytes([(value & 0x7F) | 0x80, ((value >> 7) & 0x7F) | 0x80, value >> 14])


def encode_compact_bytes(data: bytes) -> bytes:
    return encode_compact_u16(len(data)) + data


def load_keypair(path: Path) -> tuple[Keypair, bytes]:
    raw = json.loads(path.read_text())
    if not isinstance(raw, list) or len(raw) != 64:
        raise ValueError(f"invalid keypair file: {path}")
    keypair = Keypair.from_bytes(bytes(raw))
    return keypair, bytes(keypair.pubkey())


def probe_instruction_accounts(probe_id: str, payer: Pubkey) -> list[AccountMeta]:
    if probe_id == "oracle_staleness_borrow":
        return borrow_obligation_v2_probe_accounts(payer)

    accounts = [AccountMeta(payer, is_signer=True, is_writable=True)]
    for spec in probe_account_specs(probe_id):
        accounts.append(
            AccountMeta(
                Pubkey.from_string(spec.pubkey),
                is_signer=spec.is_signer,
                is_writable=spec.is_writable,
            )
        )
    return accounts


def _pubkey(value: str) -> Pubkey:
    return Pubkey.from_string(value)


def _meta(value: str | Pubkey, *, signer: bool = False, writable: bool = False) -> AccountMeta:
    pubkey = value if isinstance(value, Pubkey) else _pubkey(value)
    return AccountMeta(pubkey, is_signer=signer, is_writable=writable)


def derive_vanilla_obligation(owner: Pubkey, lending_market: str) -> Pubkey:
    program = _pubkey(KLEND_PROGRAM)
    market = _pubkey(lending_market)
    default = Pubkey.default()
    obligation, _bump = Pubkey.find_program_address(
        [
            bytes([0]),
            bytes([0]),
            bytes(owner),
            bytes(market),
            bytes(default),
            bytes(default),
        ],
        program,
    )
    return obligation


def derive_user_metadata(owner: Pubkey) -> Pubkey:
    program = _pubkey(KLEND_PROGRAM)
    user_metadata, _bump = Pubkey.find_program_address([b"user_meta", bytes(owner)], program)
    return user_metadata


def derive_associated_token_account(owner: Pubkey, mint: str) -> Pubkey:
    ata_program = _pubkey(ASSOCIATED_TOKEN_PROGRAM)
    token_program = _pubkey(SPL_TOKEN_PROGRAM)
    mint_pubkey = _pubkey(mint)
    ata, _bump = Pubkey.find_program_address(
        [bytes(owner), bytes(token_program), bytes(mint_pubkey)],
        ata_program,
    )
    return ata


def init_user_metadata_data() -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("init_user_metadata")) + bytes(Pubkey.default())


def init_obligation_data(tag: int = 0, obligation_id: int = 0) -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("init_obligation")) + bytes([tag, obligation_id])


def refresh_reserve_data() -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("refresh_reserve"))


def refresh_obligation_data() -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("refresh_obligation"))


def _optional_account(value: str | None, *, writable: bool = False) -> AccountMeta:
    value = (value or "").strip()
    if not value:
        return _meta(KLEND_PROGRAM)
    return _meta(value, writable=writable)


def borrow_refresh_prelude_instructions(payer: Pubkey) -> list[Instruction]:
    accounts = load_klend_accounts()
    reserve = accounts["reserves"]["USDC"]
    obligation = derive_vanilla_obligation(payer, accounts["market_pubkey"])
    program = _pubkey(KLEND_PROGRAM)
    refresh_reserve = Instruction(
        program,
        refresh_reserve_data(),
        [
            _meta(reserve["pubkey"], writable=True),
            _meta(accounts["market_pubkey"]),
            _optional_account(reserve.get("pyth_oracle")),
            _optional_account(reserve.get("switchboard_price_oracle")),
            _optional_account(reserve.get("switchboard_twap_oracle")),
            _optional_account(reserve.get("scope_prices")),
        ],
    )
    refresh_obligation = Instruction(
        program,
        refresh_obligation_data(),
        [
            _meta(accounts["market_pubkey"]),
            _meta(obligation, writable=True),
        ],
    )
    return [refresh_reserve, refresh_obligation]


def build_signed_borrow_setup_transaction(
    *,
    keypair: Keypair,
    recent_blockhash: bytes,
) -> tuple[bytes, dict[str, str]]:
    payer = keypair.pubkey()
    accounts = load_klend_accounts()
    market = accounts["market_pubkey"]
    user_metadata = derive_user_metadata(payer)
    obligation = derive_vanilla_obligation(payer, market)
    default = Pubkey.default()
    program = _pubkey(KLEND_PROGRAM)
    blockhash = Hash.from_bytes(recent_blockhash)
    init_user = Instruction(
        program,
        init_user_metadata_data(),
        [
            AccountMeta(payer, is_signer=True, is_writable=False),
            AccountMeta(payer, is_signer=True, is_writable=True),
            _meta(user_metadata, writable=True),
            _meta(KLEND_PROGRAM),
            _meta(SYSVAR_RENT),
            _meta(SYSTEM_PROGRAM),
        ],
    )
    init_obligation = Instruction(
        program,
        init_obligation_data(),
        [
            AccountMeta(payer, is_signer=True, is_writable=False),
            AccountMeta(payer, is_signer=True, is_writable=True),
            _meta(obligation, writable=True),
            _meta(market),
            _meta(default),
            _meta(default),
            _meta(user_metadata),
            _meta(SYSVAR_RENT),
            _meta(SYSTEM_PROGRAM),
        ],
    )
    message = Message.new_with_blockhash([init_user, init_obligation], payer, blockhash)
    return bytes(Transaction([keypair], message, blockhash)), {
        "user_metadata": str(user_metadata),
        "obligation": str(obligation),
    }


def borrow_obligation_v2_probe_accounts(payer: Pubkey) -> list[AccountMeta]:
    """Source-derived `borrow_obligation_liquidity_v2` account order.

    KLend v2 wraps the legacy borrow account struct, then appends optional farms
    accounts and the farms program. Env overrides let a live probe supply real
    obligation/destination accounts when discovered; payer fallbacks intentionally
    fail later as state-validation evidence, not as an incomplete account list.
    """
    import os

    accounts = load_klend_accounts()
    reserve = accounts["reserves"]["USDC"]
    obligation = (
        os.environ.get("KLEND_OBLIGATION", "").strip()
        or str(derive_vanilla_obligation(payer, accounts["market_pubkey"]))
    )
    destination = (
        os.environ.get("KLEND_USER_DESTINATION_LIQUIDITY", "").strip()
        or str(derive_associated_token_account(payer, reserve["mint"]))
    )
    optional_none = KLEND_PROGRAM

    return [
        AccountMeta(payer, is_signer=True, is_writable=True),
        _meta(obligation, writable=True),
        _meta(accounts["market_pubkey"]),
        _meta(accounts["lending_market_authority"]),
        _meta(reserve["pubkey"], writable=True),
        _meta(reserve["mint"]),
        _meta(reserve["supply_vault"], writable=True),
        _meta(reserve["fee_vault"], writable=True),
        _meta(destination, writable=True),
        _meta(optional_none),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SYSVAR_INSTRUCTIONS),
        _meta(optional_none),
        _meta(optional_none),
        _meta(FARMS_PROGRAM),
    ]


def probe_instruction_account_summary(probe_id: str, payer: Pubkey) -> str:
    if probe_id == "oracle_staleness_borrow":
        roles = (
            "owner",
            "obligation",
            "lending_market",
            "lending_market_authority",
            "borrow_reserve",
            "borrow_reserve_liquidity_mint",
            "reserve_source_liquidity",
            "borrow_reserve_liquidity_fee_receiver",
            "user_destination_liquidity",
            "referrer_token_state",
            "token_program",
            "instruction_sysvar",
            "obligation_farm_user_state",
            "reserve_farm_state",
            "farms_program",
        )
        return ",".join(
            f"{role}:{str(meta.pubkey)[:8]}"
            for role, meta in zip(roles, borrow_obligation_v2_probe_accounts(payer), strict=True)
        )
    return ",".join(f"{str(meta.pubkey)[:8]}" for meta in probe_instruction_accounts(probe_id, payer))


def build_signed_probe_transaction(
    *,
    keypair: Keypair,
    probe_id: str,
    recent_blockhash: bytes,
) -> bytes:
    payer = keypair.pubkey()
    program = Pubkey.from_string(KLEND_PROGRAM)
    blockhash = Hash.from_bytes(recent_blockhash)
    instruction = Instruction(
        program,
        probe_instruction_data(probe_id),
        probe_instruction_accounts(probe_id, payer),
    )
    instructions = [instruction]
    if probe_id == "oracle_staleness_borrow":
        instructions = borrow_refresh_prelude_instructions(payer) + instructions
    message = Message.new_with_blockhash(instructions, payer, blockhash)
    return bytes(Transaction([keypair], message, blockhash))


def build_invoke_transaction(
    *,
    payer_pubkey: bytes,
    program_pubkey: bytes,
    recent_blockhash: bytes,
    instruction_data: bytes,
    include_system_program: bool = False,
) -> bytes:
    """Build unsigned legacy message invoking `program_pubkey` from payer."""
    _ = include_system_program
    payer = Pubkey.from_bytes(payer_pubkey)
    program = Pubkey.from_bytes(program_pubkey)
    blockhash = Hash.from_bytes(recent_blockhash)
    instruction = Instruction(
        program,
        instruction_data,
        [AccountMeta(payer, is_signer=True, is_writable=True)],
    )
    return bytes(Message.new_with_blockhash([instruction], payer, blockhash))


def build_signed_invoke_transaction(
    *,
    keypair: Keypair,
    program_pubkey: bytes,
    recent_blockhash: bytes,
    instruction_data: bytes,
) -> bytes:
    payer = keypair.pubkey()
    program = Pubkey.from_bytes(program_pubkey)
    blockhash = Hash.from_bytes(recent_blockhash)
    instruction = Instruction(
        program,
        instruction_data,
        [AccountMeta(payer, is_signer=True, is_writable=True)],
    )
    message = Message.new_with_blockhash([instruction], payer, blockhash)
    return bytes(Transaction([keypair], message, blockhash))
