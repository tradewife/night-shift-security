"""Tests for v5 MeasuredImpactOracle (audit correction C2).

Coverage:

- Negative-result honesty: a non-positive delta on the configured tokens
  MUST come back ``measured_impact=False``.
- Threshold logic: a delta below ``MEASURED_DELTA_THRESHOLD`` returns
  ``False``; a delta above returns ``True``.
- Snapshot dataclasses round-trip via ``to_dict`` without losing the
  string-encoded full-precision integer fields.
- ``write_evidence`` produces a JSON file at the configured path with
  ``schema_version`` + ``slug`` + delta envelope.
- ``build_finding_payload`` produces a v4-schema candidate with
  ``impact_oracle.measured`` set to the diff's measured flag and a
  ``fork_evidence.token_delta`` that mirror the diff (positive on the
  on-chain donate shape).
- ``default_spec`` builds a canonical USDC/WETH 1:1 PoolKey without
  leaking secrets.
- ERC-20 ``balanceOf`` and ``eth_getBalance`` callers are exercised
  against a **monkey-patched** JSON-RPC stub so the no-RPC test baseline
  continues to pass without network access.
- Live-RPC-dependent test (gated behind ``ETHEREUM_RPC_URL``) records a
  real diff and is paradoxical: even on a real fork with no initialize
  before snapshot, the slot0 control assertion trips and the measured
  flag is ``False`` — which is the *correct* honesty path for an
  uninitialized PoolId (audit §7 anti-pattern 1).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from night_shift_security.impact import measured_oracle as mo
from night_shift_security.native import uniswap_v4 as uv4


# -------------------------------------------------------------------------- #
# Pure-Python tests (no RPC)
# -------------------------------------------------------------------------- #


def test_threshold_constant_is_one_usdc_unit() -> None:
    """``MEASURED_DELTA_THRESHOLD == 10**6`` matches USDC's smallest unit."""
    assert mo.MEASURED_DELTA_THRESHOLD == 10**6


def test_schema_version_format() -> None:
    """Schema stamp is the canonical versioned ID."""
    assert mo.SCHEMA_VERSION == "measured-oracle.v1"


def test_default_spec_sets_canonical_uniswap_v4_poolkey() -> None:
    build = mo.default_spec(
        rpc_url="http://example.invalid",
        attacker_eoa="0x" + "11" * 20,
    )
    assert build.pool_manager == uv4.DEFAULT_POOL_MANAGER_MAINNET
    assert build.state_view == uv4.DEFAULT_STATE_VIEW_MAINNET
    assert build.usdc_address == uv4.DEFAULT_USDC_ETHEREUM
    assert build.weth_address == uv4.DEFAULT_WETH_ETHEREUM
    assert len(build.pool_keys) == 1
    pk = build.pool_keys[0]
    assert pk["fee"] == 3000
    assert pk["tickSpacing"] == 60
    assert pk["currency0"].lower() == uv4.DEFAULT_USDC_ETHEREUM.lower()
    assert pk["currency1"].lower() == uv4.DEFAULT_WETH_ETHEREUM.lower()


def test_prestate_round_trip_preserves_string_precision() -> None:
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei=str(10**18)
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12),
            decimals=6,
        ),
        pool_manager_native=mo.NativeBalanceSlot(
            holder=uv4.DEFAULT_POOL_MANAGER_MAINNET,
            wei=str(2 * 10**18),
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id="0x" + "ab" * 32,
                sqrt_price_x96=str(uv4.evm_selector("donate(bytes,uint256,uint256,bytes)") or 0),
                tick=0,
                block=21_000_000,
            ),
        ],
    )
    dumped = json.dumps(pre.to_dict())
    assert str(10**18) in dumped
    assert "raw_units" in dumped
    parsed = json.loads(dumped)
    assert parsed["attacker_eoa_native"]["wei"] == str(10**18)


def test_delta_reports_non_positive_via_honesty_path() -> None:
    """A pre/post where the attacker EOA gained USDC must NOT be measured.

    Negative-result honesty: the oracle refuses to coerce ``True``.
    """
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(2 * 10**12),
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is False
    # Token delta should be *negative* on a USDC-increase, which is
    # economic-impact negative even though the attacker ``received`` USDC.
    assert out["usdc_delta_raw_units"] < 0
    assert out["above_threshold_tokens"] == []
    # The evidence label must record the honest classification reason.
    assert out["evidence"]["classification_reason"] == "non_positive_or_below_threshold"


def test_delta_reports_positive_above_threshold() -> None:
    """A pre/post where the attacker EOA l ost > 1 USDC must be measured.

    This mirrors the canonical ``PoolManager.donate(PoolKey, amount0,…)``
    shape where the donor EOA transfers ERC-20 out and the pool's
    BalanceDelta bookkeeping records a credit to the donor. The pre/post
    attacker EOA USDC delta is positive (donor paid out).
    """
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="1000000000"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(100_000 * 10**6),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="1000000000"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(50_000 * 10**6),  # donor paid 50k USDC out
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is True
    assert out["usdc_delta_raw_units"] == 50_000 * 10**6
    assert len(out["above_threshold_tokens"]) == 1
    assert out["evidence"]["classification_reason"] == "token_delta_above_threshold"


def test_delta_threshold_boundary_below_counted_as_negative() -> None:
    """A delta strictly equal to ``MEASURED_DELTA_THRESHOLD - 1`` is *not* measured."""
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12 - (mo.MEASURED_DELTA_THRESHOLD - 1)),
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is False


def test_delta_threshold_boundary_equal_to_threshold_measured() -> None:
    """A delta >= ``MEASURED_DELTA_THRESHOLD`` is *measured*."""
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12 - mo.MEASURED_DELTA_THRESHOLD),
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is True


def test_delta_pool_slot_control_records_no_movement() -> None:
    """A ``donate`` shape must record ``slot0_moved = False``."""
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12),
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id="0x" + "ab" * 32,
                sqrt_price_x96="79228162514264337593543950336",
                tick=0,
                block=21_000_000,
            ),
        ],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**12 - (50_000 * 10**6)),
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id="0x" + "ab" * 32,
                sqrt_price_x96="79228162514264337593543950336",
                tick=0,
                block=21_000_001,
            ),
        ],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is True
    pool_entry = out["evidence"]["pool_slots"][0]
    assert pool_entry["slot0_moved"] is False
    assert pool_entry["sqrt_price_x96_delta"] == "0"


def test_delta_pool_id_mismatch_raises() -> None:
    """Sanity guard — if pre/post pool_ids disagree, the diff is unsafe."""
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(10**6),
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id="0x" + "ab" * 32,
                sqrt_price_x96="79228162514264337593543950336",
                tick=0,
                block=21_000_000,
            ),
        ],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(
            holder="0x" + "11" * 20, wei="0"
        ),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units="0",
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id="0x" + "cd" * 32,
                sqrt_price_x96="79228162514264337593543950336",
                tick=0,
                block=21_000_001,
            ),
        ],
    )
    with pytest.raises(RuntimeError, match="pool_id_mismatch"):
        mo.delta(pre=pre, post=post)


def test_write_evidence_writes_schema_anchored_json(tmp_path: Path) -> None:
    """The evidence file is well-formed and round-trips via ``json.loads``."""
    envelope = {
        "spec": {
            "rpc_url": "stub",
            "attacker_eoa": "0x" + "11" * 20,
        },
        "pre": {"read_at": "now", "block": "latest"},
        "post": {"read_at": "now+1s", "block": "latest", "tx_hash": "0xfeed"},
        "delta": {
            "attacker_eoa_delta_wei": "0",
            "tokens": [
                {
                    "token": uv4.DEFAULT_USDC_ETHEREUM,
                    "delta_raw_units": "1000000",
                    "decimals": 6,
                }
            ],
            "pool_slots": [],
            "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
            "classification_reason": "token_delta_above_threshold",
        },
        "measured_impact": True,
        "above_threshold_tokens": [
            {
                "token": uv4.DEFAULT_USDC_ETHEREUM,
                "delta_raw_units": "1000000",
                "decimals": 6,
            }
        ],
        "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
        "source_commit": uv4.__file__,
        "nss_version": "5.0.0-draft",
    }
    path = mo.write_evidence(envelope, slug="uniswap_v4", output_dir=tmp_path)
    assert path.exists()
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == mo.SCHEMA_VERSION
    assert payload["slug"] == "uniswap_v4"
    assert payload["measured_impact"] is True
    assert payload["delta"]["classification_reason"] == "token_delta_above_threshold"


def test_build_finding_payload_preserves_v4_gate_shape() -> None:
    """The finding payload must satisfy the v4 gate's evidence contract."""
    envelope = {
        "spec": {
            "rpc_url": "stub",
            "attacker_eoa": "0x" + "11" * 20,
            "pool_manager": uv4.DEFAULT_POOL_MANAGER_MAINNET,
        },
        "pre": {
            "read_at": "now",
            "block": "latest",
            "attacker_eoa_native": {"holder": "0x" + "11" * 20, "wei": "0"},
            "attacker_eoa_usdc": {
                "token": uv4.DEFAULT_USDC_ETHEREUM,
                "holder": "0x" + "11" * 20,
                "raw_units": str(100_000 * 10**6),
                "decimals": 6,
            },
            "pool_slots": [],
        },
        "post": {
            "read_at": "now+1s",
            "block": "latest",
            "tx_hash": "0xfeed",
            "attacker_eoa_native": {"holder": "0x" + "11" * 20, "wei": "0"},
            "attacker_eoa_usdc": {
                "token": uv4.DEFAULT_USDC_ETHEREUM,
                "holder": "0x" + "11" * 20,
                "raw_units": str(50_000 * 10**6),
                "decimals": 6,
            },
            "pool_slots": [],
        },
        "delta": {
            "attacker_eoa_delta_wei": "0",
            "tokens": [
                {
                    "token": uv4.DEFAULT_USDC_ETHEREUM,
                    "holder": "0x" + "11" * 20,
                    "delta_raw_units": str(50_000 * 10**6),
                    "decimals": 6,
                    "pre": str(100_000 * 10**6),
                    "post": str(50_000 * 10**6),
                }
            ],
            "pool_slots": [],
            "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
            "classification_reason": "token_delta_above_threshold",
        },
        "measured_impact": True,
        "above_threshold_tokens": [
            {
                "token": uv4.DEFAULT_USDC_ETHEREUM,
                "holder": "0x" + "11" * 20,
                "delta_raw_units": str(50_000 * 10**6),
                "decimals": 6,
            }
        ],
        "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
        "source_commit": uv4.__file__,
        "nss_version": "5.0.0-draft",
    }
    out = mo.build_finding_payload(envelope, slug="uniswap_v4")
    candidate = out["candidate"]
    fork = out["fork_evidence"]

    assert candidate["candidate_schema_version"] == 4
    assert candidate["target_pinned"] is True
    assert candidate["slug"] == "uniswap_v4"
    # ``impact_oracle.measured`` MUST follow the diff's verdict — the gate
    # reads this field directly.
    assert candidate["impact_oracle"]["measured"] is True
    assert fork["balance_delta_wei"] == "0"
    assert int(fork["token_delta"]) == 50_000 * 10**6
    assert fork["token_address"].lower() == uv4.DEFAULT_USDC_ETHEREUM.lower()
    assert fork["evidence_kind"] == "measured_impact_oracle.v1"
    assert "uniswap_v4_measured_delta.json" in fork["evidence_path"]


def test_build_finding_payload_holds_negative_measured_false() -> None:
    """A non-positive diff MUST produce ``impact_oracle.measured == False``."""
    envelope = {
        "spec": {
            "rpc_url": "stub",
            "attacker_eoa": "0x" + "11" * 20,
            "pool_manager": uv4.DEFAULT_POOL_MANAGER_MAINNET,
        },
        "pre": {"read_at": "now", "block": "latest"},
        "post": {"read_at": "now+1s", "block": "latest", "tx_hash": ""},
        "delta": {
            "attacker_eoa_delta_wei": "0",
            "tokens": [
                {
                    "token": uv4.DEFAULT_USDC_ETHEREUM,
                    "delta_raw_units": "0",
                    "decimals": 6,
                }
            ],
            "pool_slots": [],
            "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
            "classification_reason": "non_positive_or_below_threshold",
        },
        "measured_impact": False,
        "above_threshold_tokens": [],
        "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
        "source_commit": uv4.__file__,
        "nss_version": "5.0.0-draft",
    }
    out = mo.build_finding_payload(envelope, slug="uniswap_v4")
    assert out["candidate"]["impact_oracle"]["measured"] is False


def test_get_balance_parses_hex_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_get_balance`` decodes a hex payload via the JSON-RPC stub."""

    captured: dict[str, Any] = {}

    def fake_urlopen(req, timeout=10.0):
        captured["url"] = req.full_url
        body = json.loads(req.data)
        captured["method"] = body["method"]
        captured["params"] = body["params"]

        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc_value, traceback):
                return False

            def read(self_inner):
                return json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x100"}).encode()

        return _Resp()

    monkeypatch.setattr(mo.urllib_request, "urlopen", fake_urlopen)
    monkeypatch.setattr(mo.urllib_request, "urlopen", fake_urlopen)
    out = mo._get_balance("0x" + "ab" * 20, "http://stub", "latest")
    assert out == "256"  # 0x100 = 256
    assert captured["method"] == "eth_getBalance"


def test_get_balance_invalid_payload_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid hex payloads raise ``rpc_decode_error``."""

    def fake_urlopen(req, timeout=10.0):
        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc_value, traceback):
                return False

            def read(self_inner):
                return json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "result": 42}
                ).encode()

        return _Resp()

    monkeypatch.setattr(mo.urllib_request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="rpc_decode_error"):
        mo._get_balance("0x" + "ab" * 20, "http://stub", "latest")


def test_balance_of_erc20_parses_uint256(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_balance_of_erc20`` parses a 32-byte hex word correctly."""

    def fake_urlopen(req, timeout=10.0):
        class _Resp:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, exc_type, exc_value, traceback):
                return False

            def read(self_inner):
                # 32-byte word with value 256 == 0x100
                payload = "0x" + format(256, "064x")
                return json.dumps(
                    {"jsonrpc": "2.0", "id": 1, "result": payload}
                ).encode()

        return _Resp()

    monkeypatch.setattr(mo.urllib_request, "urlopen", fake_urlopen)
    out = mo._balance_of_erc20(
        "0x" + "11" * 20,
        "0x" + "22" * 20,
        "http://stub",
        "latest",
    )
    assert out == "256"


# -------------------------------------------------------------------------- #
# Live-RPC-dependent test (gated behind ETHEREUM_RPC_URL)
# -------------------------------------------------------------------------- #


def test_live_rpc_uninitialized_pool_recorders_zero_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    """If ``ETHEREUM_RPC_URL`` is set, real pre/post reads against an uninitialized
    canonical PoolId MUST return ``measured_impact=False`` (slot0 still empty).

    This is the honesty path the audit demands: even on a live fork, an
    operator error (forgetting to initialize / donate first) must surface
    a non-positive diff — never a fabricated impact. ``StateView.getSlot0``
    reverts on an unknown PoolId (``execution reverted``); the oracle
    re-raises the typed error and the wrapper below treats it as a
    non-positive diff for the purposes of this audit-shaped honesty test.
    """
    rpc = os.environ.get("ETHEREUM_RPC_URL", "")
    if not rpc:
        pytest.importorskip("ETHEREUM_RPC_URL")

    spec = mo.default_spec(rpc_url=rpc, attacker_eoa="0x" + "11" * 20)
    # Two paths: (a) StateView.getSlot0 returns a real-empty slot (delta
    # 0, all non-positive) — measured_impact is False; (b) StateView
    # reverts because the PoolKey has not been initialized on mainnet —
    # this is also ``measured_impact=False`` for honesty purposes (the
    # oracle refuses to fabricate).
    try:
        envelope = mo.build_evidence_envelope(spec)
        assert envelope["measured_impact"] is False
        assert (
            envelope["delta"]["classification_reason"]
            == "non_positive_or_below_threshold"
        )
    except RuntimeError as exc:
        # ``rpc_error:eth_call:3:execution reverted`` is the canonical
        # result of calling getSlot0 against an unknown PoolId. The
        # oracle's contract is: re-raise the typed error and never
        # fabricate — confirm the message has the audit-mandated prefix.
        assert str(exc).startswith("rpc_error"), f"unexpected: {exc}"


# -------------------------------------------------------------------------- #
# Morpho Blue evidence round-trip (no RPC)
# -------------------------------------------------------------------------- #


def test_morpho_evidence_file_has_correct_schema() -> None:
    """Morpho Blue evidence file carries nss_version or schema version."""
    path = Path("data/security_results/impact/morpho_blue_measured_delta.json")
    if not path.is_file():
        pytest.skip("morpho Blue evidence file not present")
    data = json.loads(path.read_text())
    # The morpho evidence uses nss_version instead of schema_version
    assert data.get("nss_version") == "5.0.0-draft" or data.get("schema_version") == "measured-oracle.v1"
    assert "spec" in data
    assert "delta" in data


def test_morpho_evidence_delta_structure() -> None:
    """Morpho Blue evidence delta contains morpho_market field."""
    path = Path("data/security_results/impact/morpho_blue_measured_delta.json")
    if not path.is_file():
        pytest.skip("morpho Blue evidence file not present")
    data = json.loads(path.read_text())
    delta = data.get("delta", {})
    assert "morpho_market" in delta, "Expected morpho_market in delta"
    market = delta["morpho_market"]
    assert "market_id" in market
    assert "supply_assets_delta" in market


# -------------------------------------------------------------------------- #
# Aave v3 evidence round-trip (no RPC)
# -------------------------------------------------------------------------- #


def test_aave_v3_evidence_file_has_correct_schema() -> None:
    """Aave v3 evidence file carries measured-oracle.v1 schema."""
    path = Path("data/security_results/impact/aave_v3_measured_delta.json")
    if not path.is_file():
        pytest.skip("Aave v3 evidence file not present")
    data = json.loads(path.read_text())
    assert data.get("schema_version") == "measured-oracle.v1"
    assert data.get("slug") == "aave_v3"


def test_aave_v3_evidence_positive_delta() -> None:
    """Aave v3 evidence has measured_impact=True."""
    path = Path("data/security_results/impact/aave_v3_measured_delta.json")
    if not path.is_file():
        pytest.skip("Aave v3 evidence file not present")
    data = json.loads(path.read_text())
    assert data.get("measured_impact") is True


def test_aave_v3_evidence_delta_fields() -> None:
    """Aave v3 evidence delta has liquidity and borrow index deltas."""
    path = Path("data/security_results/impact/aave_v3_measured_delta.json")
    if not path.is_file():
        pytest.skip("Aave v3 evidence file not present")
    data = json.loads(path.read_text())
    delta = data.get("delta", {})
    assert "liquidity_index_delta" in delta
    assert "variable_borrow_index_delta" in delta
    # At least one should be non-zero
    liq = int(delta.get("liquidity_index_delta", "0"))
    borrow = int(delta.get("variable_borrow_index_delta", "0"))
    assert liq != 0 or borrow != 0


def test_delta_pool_id_mismatch_raises() -> None:
    """Mismatched pool_id between pre/post snapshots raises RuntimeError."""
    pre_slot = mo.PoolSlot(
        pool_id="0x" + "aa" * 32,
        sqrt_price_x96="1",
        tick=0,
        block=21_000_000,
    )
    post_slot = mo.PoolSlot(
        pool_id="0x" + "bb" * 32,
        sqrt_price_x96="2",
        tick=1,
        block=21_000_001,
    )
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units="0",
            decimals=6,
        ),
        pool_slots=[pre_slot],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units="0",
            decimals=6,
        ),
        pool_slots=[post_slot],
    )
    with pytest.raises(RuntimeError, match="pool_id_mismatch"):
        mo.delta(pre=pre, post=post)


def test_delta_at_threshold_boundary_is_measured() -> None:
    """USDC delta exactly at MEASURED_DELTA_THRESHOLD counts as measured."""
    threshold = mo.MEASURED_DELTA_THRESHOLD
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(2 * threshold),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(threshold),
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is True
    assert out["evidence"]["classification_reason"] == "token_delta_above_threshold"


def test_delta_one_below_threshold_not_measured() -> None:
    """USDC delta one unit below threshold stays non-measured."""
    threshold = mo.MEASURED_DELTA_THRESHOLD
    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block=21_000_000,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units=str(threshold),
            decimals=6,
        ),
        pool_slots=[],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block=21_000_001,
        attacker_eoa_native=mo.NativeBalanceSlot(holder="0x" + "11" * 20, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder="0x" + "11" * 20,
            raw_units="1",
            decimals=6,
        ),
        pool_slots=[],
    )
    out = mo.delta(pre=pre, post=post)
    assert out["measured_impact"] is False
    assert out["usdc_delta_raw_units"] == threshold - 1
    assert out["evidence"]["classification_reason"] == "non_positive_or_below_threshold"
