"""Tests for Jito native harness (Phase 9)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from night_shift_security.native import jito
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata() -> None:
    assert jito.HARNESS_TARGET == "jito"
    assert jito.HARNESS_CHAIN == "solana"


def test_program_ids() -> None:
    ids = jito.program_ids()
    assert ids["spl_stake_pool"] == "SPoo1Ku8WFXoNDMHPsrGSTSG1Y47rzgn41SLUNakuHy"
    assert ids["jito_stake_pool"].startswith("Jito4")


def test_discriminators_format() -> None:
    regex = re.compile(r"^0x[0-9a-f]{16}$")
    for value in jito.discriminators().values():
        assert regex.match(value)


def test_discriminators_match_helper() -> None:
    for name in jito.TOP_INSTRUCTIONS[:3]:
        assert jito.discriminators()[name] == anchor_discriminator(name)


def test_load_idl_fallback() -> None:
    idl = jito.load_idl(Path("/none"))
    assert idl["address"] == jito.SPL_STAKE_POOL_PROGRAM
    assert len(idl["instructions"]) == 10


def test_load_idl_artifact(tmp_path: Path) -> None:
    (tmp_path / "idl.json").write_text(json.dumps({"address": "x", "instructions": []}))
    assert jito.load_idl(tmp_path)["address"] == "x"


def test_resolve_accounts_mocked() -> None:
    with (
        patch.object(jito, "_rpc", side_effect=[
            {"value": {"executable": True, "lamports": 1}},
            42,
        ]),
    ):
        res = jito.resolve_accounts("", "http://localhost")
        assert res.slot == 42
        assert res.executable is True


def test_resolve_accounts_missing_program() -> None:
    with patch.object(jito, "_rpc", return_value={"value": None}):
        with pytest.raises(RuntimeError, match="rpc_no_code_at"):
            jito.resolve_accounts("", "http://localhost")


def test_instruction_names_count() -> None:
    assert len(jito.instruction_names()) == 10


def test_account_resolution_to_dict() -> None:
    d = jito.AccountResolution("p", 1, 2, True).to_dict()
    assert d["program_id"] == "p"