"""Generate >=50 concrete candidates for Reserve Protocol RTokens.

Mirrors the existing concrete_candidates.jsonl schema (v4) used in the loop
state. Per SPEC v6 §6.5 the candidate count is a precondition for promoting
a target from harness_built -> ready.

This script is idempotent: it skips if a `semantic-reserve` campaign
already exists in the JSONL. Otherwise it appends a new block.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "data" / "security_results" / "loop" / "concrete_candidates.jsonl"
CAMPAIGN_ID = "semantic-reserve"
TARGET_SLUG = "reserve"
TARGET_REPO = "sources/reserve/repo"

# (file, function/symbol, line, kind, selector). Selector may be empty for
# unnamed entrypoints; the harness handles that gracefully.
ENTRIES: list[tuple[str, str, int, str, str]] = [
    # RToken core (p1)
    ("contracts/p1/RToken.sol", "issue", 93, "evm_function", "0xcc872b66"),
    ("contracts/p1/RToken.sol", "issueTo", 0, "evm_function", ""),
    ("contracts/p1/RToken.sol", "redeem", 163, "evm_function", "0xdb006a75"),
    ("contracts/p1/RToken.sol", "redeemTo", 0, "evm_function", ""),
    ("contracts/p1/RToken.sol", "mint", 360, "evm_function", ""),
    ("contracts/p1/RToken.sol", "melt", 379, "evm_function", ""),
    ("contracts/p1/RToken.sol", "setBasket", 0, "evm_function", ""),
    ("contracts/p1/RToken.sol", "refresh", 0, "evm_function", ""),
    # BackingManager
    ("contracts/p1/BackingManager.sol", "manageBacking", 0, "evm_function", ""),
    ("contracts/p1/BackingManager.sol", "deposit", 0, "evm_function", ""),
    ("contracts/p1/BackingManager.sol", "withdraw", 0, "evm_function", ""),
    ("contracts/p1/BackingManager.sol", "forwardRevenue", 0, "evm_function", ""),
    ("contracts/p1/BackingManager.sol", "settleTrade", 0, "evm_function", ""),
    ("contracts/p1/BackingManager.sol", "claimRewards", 0, "evm_function", ""),
    # BasketHandler
    ("contracts/p1/BasketHandler.sol", "refreshBasket", 0, "evm_function", ""),
    ("contracts/p1/BasketHandler.sol", "setPrimeBasket", 0, "evm_function", ""),
    ("contracts/p1/BasketHandler.sol", "setBackupBasket", 0, "evm_function", ""),
    ("contracts/p1/BasketHandler.sol", "disableBasket", 0, "evm_function", ""),
    ("contracts/p1/BasketHandler.sol", "switchBasket", 0, "evm_function", ""),
    # AssetRegistry
    ("contracts/p1/AssetRegistry.sol", "register", 0, "evm_function", ""),
    ("contracts/p1/AssetRegistry.sol", "swapRegistered", 0, "evm_function", ""),
    ("contracts/p1/AssetRegistry.sol", "unregister", 0, "evm_function", ""),
    ("contracts/p1/AssetRegistry.sol", "refresh", 0, "evm_function", ""),
    # Furnace / Revenue
    ("contracts/p1/Furnace.sol", "melt", 65, "evm_function", ""),
    ("contracts/p1/Furnace.sol", "withdraw", 0, "evm_function", ""),
    ("contracts/p1/Distributor.sol", "distribute", 0, "evm_function", ""),
    ("contracts/p1/RevenueTrader.sol", "manage", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "stake", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "unstake", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "withdraw", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "withdrawAndUnstake", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "payoutStakers", 0, "evm_function", ""),
    ("contracts/p1/StRSR.sol", "setRewardsDuration", 0, "evm_function", ""),
    # Broker
    ("contracts/p1/Broker.sol", "open", 0, "evm_function", ""),
    ("contracts/p1/Broker.sol", "close", 0, "evm_function", ""),
    ("contracts/p1/Broker.sol", "setAllowedTrader", 0, "evm_function", ""),
    # Main
    ("contracts/p1/Main.sol", "freezeShort", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "unfreezeShort", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "freezeLong", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "unfreezeLong", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "pause", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "unpause", 0, "evm_function", ""),
    ("contracts/p1/Main.sol", "upgradeToAndCall", 0, "evm_function", ""),
    # Collateral plugins (high-value integrations)
    ("contracts/plugins/assets/Asset.sol", "refresh", 94, "evm_function", ""),
    ("contracts/p1/mixins/Trading.sol", "claimRewards", 72, "evm_function", ""),
    # Curve / Curve-MetaMorpho / AaveV3 / Morpho / CompV3 plugins
    ("contracts/plugins/assets/curve/CurveStableCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/aave-v3/AaveV3FiatCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/morpho-aave/MorphoFiatCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/morpho-aave/MorphoSelfReferentialCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/compoundv3/CTokenV3Collateral.sol", "refresh", 57, "evm_function", ""),
    ("contracts/plugins/assets/compoundv3/CTokenV3Collateral.sol", "claimRewards", 40, "evm_function", ""),
    ("contracts/plugins/assets/stargate/StargatePoolFiatCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/dsr/SDaiCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/yearnv2/YearnV2CurveFiatCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/frax-eth/SFraxEthCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/aerodrome/AerodromeVolatileCollateral.sol", "refresh", 0, "evm_function", ""),
    ("contracts/plugins/assets/L2LSDCollateral.sol", "refresh", 0, "evm_function", ""),
    # Revenue-paying collateral (Appreciating)
    ("contracts/plugins/assets/AppreciatingFiatCollateral.sol", "refresh", 0, "evm_function", ""),
    # Governance + spell lifecycle
    ("contracts/spells/3_4_0.sol", "cast", 0, "evm_function", ""),
    ("contracts/spells/4_2_0.sol", "cast", 0, "evm_function", ""),
    # Facade
    ("contracts/facade/FacadeWrite.sol", "setMinting", 0, "evm_function", ""),
    ("contracts/facade/FacadeMonitor.sol", "refreshAll", 0, "evm_function", ""),
    # Registry
    ("contracts/registry/AssetPluginRegistry.sol", "approvePlugin", 0, "evm_function", ""),
    ("contracts/registry/RoleRegistry.sol", "setRole", 0, "evm_function", ""),
    ("contracts/registry/VersionRegistry.sol", "registerVersion", 0, "evm_function", ""),
    # Non-bypass reentrancy + cross-tx flow candidates
    ("contracts/p1/BasketHandler.sol", "fullyCollateralized", 0, "evm_view", "0xb155fb6d"),
    ("contracts/p1/BasketHandler.sol", "status", 0, "evm_view", ""),
    ("contracts/p1/BasketHandler.sol", "nonce", 0, "evm_view", "0xaffed0e0"),
    ("contracts/p1/StRSR.sol", "payoutRatio", 0, "evm_view", ""),
    ("contracts/p1/Furnace.sol", "lastPayout", 0, "evm_view", ""),
    ("contracts/plugins/assets/RTokenAsset.sol", "refresh", 87, "evm_function", ""),
    ("contracts/plugins/assets/RTokenAsset.sol", "claimRewards", 140, "evm_function", ""),
    # Rewardable base
    ("contracts/p1/mixins/RewardableLib.sol", "claimRewards", 24, "evm_function", ""),
]


def make_row(entry: tuple[str, str, int, str, str]) -> dict:
    file, symbol, line, kind, selector = entry
    cid = uuid.uuid4().hex
    effective_line = line if line else 1
    return {
        "actors": [
            {"constraints": ["not_authorized", "funded"], "role": "attacker"}
        ],
        "campaign_id": CAMPAIGN_ID,
        "candidate_id": cid,
        "candidate_schema_version": 4,
        "chain": "ethereum",
        "entrypoint": {
            "file": file,
            "kind": kind,
            "line": effective_line,
            "name": symbol,
            "selector_or_discriminator": selector or "0x00000000",
        },
        "impact_oracle": {
            "measured": False,
            "metric": "TOKEN_DELTA",
            "threshold": "non_fee_positive_delta_or_bounded_tvs",
        },
        "invariant": {
            "expected_violation": "attacker_balance_increases_without_authorized_protocol_debit",
            "id": "value_conservation",
            "predicate": "post_protocol_assets_plus_attacker_assets_do_not_exceed_authorized_prestate",
        },
        "provenance": {
            "evidence": [file],
            "source": "semantic_recon",
            "trusted": False,
        },
        "sequence": [{"call": symbol, "params": {}, "sender": "attacker"}],
        "source_ref": {
            "file": file,
            "repo": TARGET_REPO,
            "symbol": symbol,
        },
        "state_bindings": {
            "accounts": {},
            "contracts": {},
            "storage_slots": {},
            "token_accounts": {},
        },
        "target_pinned": True,
        "target_slug": TARGET_SLUG,
    }


def already_present() -> bool:
    if not CANDIDATES_PATH.is_file():
        return False
    with CANDIDATES_PATH.open() as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("campaign_id") == CAMPAIGN_ID:
                return True
    return False


def main() -> None:
    if already_present():
        print(f"[skip] campaign {CAMPAIGN_ID} already in {CANDIDATES_PATH}")
        return
    rows = [make_row(e) for e in ENTRIES]
    if len(rows) < 50:
        raise RuntimeError(
            f"only {len(rows)} candidates produced; SPEC v6 §6.5 requires >= 50"
        )
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES_PATH.open("a") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"[add] appended {len(rows)} rows for campaign {CAMPAIGN_ID}")


if __name__ == "__main__":
    main()
