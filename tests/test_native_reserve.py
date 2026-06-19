"""Tests for the Reserve Protocol native harness."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from night_shift_security.native.reserve import (
    DEFAULT_HYUSD_MAINNET,
    DEFAULT_RTOKEN_MAINNET,
    RTOKEN_FUNCTIONS,
    RTOKEN_VIEW_FUNCTIONS,
    _normalize_block,
    eth_call,
    get_code,
    load_abi,
    measure_state_diff,
    program_ids,
    resolve_rtoken,
    selectors,
    signatures,
)


def _expected_eusd() -> str:
    """Canonical eUSD mainnet address (lowercased).

    Recovered by concatenation: ``0x`` + ``A0d69E286B938e21``.lower() +
    ``CBf7E51D71F6A4c8918f482F``.lower(). Hardcoded in the harness as
    `_EUSD_HEX_HEAD` and `_EUSD_HEX_TAIL`.
    """
    return "0x" + "A0d69E286B938e21".lower() + "CBf7E51D71F6A4c8918f482F".lower()


# ------------------------------------------------------------------ #
# Selector / signature tests
# ------------------------------------------------------------------ #


def test_selectors_returns_expected_keys():
    sels = selectors()
    assert "rtoken" in sels
    assert "rtoken_view" in sels
    assert isinstance(sels["rtoken"], dict)
    assert isinstance(sels["rtoken_view"], dict)


def test_issue_selector_is_10_chars():
    sels = selectors()
    sel = sels["rtoken"]["issue"]
    assert sel.startswith("0x")
    assert len(sel) == 10


def test_redeem_selector_matches_keccak():
    from night_shift_security.crypto import keccak256

    sels = selectors()
    sig = "redeem(uint256)"
    expected = "0x" + keccak256(sig.encode()).hex()[:8]
    assert sels["rtoken"]["redeem"] == expected


def test_total_supply_selector_matches_keccak():
    from night_shift_security.crypto import keccak256

    sels = selectors()
    expected = "0x" + keccak256("totalSupply()".encode()).hex()[:8]
    assert sels["rtoken_view"]["totalSupply"] == expected
    assert expected == "0x18160ddd"  # well-known ERC20 selector


def test_main_selector_matches_keccak():
    from night_shift_security.crypto import keccak256

    sels = selectors()
    expected = "0x" + keccak256("main()".encode()).hex()[:8]
    assert sels["rtoken_view"]["main"] == expected


def test_signatures_match_selectors():
    sigs = signatures()
    sels = selectors()
    for name in sels["rtoken"]:
        assert any(name in sig for sig in sigs["rtoken"])
    for name in sels["rtoken_view"]:
        assert any(name in sig for sig in sigs["rtoken_view"])


# ------------------------------------------------------------------ #
# Program IDs / addresses
# ------------------------------------------------------------------ #


def test_default_rtoken_matches_eUSD_address():
    """eUSD is the canonical mainnet proxy pointed at by the v6 harness."""
    assert DEFAULT_RTOKEN_MAINNET == _expected_eusd()


def test_default_rtoken_lowercase_form():
    # The harness returns a lowercase 0x-prefixed 42-char string.
    assert len(DEFAULT_RTOKEN_MAINNET) == 42
    cleaned = DEFAULT_RTOKEN_MAINNET.removeprefix("0x")
    assert len(cleaned) == 40 and all(c in "0123456789abcdef" for c in cleaned)


def test_default_hyUSD_address_is_distinct():
    assert DEFAULT_HYUSD_MAINNET != DEFAULT_RTOKEN_MAINNET


def test_program_ids_returns_both_rtokens():
    ids = program_ids()
    assert "rtoken_eUSD" in ids and "rtoken_hyUSD" in ids
    assert ids["rtoken_eUSD"] == DEFAULT_RTOKEN_MAINNET


# ------------------------------------------------------------------ #
# ABI loader
# ------------------------------------------------------------------ #


def test_load_abi_returns_nonempty_list():
    abi = load_abi(Path("/home/kt/projects/rtp/night-shift-security/sources/reserve/repo"))
    assert isinstance(abi, list)
    assert len(abi) >= 6
    names = {entry.get("name") for entry in abi}
    for required in ("issue", "redeem", "mint", "melt", "setBasket", "refresh",
                     "totalSupply", "main"):
        assert required in names


def test_load_abi_includes_view_function_state_mutability():
    abi = load_abi(Path("/home/kt/projects/rtp/night-shift-security/sources/reserve/repo"))
    by_name = {entry["name"]: entry for entry in abi}
    assert by_name["totalSupply"]["stateMutability"] == "view"
    assert by_name["issue"]["stateMutability"] == "nonpayable"


def test_function_lists_disjoint_naming():
    """Mutating vs view function lists must not double-name a function."""
    mut_names = {e["name"] for e in RTOKEN_FUNCTIONS}
    view_names = {e["name"] for e in RTOKEN_VIEW_FUNCTIONS}
    assert mut_names.isdisjoint(view_names)


# ------------------------------------------------------------------ #
# Block normalization (JSON-RPC compatibility shim)
# ------------------------------------------------------------------ #


def test_normalize_block_passes_through_strings():
    assert _normalize_block("latest") == "latest"
    assert _normalize_block("0xdeadbeef") == "0xdeadbeef"


def test_normalize_block_coerces_int_to_hex():
    assert _normalize_block(0) == "0x0"
    assert _normalize_block(25354793) == "0x182e229"
    assert _normalize_block(1) == "0x1"


def test_normalize_block_treats_negative_as_latest():
    # `latest` is the safe fallback when block height is unknown / negative.
    assert _normalize_block(-1) == "latest"


# ------------------------------------------------------------------ #
# RPC shims
# ------------------------------------------------------------------ #


def test_eth_call_normalizes_int_block_to_hex():
    captured = {}

    def fake_call_rpc(rpc_url, method, params, timeout=10.0):
        captured["params"] = params
        return "0x" + "0" * 64

    import night_shift_security.native.reserve as reserve_mod

    with patch.object(reserve_mod, "_call_rpc", side_effect=fake_call_rpc):
        result = eth_call("0x" + "0" * 40, "0xabcd", "https://example/rpc", 12345)
    assert result.startswith("0x")
    # eth_call params: [{to,data}, block_tag] - block MUST be a hex string here
    assert captured["params"][1] == "0x3039"


def test_get_code_normalizes_int_block_to_hex():
    captured = {}

    def fake_call_rpc(rpc_url, method, params, timeout=10.0):
        captured["params"] = params
        return "0x6001600081"

    import night_shift_security.native.reserve as reserve_mod

    with patch.object(reserve_mod, "_call_rpc", side_effect=fake_call_rpc):
        result = get_code("0x" + "a" * 40, "https://example/rpc", 99)
    assert result.startswith("0x")
    assert captured["params"][1] == "0x63"  # 99 in hex


# ------------------------------------------------------------------ #
# LD-level resolver (mocked eth_call / get_code)
# ------------------------------------------------------------------ #


def _addr_word(addr_hex_no0x: str) -> str:
    # Pad to 32 bytes as a word like ABI uint256 - then narrow to address.
    raw = addr_hex_no0x.lower().removeprefix("0x")
    return "0x" + raw.rjust(64, "0")


def _build_mock_rpc(addr_main: str, total_supply: int):
    """Return a fake _call_rpc that responds to known selectors."""
    main_word = _addr_word(addr_main)
    ts_word = format(total_supply, "064x")

    def fake(rpc_url, method, params, timeout=10.0):
        m = method
        if m != "eth_call":
            # eth_blockNumber / eth_getCode
            if m == "eth_blockNumber":
                return hex(25_354_793)
            return "0x" + "60" + "60" + "00"  # arbitrary non-empty bytecode stub
        data = params[0]["data"]
        if data == "0x18160ddd":
            return "0x" + ts_word
        if data == "0xdffeadd0":
            return main_word
        raise AssertionError(f"unexpected eth_call data {data}")

    return fake


def test_resolve_rtoken_decodes_main_and_total_supply(monkeypatch):
    fake = _build_mock_rpc(
        addr_main="0x" + "7697ae4def3c3cd52493ba3a6f57fc6d8c59108a",
        total_supply=2_335_110 * 10**18,
    )
    import night_shift_security.native.reserve as reserve_mod

    monkeypatch.setattr(reserve_mod, "_call_rpc", fake)
    state = resolve_rtoken("https://example/rpc", 25_354_793, rtoken_address=_expected_eusd())
    assert state.rtoken_address == _expected_eusd()
    assert state.total_supply == 2_335_110 * 10**18
    assert state.main_address == "0x7697ae4def3c3cd52493ba3a6f57fc6d8c59108a"
    assert state.block == 25_354_793


def test_resolve_rtoken_raises_when_no_code(monkeypatch):
    def fake(rpc_url, method, params, timeout=10.0):
        if method == "eth_getCode":
            return "0x"
        raise AssertionError(method)

    import night_shift_security.native.reserve as reserve_mod

    monkeypatch.setattr(reserve_mod, "_call_rpc", fake)
    with pytest.raises(RuntimeError, match="rpc_no_code_at"):
        resolve_rtoken("https://example/rpc", "latest", rtoken_address=_expected_eusd())


def test_measure_state_diff_returns_pair(monkeypatch):
    addr = "0x" + "7697ae4def3c3cd52493ba3a6f57fc6d8c59108a"
    supply_pre = 2_000_000 * 10**18
    supply_post = 2_500_000 * 10**18

    calls = {"n": 0}

    def fake(rpc_url, method, params, timeout=10.0):
        m = method
        if m == "eth_getCode":
            return "0x" + "60" + "60" + "00"
        if m == "eth_call":
            data = params[0]["data"]
            if data == "0x18160ddd":
                # First two calls are pre (totalSupply,main); then post.
                # We alternate based on a counter.
                idx = calls["n"]
                calls["n"] += 1
                return "0x" + format(
                    supply_pre if idx in (0, 1) else supply_post,
                    "064x",
                )
            if data == "0xdffeadd0":
                idx = calls["n"]
                calls["n"] += 1
                return _addr_word(addr)
        if m == "eth_blockNumber":
            return hex(25_354_793)
        raise AssertionError(f"{m}")

    import night_shift_security.native.reserve as reserve_mod

    monkeypatch.setattr(reserve_mod, "_call_rpc", fake)
    res = measure_state_diff(
        "https://example/rpc",
        25_354_000,
        25_354_793,
        rtoken_address=_expected_eusd(),
        source_commit="879b0e955de3aa82b5b9f06c532429087ce7feea",
    )
    assert res.pre is not None and res.post is not None
    assert res.pre.total_supply == supply_pre
    assert res.post.total_supply == supply_post
    assert (res.post.total_supply - res.pre.total_supply) == (supply_post - supply_pre)
    assert res.pre.main_address == res.post.main_address == addr
    assert res.source_commit == "879b0e955de3aa82b5b9f06c532429087ce7feea"


def test_resolve_rtoken_translates_int_block(monkeypatch):
    seen_blocks = []

    def fake(rpc_url, method, params, timeout=10.0):
        if method == "eth_call":
            seen_blocks.append(params[1])
        if method == "eth_getCode":
            return "0x" + "60" + "60" + "00"
        if method == "eth_call":
            data = params[0]["data"]
            if data == "0x18160ddd":
                return "0x" + format(1, "064x")
            if data == "0xdffeadd0":
                return _addr_word("0x" + "1" * 40)
        raise AssertionError

    import night_shift_security.native.reserve as reserve_mod

    monkeypatch.setattr(reserve_mod, "_call_rpc", fake)
    resolve_rtoken("https://example/rpc", 25_354_793)
    # All observed block tags must be hex strings (not decimal ints)
    assert all(b.startswith("0x") or b == "latest" for b in seen_blocks)
    assert seen_blocks[0] == "0x182e229"  # 25354793
