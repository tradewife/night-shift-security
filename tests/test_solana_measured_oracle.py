"""Tests for Solana MeasuredImpactOracle (Phase 8)."""

from __future__ import annotations

import struct
from unittest.mock import patch

import pytest

from night_shift_security.impact import solana_measured_oracle as smo
from night_shift_security.native import kamino


def _fake_reserve_data(
    *,
    last_slot: int = 100,
    borrowed_lo: int = 1000,
    borrowed_hi: int = 0,
    cum_rate: tuple[int, int, int, int] = (1, 2, 3, 4),
) -> bytes:
    data = bytearray(400)
    struct.pack_into("<Q", data, smo._RESERVE_LAST_UPDATE_SLOT_OFF, last_slot)
    struct.pack_into("<QQ", data, smo._RESERVE_BORROWED_SF_OFF, borrowed_lo, borrowed_hi)
    struct.pack_into("<QQQQ", data, smo._RESERVE_CUM_BORROW_RATE_OFF, *cum_rate)
    return bytes(data)


def test_schema_version_constant() -> None:
    assert smo.SCHEMA_VERSION == "measured-oracle-solana.v1"


def test_parse_reserve_fields() -> None:
    data = _fake_reserve_data(last_slot=42)
    fields = smo.parse_reserve_fields(data, kamino.DEFAULT_USDC_RESERVE)
    assert fields.last_update_slot == "42"
    assert fields.borrowed_amount_sf == "1000"


def test_parse_reserve_fields_too_short() -> None:
    with pytest.raises(RuntimeError, match="reserve_data_too_short"):
        smo.parse_reserve_fields(b"\x00" * 10, "x")


def test_delta_slot_advance_measured() -> None:
    pre = smo.SolanaMeasureState(
        slot=100,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot(
            reserve_pubkey="r",
            last_update_slot="100",
            borrowed_amount_sf="1000",
            cumulative_borrow_rate="1:2:3:4",
        ),
    )
    post = smo.SolanaMeasureState(
        slot=150,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot(
            reserve_pubkey="r",
            last_update_slot="105",
            borrowed_amount_sf="1000",
            cumulative_borrow_rate="1:2:3:4",
        ),
    )
    result = smo.delta(pre, post)
    assert result["measured_impact"] is True
    assert result["classification_reason"] == "reserve_last_update_slot_advanced"


def test_delta_supply_vault_threshold() -> None:
    pre = smo.SolanaMeasureState(
        slot=1,
        token_accounts=[
            smo.TokenAccountSlot(pubkey="v", mint="m", amount="0"),
        ],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "0:0:0:0", "0"),
    )
    post = smo.SolanaMeasureState(
        slot=2,
        token_accounts=[
            smo.TokenAccountSlot(pubkey="v", mint="m", amount=str(smo.MEASURED_SPL_THRESHOLD + 1)),
        ],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "0:0:0:0", str(smo.MEASURED_SPL_THRESHOLD + 1)),
    )
    result = smo.delta(pre, post)
    assert result["measured_impact"] is True


def test_delta_zero_honest() -> None:
    fields = smo.ReserveFieldSlot("r", "5", "0", "0:0:0:0", "0")
    state = smo.SolanaMeasureState(slot=5, token_accounts=[], reserve_fields=fields)
    result = smo.delta(state, state)
    assert result["measured_impact"] is False


def test_build_evidence_envelope_shape() -> None:
    spec = smo.SolanaMeasureSpec(rpc_url="http://localhost")
    pre = smo.SolanaMeasureState(
        slot=1,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "0:0:0:0"),
    )
    post = smo.SolanaMeasureState(
        slot=2,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "2", "0", "0:0:0:0"),
    )
    env = smo.build_evidence_envelope(spec, pre, post)
    assert env["measured_impact"] is True
    assert env["spec"]["program_id"] == kamino.KLEND_PROGRAM
    assert env["on_chain_state_diff"]["non_fee"] is True


def test_write_evidence(tmp_path) -> None:
    path = smo.write_evidence({"measured_impact": True}, "kamino", output_dir=tmp_path)
    assert path.name == "kamino_measured_delta.json"
    assert path.is_file()


def test_read_state_mocked() -> None:
    spec = smo.SolanaMeasureSpec(
        rpc_url="http://localhost",
        reserve_pubkey=kamino.DEFAULT_USDC_RESERVE,
    )
    reserve_data = _fake_reserve_data()

    with (
        patch("night_shift_security.native.kamino.get_slot", return_value=200),
        patch.object(smo, "_fetch_account_data", return_value=reserve_data),
        patch.object(smo, "_token_balance", return_value=smo.TokenAccountSlot("v", "m", "5000")),
    ):
        state = smo.read_state(spec)
        assert state.slot == 200
        assert state.reserve_fields.last_update_slot == "100"


def test_capture_cross_slot_mocked(tmp_path, monkeypatch) -> None:
    pre_state = smo.SolanaMeasureState(
        slot=1,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "0:0:0:0"),
    )
    post_state = smo.SolanaMeasureState(
        slot=3,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "2", "0", "0:0:0:0"),
    )
    monkeypatch.chdir(tmp_path)
    import time

    with (
        patch.object(smo, "read_state", side_effect=[pre_state, post_state]),
        patch.object(smo, "_latest_signature_slot", return_value=0),
        patch.object(time, "sleep"),
    ):
        env = smo.capture_cross_slot("http://localhost", slug="kamino")
        assert env["measured_impact"] is True


def test_measured_thresholds_positive() -> None:
    assert smo.MEASURED_LAMPORT_THRESHOLD > 0
    assert smo.MEASURED_SPL_THRESHOLD > 0


def test_delta_cumulative_rate_change() -> None:
    pre = smo.SolanaMeasureState(
        slot=1,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "1:2:3:4"),
    )
    post = smo.SolanaMeasureState(
        slot=2,
        token_accounts=[],
        reserve_fields=smo.ReserveFieldSlot("r", "1", "0", "5:6:7:8"),
    )
    result = smo.delta(pre, post)
    assert result["measured_impact"] is True
    assert result["classification_reason"] == "cumulative_borrow_rate_changed"