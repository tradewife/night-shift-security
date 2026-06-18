"""Tiny pure-Python Keccak-256 helper.

This module provides ``keccak256(data)`` for environments where neither
``pycryptodome`` nor ``pysha3`` is available (the Night Shift v5 sandbox
ships neither — see ``pyproject.toml`` ``[project].dependencies``).

The implementation is the standard reference Keccak-f1600 permutation
used by Ethereum (NOT SHA-3 — note the different round constants / bit
ordering).

This module is intentionally dependency-free.
"""

from __future__ import annotations


_ROUND_CONSTANTS = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]

_ROTATIONS = [
    [0, 36, 3, 41, 18],
    [1, 44, 10, 45, 2],
    [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39, 8, 14],
]

MASK64 = (1 << 64) - 1


def _rotl(value: int, shift: int) -> int:
    value &= MASK64
    shift = shift % 64
    if shift == 0:
        return value
    return ((value << shift) | (value >> (64 - shift))) & MASK64


def _keccak_f(state):
    """In-place Keccak-f1600 permutation over a 5x5 uint64 state."""
    for round_idx in range(24):
        # Theta
        c = [
            state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
            for x in range(5)
        ]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        new = list(state)
        for y in range(5):
            for x in range(5):
                new[y * 5 + x] ^= d[x]

        # Rho + Pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + ((2 * x + 3 * y) % 5) * 5] = _rotl(new[x + 5 * y], _ROTATIONS[x][y])

        # Chi
        for y in range(5):
            for x in range(5):
                state[y * 5 + x] = b[y * 5 + x] ^ (
                    (~b[y * 5 + (x + 1) % 5]) & b[y * 5 + (x + 2) % 5] & MASK64
                )

        # Iota
        state[0] ^= _ROUND_CONSTANTS[round_idx]


def keccak256(data):
    """Return the Keccak-256 32-byte digest of ``data`` (Ethereum-flavoured)."""
    if isinstance(data, str):
        data = data.encode("utf-8")

    buf = bytearray(data)
    buf.append(0x01)
    while (len(buf) % 136) != 135:
        buf.append(0x00)
    buf.append(0x80)

    state = [0] * 25
    rate = 136
    for block in range(0, len(buf), rate):
        for i in range(17):
            state[i] ^= int.from_bytes(buf[block + i * 8 : block + i * 8 + 8], "little")
        _keccak_f(state)

    out = bytearray()
    for i in range(4):
        out.extend(state[i].to_bytes(8, "little"))
    return bytes(out)


def evm_function_selector(signature):
    """Return the canonical 4-byte EVM selector for a Solidity signature."""
    digest = keccak256(signature)
    return "0x" + digest[:4].hex()


__all__ = ["keccak256", "evm_function_selector"]
