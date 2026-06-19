"""Solana legacy transaction builder for KLend CPI probe invokes."""

from __future__ import annotations

import json
import os
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


def _flash_reserve_symbol() -> str:
    return os.environ.get("NSS_KLEND_FLASH_RESERVE", "SOL").strip().upper() or "SOL"


def _flash_reserve_entry() -> dict[str, str]:
    accounts = load_klend_accounts()
    symbol = _flash_reserve_symbol()
    reserve = (accounts.get("reserves") or {}).get(symbol)
    if not reserve:
        raise KeyError(f"unknown flash reserve symbol: {symbol}")
    return reserve


def refresh_reserve_probe_accounts() -> list[AccountMeta]:
    """Account metas for standalone ``refresh_reserve`` (kamino-native-001)."""
    accounts = load_klend_accounts()
    reserve = accounts["reserves"]["USDC"]
    return [
        _meta(reserve["pubkey"], writable=True),
        _meta(accounts["market_pubkey"]),
        _optional_account(reserve.get("pyth_oracle")),
        _optional_account(reserve.get("switchboard_price_oracle")),
        _optional_account(reserve.get("switchboard_twap_oracle")),
        _optional_account(reserve.get("scope_prices")),
    ]


def _optional_klend_account(pubkey: str | None, *, writable: bool = False) -> AccountMeta:
    value = (pubkey or "").strip()
    if not value:
        return _meta(KLEND_PROGRAM, writable=writable)
    return _meta(value, writable=writable)


def flash_borrow_probe_accounts(payer: Pubkey) -> list[AccountMeta]:
    """Source-derived ``flash_borrow_reserve_liquidity`` account order."""
    accounts = load_klend_accounts()
    reserve = _flash_reserve_entry()
    destination = derive_associated_token_account(payer, reserve["mint"])
    return [
        AccountMeta(payer, is_signer=True, is_writable=False),
        _meta(accounts["lending_market_authority"]),
        _meta(accounts["market_pubkey"]),
        _meta(reserve["pubkey"], writable=True),
        _meta(reserve["mint"]),
        _meta(reserve["supply_vault"], writable=True),
        _meta(destination, writable=True),
        _meta(reserve["fee_vault"], writable=True),
        _optional_klend_account(None, writable=True),
        _optional_klend_account(None, writable=True),
        _meta(SYSVAR_INSTRUCTIONS),
        _meta(SPL_TOKEN_PROGRAM),
    ]


def flash_repay_probe_accounts(payer: Pubkey) -> list[AccountMeta]:
    """Source-derived ``flash_repay_reserve_liquidity`` account order."""
    accounts = load_klend_accounts()
    reserve = _flash_reserve_entry()
    source = derive_associated_token_account(payer, reserve["mint"])
    return [
        AccountMeta(payer, is_signer=True, is_writable=False),
        _meta(accounts["lending_market_authority"]),
        _meta(accounts["market_pubkey"]),
        _meta(reserve["pubkey"], writable=True),
        _meta(reserve["mint"]),
        _meta(reserve["supply_vault"], writable=True),
        _meta(source, writable=True),
        _meta(reserve["fee_vault"], writable=True),
        _optional_klend_account(None, writable=True),
        _optional_klend_account(None, writable=True),
        _meta(SYSVAR_INSTRUCTIONS),
        _meta(SPL_TOKEN_PROGRAM),
    ]


def deposit_reserve_liquidity_probe_accounts(payer: Pubkey) -> list[AccountMeta]:
    """Account metas for ``deposit_reserve_liquidity`` probe.

    Account order from KLend interface:
    1. owner (signer)
    2. reserve (writable)
    3. lending_market (readonly)
    4. lending_market_authority (readonly)
    5. reserve_liquidity_mint (readonly)
    6. reserve_liquidity_supply (writable)
    7. reserve_collateral_mint (writable)
    8. user_source_liquidity (writable)
    9. user_destination_collateral (writable)
    10. TOKEN_PROGRAM_ID (readonly)
    11. liquidity_token_program (readonly)
    12. SYSVAR_INSTRUCTIONS_ID (readonly)
    """
    accounts = load_klend_accounts()
    reserve = accounts["reserves"]["USDC"]
    collateral_mint = reserve.get("collateral_mint", KLEND_PROGRAM)
    source = derive_associated_token_account(payer, reserve["mint"])
    destination = derive_associated_token_account(payer, collateral_mint)
    return [
        AccountMeta(payer, is_signer=True, is_writable=False),
        _meta(reserve["pubkey"], writable=True),
        _meta(accounts["market_pubkey"]),
        _meta(accounts["lending_market_authority"]),
        _meta(reserve["mint"]),
        _meta(reserve["supply_vault"], writable=True),
        _meta(collateral_mint, writable=True),
        _meta(source, writable=True),
        _meta(destination, writable=True),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SYSVAR_INSTRUCTIONS),
    ]


def redeem_reserve_collateral_probe_accounts(payer: Pubkey) -> list[AccountMeta]:
    """Account metas for ``redeem_reserve_collateral`` probe.

    Account order from KLend Anchor struct ``RedeemReserveCollateral``:
    1. owner (signer)
    2. lending_market (readonly)
    3. reserve (writable, has_one=lending_market)
    4. lending_market_authority (readonly, PDA)
    5. reserve_liquidity_mint (readonly)
    6. reserve_collateral_mint (writable)
    7. reserve_liquidity_supply (writable)
    8. user_source_collateral (writable, mint=reserve_collateral_mint)
    9. user_destination_liquidity (writable, mint=reserve_liquidity_mint, authority=owner)
    10. collateral_token_program (readonly)
    11. liquidity_token_program (readonly)
    12. instruction_sysvar_account (readonly)
    """
    accounts = load_klend_accounts()
    reserve = accounts["reserves"]["USDC"]
    collateral_mint = reserve.get("collateral_mint", KLEND_PROGRAM)
    source = derive_associated_token_account(payer, collateral_mint)
    destination = derive_associated_token_account(payer, reserve["mint"])
    return [
        AccountMeta(payer, is_signer=True, is_writable=False),
        _meta(accounts["market_pubkey"]),
        _meta(reserve["pubkey"], writable=True),
        _meta(accounts["lending_market_authority"]),
        _meta(reserve["mint"]),
        _meta(collateral_mint, writable=True),
        _meta(reserve["supply_vault"], writable=True),
        _meta(source, writable=True),
        _meta(destination, writable=True),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SYSVAR_INSTRUCTIONS),
    ]


def flash_borrow_reserve_liquidity_data(liquidity_amount: int = 1) -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("flash_borrow_reserve_liquidity")) + int(
        liquidity_amount
    ).to_bytes(8, "little")


def flash_repay_reserve_liquidity_data(
    liquidity_amount: int = 1,
    *,
    borrow_instruction_index: int = 0,
) -> bytes:
    from klend_v2 import anchor_discriminator

    return (
        bytes.fromhex(anchor_discriminator("flash_repay_reserve_liquidity"))
        + int(liquidity_amount).to_bytes(8, "little")
        + bytes([borrow_instruction_index & 0xFF])
    )


def probe_instruction_accounts(probe_id: str, payer: Pubkey) -> list[AccountMeta]:
    if probe_id == "refresh_reserve_live":
        return refresh_reserve_probe_accounts()
    if probe_id == "oracle_staleness_borrow":
        return borrow_obligation_v2_probe_accounts(payer)
    if probe_id == "flash_loan_collateral_loop":
        return flash_borrow_probe_accounts(payer)
    if probe_id == "deposit_reserve_liquidity_live":
        return deposit_reserve_liquidity_probe_accounts(payer)
    if probe_id == "redeem_reserve_collateral_live":
        return redeem_reserve_collateral_probe_accounts(payer)
    if probe_id == "flash_borrow_reserve_liquidity_live":
        return flash_borrow_probe_accounts(payer)

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


def refresh_obligation_instruction(
    payer: Pubkey,
    *,
    deposit_symbols: tuple[str, ...] = (),
) -> Instruction:
    accounts = load_klend_accounts()
    obligation = derive_vanilla_obligation(payer, accounts["market_pubkey"])
    remaining = [
        _meta(accounts["reserves"][symbol.strip().upper()]["pubkey"], writable=True)
        for symbol in deposit_symbols
        if symbol.strip()
    ]
    return Instruction(
        _pubkey(KLEND_PROGRAM),
        refresh_obligation_data(),
        [_meta(accounts["market_pubkey"]), _meta(obligation, writable=True), *remaining],
    )


def _optional_account(value: str | None, *, writable: bool = False) -> AccountMeta:
    value = (value or "").strip()
    if not value:
        return _meta(KLEND_PROGRAM)
    return _meta(value, writable=writable)


def deposit_collateral_and_obligation_data(liquidity_amount: int) -> bytes:
    from klend_v2 import anchor_discriminator

    instruction = os.environ.get(
        "NSS_KLEND_DEPOSIT_INSTRUCTION",
        "deposit_reserve_liquidity_and_obligation_collateral",
    ).strip()
    return bytes.fromhex(anchor_discriminator(instruction)) + int(liquidity_amount).to_bytes(8, "little")


def deposit_collateral_and_obligation_v2_data(liquidity_amount: int) -> bytes:
    return deposit_collateral_and_obligation_data(liquidity_amount)


def deposit_collateral_and_obligation_accounts(
    payer: Pubkey,
    *,
    collateral_symbol: str = "SOL",
) -> list[AccountMeta]:
    from klend_account_discovery import reserve_collateral_accounts

    accounts = load_klend_accounts()
    symbol = collateral_symbol.strip().upper() or "SOL"
    reserve_entry = accounts["reserves"][symbol]
    reserve_pubkey = reserve_entry["pubkey"]
    collateral_mint, collateral_supply_vault = reserve_collateral_accounts(symbol=symbol)
    user_source_liquidity = derive_associated_token_account(payer, reserve_entry["mint"])
    return [
        AccountMeta(payer, is_signer=True, is_writable=True),
        _meta(derive_vanilla_obligation(payer, accounts["market_pubkey"]), writable=True),
        _meta(accounts["market_pubkey"]),
        _meta(accounts["lending_market_authority"]),
        _meta(reserve_pubkey, writable=True),
        _meta(reserve_entry["mint"]),
        _meta(reserve_entry["supply_vault"], writable=True),
        _meta(collateral_mint, writable=True),
        _meta(collateral_supply_vault, writable=True),
        _meta(user_source_liquidity, writable=True),
        _optional_klend_account(None, writable=False),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SYSVAR_INSTRUCTIONS),
    ]


def deposit_collateral_and_obligation_v2_accounts(payer: Pubkey, *, collateral_symbol: str = "SOL") -> list[AccountMeta]:
    from klend_account_discovery import reserve_collateral_accounts

    accounts = load_klend_accounts()
    symbol = collateral_symbol.strip().upper() or "SOL"
    reserve_entry = accounts["reserves"][symbol]
    reserve_pubkey = reserve_entry["pubkey"]
    collateral_mint, collateral_supply_vault = reserve_collateral_accounts(symbol=symbol)
    user_source_liquidity = derive_associated_token_account(payer, reserve_entry["mint"])
    return [
        AccountMeta(payer, is_signer=True, is_writable=True),
        _meta(derive_vanilla_obligation(payer, accounts["market_pubkey"]), writable=True),
        _meta(accounts["market_pubkey"]),
        _meta(accounts["lending_market_authority"]),
        _meta(reserve_pubkey, writable=True),
        _meta(reserve_entry["mint"]),
        _meta(reserve_entry["supply_vault"], writable=True),
        _meta(collateral_mint, writable=True),
        _meta(collateral_supply_vault, writable=True),
        _meta(user_source_liquidity, writable=True),
        _optional_klend_account(None, writable=False),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SPL_TOKEN_PROGRAM),
        _meta(SYSVAR_INSTRUCTIONS),
        _optional_klend_account(None, writable=True),
        _optional_klend_account(None, writable=True),
        _meta(FARMS_PROGRAM),
    ]


def _collateral_reserve_context(payer: Pubkey, *, collateral_symbol: str = "SOL") -> dict[str, str]:
    from klend_account_discovery import derive_obligation_farm_user_state, reserve_farm_collateral_account

    accounts = load_klend_accounts()
    symbol = collateral_symbol.strip().upper() or "SOL"
    reserve = accounts["reserves"][symbol]
    market = accounts["market_pubkey"]
    obligation = str(derive_vanilla_obligation(payer, market))
    farm_state = reserve_farm_collateral_account(symbol=symbol)
    return {
        "market": market,
        "lending_market_authority": accounts["lending_market_authority"],
        "reserve_pubkey": reserve["pubkey"],
        "obligation": obligation,
        "farm_state": farm_state,
        "obligation_farm_user_state": derive_obligation_farm_user_state(
            farm_state=farm_state,
            obligation=obligation,
        ),
    }


def init_obligation_farms_for_reserve_data(*, mode: int = 0) -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("init_obligation_farms_for_reserve")) + bytes([mode])


def init_obligation_farms_for_reserve_accounts(payer: Pubkey, *, collateral_symbol: str = "SOL") -> list[AccountMeta]:
    ctx = _collateral_reserve_context(payer, collateral_symbol=collateral_symbol)
    return [
        AccountMeta(payer, is_signer=True, is_writable=True),
        AccountMeta(payer, is_signer=False, is_writable=False),
        _meta(ctx["obligation"], writable=True),
        _meta(ctx["lending_market_authority"]),
        _meta(ctx["reserve_pubkey"], writable=True),
        _meta(ctx["farm_state"], writable=True),
        _meta(ctx["obligation_farm_user_state"], writable=True),
        _meta(ctx["market"]),
        _meta(FARMS_PROGRAM),
        _meta(SYSVAR_RENT),
        _meta(SYSTEM_PROGRAM),
    ]


def refresh_obligation_farms_for_reserve_data(*, mode: int = 0) -> bytes:
    from klend_v2 import anchor_discriminator

    return bytes.fromhex(anchor_discriminator("refresh_obligation_farms_for_reserve")) + bytes([mode])


def refresh_obligation_farms_for_reserve_accounts(payer: Pubkey, *, collateral_symbol: str = "SOL") -> list[AccountMeta]:
    ctx = _collateral_reserve_context(payer, collateral_symbol=collateral_symbol)
    return [
        AccountMeta(payer, is_signer=True, is_writable=False),
        _meta(ctx["obligation"]),
        _meta(ctx["lending_market_authority"]),
        _meta(ctx["reserve_pubkey"]),
        _meta(ctx["farm_state"], writable=True),
        _meta(ctx["obligation_farm_user_state"], writable=True),
        _meta(ctx["market"]),
        _meta(FARMS_PROGRAM),
        _meta(SYSVAR_RENT),
        _meta(SYSTEM_PROGRAM),
    ]


def collateral_deposit_refresh_instructions(payer: Pubkey, *, collateral_symbol: str = "SOL") -> list[Instruction]:
    accounts = load_klend_accounts()
    symbol = collateral_symbol.strip().upper() or "SOL"
    reserve = accounts["reserves"][symbol]
    obligation = derive_vanilla_obligation(payer, accounts["market_pubkey"])
    program = _pubkey(KLEND_PROGRAM)
    refresh_farms = Instruction(
        program,
        refresh_obligation_farms_for_reserve_data(mode=0),
        refresh_obligation_farms_for_reserve_accounts(payer, collateral_symbol=symbol),
    )
    refresh_obligation = refresh_obligation_instruction(payer)
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
    return [refresh_reserve, refresh_obligation, refresh_farms]


def build_signed_collateral_deposit_transaction(
    *,
    keypair: Keypair,
    recent_blockhash: bytes,
    liquidity_amount: int | None = None,
    collateral_symbol: str = "SOL",
) -> bytes:
    payer = keypair.pubkey()
    amount = int(
        liquidity_amount
        if liquidity_amount is not None
        else int(os.environ.get("NSS_KLEND_COLLATERAL_LAMPORTS", "100000000"))
    )
    program = _pubkey(KLEND_PROGRAM)
    blockhash = Hash.from_bytes(recent_blockhash)
    use_v2 = os.environ.get("NSS_KLEND_DEPOSIT_INSTRUCTION", "").strip().endswith("_v2")
    deposit_ix = Instruction(
        program,
        deposit_collateral_and_obligation_data(amount),
        (
            deposit_collateral_and_obligation_v2_accounts(payer, collateral_symbol=collateral_symbol)
            if use_v2
            else deposit_collateral_and_obligation_accounts(payer, collateral_symbol=collateral_symbol)
        ),
    )
    refresh_instructions = collateral_deposit_refresh_instructions(
        payer,
        collateral_symbol=collateral_symbol,
    )
    post_farm_refresh = Instruction(
        program,
        refresh_obligation_farms_for_reserve_data(mode=0),
        refresh_obligation_farms_for_reserve_accounts(payer, collateral_symbol=collateral_symbol),
    )
    instructions = refresh_instructions + [deposit_ix, post_farm_refresh]
    message = Message.new_with_blockhash(instructions, payer, blockhash)
    return bytes(Transaction([keypair], message, blockhash))


def _refresh_reserve_instruction(reserve_entry: dict[str, str], market_pubkey: str) -> Instruction:
    return Instruction(
        _pubkey(KLEND_PROGRAM),
        refresh_reserve_data(),
        [
            _meta(reserve_entry["pubkey"], writable=True),
            _meta(market_pubkey),
            _optional_account(reserve_entry.get("pyth_oracle")),
            _optional_account(reserve_entry.get("switchboard_price_oracle")),
            _optional_account(reserve_entry.get("switchboard_twap_oracle")),
            _optional_account(reserve_entry.get("scope_prices")),
        ],
    )


def borrow_refresh_prelude_instructions(payer: Pubkey) -> list[Instruction]:
    accounts = load_klend_accounts()
    market = accounts["market_pubkey"]
    collateral_symbol = os.environ.get("NSS_KLEND_COLLATERAL_SYMBOL", "SOL").strip().upper() or "SOL"
    return [
        _refresh_reserve_instruction(accounts["reserves"][collateral_symbol], market),
        _refresh_reserve_instruction(accounts["reserves"]["USDC"], market),
        refresh_obligation_instruction(payer, deposit_symbols=(collateral_symbol,)),
    ]


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
    setup_instructions = [init_user, init_obligation]
    if os.environ.get("NSS_KLEND_INIT_OBLIGATION_FARM", "1").lower() not in ("0", "false", "no"):
        setup_instructions.append(
            Instruction(
                program,
                init_obligation_farms_for_reserve_data(mode=0),
                init_obligation_farms_for_reserve_accounts(payer, collateral_symbol="SOL"),
            )
        )
    message = Message.new_with_blockhash(setup_instructions, payer, blockhash)
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
    if probe_id == "refresh_reserve_live":
        roles = (
            "reserve",
            "lending_market",
            "pyth_oracle",
            "switchboard_price_oracle",
            "switchboard_twap_oracle",
            "scope_prices",
        )
        return ",".join(
            f"{role}:{str(meta.pubkey)[:8]}"
            for role, meta in zip(roles, refresh_reserve_probe_accounts(), strict=True)
        )
    if probe_id == "flash_loan_collateral_loop":
        roles = (
            "user_transfer_authority",
            "lending_market_authority",
            "lending_market",
            "reserve",
            "reserve_liquidity_mint",
            "reserve_source_liquidity",
            "user_destination_liquidity",
            "reserve_liquidity_fee_receiver",
            "referrer_token_state",
            "referrer_account",
            "sysvar_info",
            "token_program",
        )
        return ",".join(
            f"{role}:{str(meta.pubkey)[:8]}"
            for role, meta in zip(roles, flash_borrow_probe_accounts(payer), strict=True)
        )
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
    instructions: list[Instruction]
    if probe_id in ("flash_loan_collateral_loop", "flash_borrow_reserve_liquidity_live"):
        amount = int(os.environ.get("NSS_KLEND_FLASH_AMOUNT", "1000000"))
        borrow_ix = Instruction(
            program,
            flash_borrow_reserve_liquidity_data(amount),
            flash_borrow_probe_accounts(payer),
        )
        repay_ix = Instruction(
            program,
            flash_repay_reserve_liquidity_data(amount, borrow_instruction_index=0),
            flash_repay_probe_accounts(payer),
        )
        instructions = [borrow_ix, repay_ix]
    else:
        instruction = Instruction(
            program,
            probe_instruction_data(probe_id),
            probe_instruction_accounts(probe_id, payer),
        )
        instructions = [instruction]
        if probe_id == "refresh_reserve_live":
            instructions = [borrow_refresh_prelude_instructions(payer)[0]]
        elif probe_id == "oracle_staleness_borrow":
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
