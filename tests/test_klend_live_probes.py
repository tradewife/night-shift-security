"""Unit tests for KLend live probe helpers."""

import sys
from pathlib import Path

_SOLANA_ROOT = Path(__file__).resolve().parents[1] / "solana"
if str(_SOLANA_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOLANA_ROOT))

import klend_live_probes as klp  # noqa: E402


def test_usdc_micro_to_lamport_equiv_threshold():
    # 15 USDC drain ~= 0.1 SOL at $150/SOL
    lamports = klp._usdc_micro_to_lamport_equiv(15_000_000, sol_usd=150.0)
    assert lamports == 100_000_000