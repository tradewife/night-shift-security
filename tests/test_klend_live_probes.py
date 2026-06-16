"""Unit tests for KLend live probe helpers."""

import sys
from pathlib import Path

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

import klend_live_probes as klp  # noqa: E402
import klend_probes as kp  # noqa: E402
import klend_v2 as kv2  # noqa: E402


def test_usdc_micro_to_lamport_equiv_threshold():
    # 15 USDC drain ~= 0.1 SOL at $150/SOL
    lamports = klp._usdc_micro_to_lamport_equiv(15_000_000, sol_usd=150.0)
    assert lamports == 100_000_000


def test_klend_instruction_map_has_real_discriminator():
    mapping = kv2.klend_instruction_map()
    borrow = mapping["instructions"]["borrow_obligation_liquidity_v2"]
    assert borrow["discriminator"].startswith("0x")
    assert len(borrow["discriminator"]) == 18
    assert mapping["probe_bindings"]["oracle_staleness_borrow"]["name"] == "borrow_obligation_liquidity_v2"


def test_probe_instruction_data_uses_v2_discriminator():
    data = kp.probe_instruction_data("oracle_staleness_borrow")
    discriminator = bytes.fromhex(kv2.anchor_discriminator("borrow_obligation_liquidity_v2"))
    assert data == discriminator + (1).to_bytes(8, "little")
    assert data != bytes([0x00, 0xCA, 0xFE, 0x01])


def test_liquidation_probe_instruction_data_serializes_three_args():
    data = kv2.instruction_data_for_probe("liquidation_solvency_gap")
    assert data[:8] == bytes.fromhex(kv2.anchor_discriminator("liquidate_obligation_and_redeem_reserve_collateral_v2"))
    assert len(data) == 32


def test_klend_account_roles_and_diff():
    accounts = {
        "market_pubkey": "market",
        "lending_market_authority": "authority",
        "global_config": "global",
        "reserves": {
            "USDC": {
                "pubkey": "reserve",
                "supply_vault": "supply",
                "fee_vault": "fee",
                "mint": "mint",
            }
        },
    }
    roles = kv2.build_account_roles(accounts)
    assert any(r["role"] == "usdc_supply_vault" for r in roles["roles"])
    diff = kv2.account_diff({"usdc": 10}, {"usdc": 7, "sol": 3})
    assert diff["deltas"]["usdc"] == -3
    assert diff["deltas"]["sol"] == 3


def test_klend_failure_classifier():
    assert kv2.classify_failure({"error": "data_account_missing:x"}) == "missing_account"
    assert kv2.classify_failure({"error": "program_not_deployed:x"}) == "missing_program"
    assert kv2.classify_failure({"failed_on_chain": True, "chain_error": {"InstructionError": [0, {"Custom": 102}]}}) == "bad_instruction_data"
    assert kv2.classify_failure({"failed_on_chain": True, "chain_error": {"InstructionError": [0, {"Custom": 3002}]}}) == "account_metas_incomplete"
    assert kv2.anchor_builtin_error_name({"chain_error": {"InstructionError": [0, {"Custom": 3002}]}}) == "AccountNotEnoughKeys"
    assert kv2.classify_failure({"probe_executed": True, "protocol_delta_lamports": 0, "wallet_delta_lamports": 5000}) == "fee_only"
    assert kv2.classify_failure({"probe_executed": True, "protocol_delta_lamports": 0, "wallet_delta_lamports": 0}) == "no_protocol_delta"
