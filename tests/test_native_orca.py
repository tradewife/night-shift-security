"""Tests for Orca native harness (Phase 9)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native import orca


def test_harness_metadata() -> None:
    assert orca.HARNESS_TARGET == "orca"
    assert orca.WHIRLPOOL_PROGRAM.startswith("whirL")


def test_program_ids() -> None:
    assert orca.program_ids()["whirlpool"] == orca.WHIRLPOOL_PROGRAM


def test_discriminators_swap_present() -> None:
    assert "swap" in orca.discriminators()


def test_discriminator_format() -> None:
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for v in orca.discriminators().values():
        assert regex.match(v)


def test_load_idl_fallback() -> None:
    idl = orca.load_idl(Path("/none"))
    assert idl["address"] == orca.WHIRLPOOL_PROGRAM


def test_load_idl_artifact(tmp_path: Path) -> None:
    d = tmp_path / "target" / "idl"
    d.mkdir(parents=True)
    (d / "whirlpool.json").write_text(json.dumps({"address": "w", "instructions": []}))
    assert orca.load_idl(tmp_path)["address"] == "w"


def test_resolve_accounts_mocked() -> None:
    import base64
    import struct

    data = bytearray(100)
    struct.pack_into("<Q", data, 65, 12345)
    payload = base64.b64encode(bytes(data)).decode()
    with patch.object(
        orca,
        "_rpc",
        side_effect=[
            {"value": {"lamports": 1}},
            {"value": {"lamports": 2, "data": [payload, "base64"]}},
            55,
        ],
    ):
        res = orca.resolve_accounts("", "http://localhost")
        assert res.slot == 55
        assert res.sqrt_price_hint == "12345"


def test_resolve_accounts_no_program() -> None:
    with patch.object(orca, "_rpc", return_value={"value": None}):
        with pytest.raises(RuntimeError, match="rpc_no_code_at"):
            orca.resolve_accounts("", "http://localhost")


def test_default_whirlpool_set() -> None:
    assert len(orca.DEFAULT_WHIRLPOOL) >= 32


def test_ten_instructions() -> None:
    assert len(orca.instruction_names()) == 10