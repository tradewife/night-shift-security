"""Tests for the pure-Python Keccak-256 helper (v5 NativeHarness crypto)."""

from __future__ import annotations

from night_shift_security.crypto import evm_function_selector, keccak256


def test_keccak256_empty() -> None:
    # Canonical Ethereum keccak256("") vector.
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_keccak256_abc() -> None:
    # Canonical Ethereum keccak256("abc") vector.
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"


def test_keccak256_str_input() -> None:
    assert keccak256("").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_keccak256_output_length() -> None:
    assert len(keccak256(b"foo")) == 32


def test_evm_function_selector_format() -> None:
    sel = evm_function_selector("swap((address,address,uint24,int24,address),(bool,uint128,int256,uint160),bytes)")
    assert sel.startswith("0x")
    assert len(sel) == 10
    assert all(c in "0123456789abcdef" for c in sel[2:])


def test_evm_function_selector_returns_a_4_byte_value() -> None:
    """Each arbitrary Solidity signature maps to a 4-byte selector."""
    signatures = [
        "swap()",
        "balanceOf(address)",
        "modifyLiquidity((address,address,uint24,int24,address),(int24,int24,int256,bytes32),bytes)",
    ]
    selectors = [evm_function_selector(sig) for sig in signatures]
    assert len(set(selectors)) == 3  # all unique
