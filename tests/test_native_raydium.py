"""Tests for Raydium native harness (Phase 9)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native import raydium


def test_harness_metadata() -> None:
    assert raydium.HARNESS_TARGET == "raydium"
    assert raydium.CLMM_PROGRAM.startswith("CAMM")


def test_program_ids() -> None:
    assert raydium.program_ids()["clmm"] == raydium.CLMM_PROGRAM


def test_discriminators_count() -> None:
    assert len(raydium.discriminators()) == 10


def test_discriminator_hex_format() -> None:
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for v in raydium.discriminators().values():
        assert regex.match(v)


def test_load_idl_fallback() -> None:
    idl = raydium.load_idl(Path("/none"))
    assert idl["address"] == raydium.CLMM_PROGRAM


def test_load_idl_artifact(tmp_path: Path) -> None:
    d = tmp_path / "target" / "idl"
    d.mkdir(parents=True)
    (d / "amm_v3.json").write_text(json.dumps({"address": "a", "instructions": []}))
    assert raydium.load_idl(tmp_path)["address"] == "a"


def test_resolve_accounts_mocked() -> None:
    import base64

    payload = base64.b64encode(b"\x00" * 200).decode()
    with patch.object(
        raydium,
        "_rpc",
        side_effect=[
            {"value": {"lamports": 1}},
            {"value": {"lamports": 2, "data": [payload, "base64"]}},
            77,
        ],
    ):
        res = raydium.resolve_accounts("", "http://localhost")
        assert res.slot == 77
        assert res.data_len == 200


def test_resolve_accounts_no_pool() -> None:
    with patch.object(
        raydium,
        "_rpc",
        side_effect=[
            {"value": {"lamports": 1}},
            RuntimeError("rpc_error:getAccountInfo:WrongSize"),
            77,
        ],
    ):
        res = raydium.resolve_accounts("bad_pool", "http://localhost")
        assert res.slot == 77
        assert res.pool_state == ""


def test_default_pool_state_set() -> None:
    assert len(raydium.DEFAULT_POOL_STATE) >= 32


def test_instruction_names() -> None:
    assert "swap" in raydium.instruction_names()