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
    message = Message.new_with_blockhash([instruction], payer, blockhash)
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