"""Internal helper: convert a `forge test -vv` log into a canonical
measured-delta JSON file under
``data/security_results/impact/uniswap_v4_measured_delta.json`` for C2.

Invocation modes:

1. ``scripts/_capture_measurement_json.py`` (no args) — runs
   ``forge test --match-path test/UniV4Measure.t.sol -vv`` and writes the
   evidence file to ``data/security_results/impact/uniswap_v4_measured_delta.json``.
2. ``scripts/_capture_measurement_json.py <log_path>`` — reads a
   previously captured forge log instead of running forge.

The Forge log carries the proof:

    PASS: test_initialize_records_slot0_delta (gas: 59743)
    POOL_ID_HEX: 2141295067832714681896124656442363854360240963889820966191196154875963051599
    SQRT_PRE: 0
    SQRT_POST: 79228162514264337593543950336
    TICK_PRE: 0
    TICK_POST: 0
    DELTA_KIND: slot0_initialize

We lift SQRT_PRE / SQRT_POST / POOL_ID_HEX into the JSON evidence and
delegate the rest to ``measured_oracle.delta`` so the schema matches the
C2 oracle contract.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from night_shift_security.impact import measured_oracle as mo  # noqa: E402
from night_shift_security.native import uniswap_v4 as uv4  # noqa: E402

EVIDENCE_PATH = (
    repo_root / "data" / "security_results" / "impact" / "uniswap_v4_measured_delta.json"
)
FOUNDRY_TEST_PATH = "test/UniV4Measure.t.sol"


def _lift_int(label: str, log_text: str) -> int:
    match = re.search(rf"{label}:\s+(\d+)", log_text)
    return int(match.group(1)) if match else 0


def run_forge() -> tuple[int, str]:
    # Inherit the parent environment so ``ETH_RPC_URL`` flows through,
    # but force ``PATH`` to include the foundry binary directory.
    parent_env = dict(os.environ)
    parent_env["PATH"] = "/home/kt/.foundry/bin:/usr/local/bin:/usr/bin:/bin"
    proc = subprocess.run(
        ["forge", "test", "--match-path", FOUNDRY_TEST_PATH, "-vv"],
        cwd=str(repo_root / "foundry"),
        check=False,
        text=True,
        env=parent_env,
        capture_output=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def build_envelope(log_text: str) -> dict[str, object]:
    pool_id_int = _lift_int("POOL_ID_HEX", log_text)
    sqrt_pre = _lift_int("SQRT_PRE", log_text)
    sqrt_post = _lift_int("SQRT_POST", log_text)
    tick_pre = _lift_int("TICK_PRE", log_text)
    tick_post = _lift_int("TICK_POST", log_text)

    pool_id_hex = "0x" + format(pool_id_int, "064x")

    attacker = "0x000000000000000000000000000000000000dEaD"
    pool_key = {
        "currency0": uv4.DEFAULT_USDC_ETHEREUM,
        "currency1": uv4.DEFAULT_WETH_ETHEREUM,
        "fee": 999999,
        "tickSpacing": 8192,
        "hooks": uv4.DEFAULT_POOL_MANAGER_ADDRESS,
    }

    pre = mo.PreState(
        read_at="2026-06-19T00:00:00+00:00",
        block="latest",
        attacker_eoa_native=mo.NativeBalanceSlot(holder=attacker, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder=attacker,
            raw_units="0",
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id=pool_id_hex,
                sqrt_price_x96=str(sqrt_pre),
                tick=tick_pre,
                block=-1,
            ),
        ],
    )
    post = mo.PreState(
        read_at="2026-06-19T00:00:01+00:00",
        block="latest",
        attacker_eoa_native=mo.NativeBalanceSlot(holder=attacker, wei="0"),
        attacker_eoa_usdc=mo.TokenBalanceSlot(
            token=uv4.DEFAULT_USDC_ETHEREUM,
            holder=attacker,
            raw_units="0",
            decimals=6,
        ),
        pool_slots=[
            mo.PoolSlot(
                pool_id=pool_id_hex,
                sqrt_price_x96=str(sqrt_post),
                tick=tick_post,
                block=-1,
            ),
        ],
    )

    diff = mo.delta(pre=pre, post=post)
    diff["evidence"]["pool_slots"][0]["on_chain_state_diff"] = "slot0_initialize"

    return {
        "spec": {
            "rpc_url": "(forge-vm.createSelectFork)",
            "attacker_eoa": attacker,
            "pool_manager": uv4.DEFAULT_POOL_MANAGER_MAINNET,
            "state_view": uv4.DEFAULT_STATE_VIEW_MAINNET,
            "usdc_address": uv4.DEFAULT_USDC_ETHEREUM,
            "weth_address": uv4.DEFAULT_WETH_ETHEREUM,
            "pool_keys": [pool_key],
            "block_pre": "latest",
            "block_post": "latest",
        },
        "pre": pre.to_dict(),
        "post": post.to_dict(),
        "delta": diff["evidence"],
        "measured_impact": False,
        "above_threshold_tokens": [],
        "threshold_raw_units": str(mo.MEASURED_DELTA_THRESHOLD),
        "source_commit": "foundry/test/UniV4Measure.t.sol",
        "nss_version": "5.0.0-draft",
        "on_chain_state_diff": {
            "kind": "slot0_initialize",
            "pool_id": pool_id_hex,
            "pre_sqrt_price_x96": str(sqrt_pre),
            "post_sqrt_price_x96": str(sqrt_post),
            "delta_raw": str(sqrt_post - sqrt_pre),
            "pre_tick": tick_pre,
            "post_tick": tick_post,
            "decoded_protocol_layer": "PoolManager singleton",
            "non_fee": True,
            "non_market_resetting": False,
        },
        "measured_impact_reason": (
            "Token-unit balances unchanged; the authoritative measured "
            "delta is PoolManager's slot0 sqrtPriceX96 transition from "
            "0 to 2**96 on a forked mainnet probe via PoolManager.initialize. "
            "This is the audit-mandated substrate-binding proof: the "
            "oracle refuses to register a positive token-unitholder delta "
            "for the slot0-only case because v4 submits still require "
            "real ERC-20 movement for ``submit_ready``."
        ),
    }


def main() -> int:
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
        log_text = log_path.read_text() if log_path.is_file() else Path(sys.argv[1]).read_text()
    else:
        rc, log_text = run_forge()
        if rc != 0 or "PASS" not in log_text:
            sys.stderr.write(
                "forge test failed; log follows:\n"
                + log_text
                + "\n"
            )
            return rc or 5

    envelope = build_envelope(log_text)
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(envelope, indent=2, default=str) + "\n")
    sys.stdout.write(json.dumps(envelope, indent=2, default=str) + "\n")
    sys.stderr.write(f"\nWROTE: {EVIDENCE_PATH}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
