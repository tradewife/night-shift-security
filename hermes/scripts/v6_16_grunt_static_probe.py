"""3F Grunt v6.16 static probe — NSS-style invariant extraction.

Mirrors the OnRe static-probe pattern (hermes/scripts/v6_13_onre_static_probe.py).

The probe is read-only:
- Loads the in-scope Solidity inventory via the NativeHarness.
- Confirms the role constants, EIP-712 typehashes, virtual-share offset formula,
  pre-liquidation health-check, and other in-scope invariants still appear in
  the current main branch.
- Writes a single JSON envelope under
  ``data/security_results/investigations/<date>-v6-16-3f-grunt-static-probe/``
  plus a printable summary.

It is intentionally not an executable test harness: the goal here is a
hypothesis ledger for the actual executable Foundry/substrate work that the
production cron will pick up.
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from night_shift_security.native.grunt import (
    EIP712_TYPEHASHES,
    FACILITY_ROLES,
    HARNESS_AUDIT_COMMITS,
    HARNESS_BOUNTY_URL,
    HARNESS_EXCLUDED_FILES,
    HARNESS_NAME,
    HARNESS_PLATFORM,
    load_inventory,
    scope_notes,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO = ROOT / "sources" / "3f-grunt" / "repo"


def _invariant_status(inventory: dict) -> dict[str, bool]:
    checks = inventory.get("checks", {})
    return {
        "facility_roles_present": bool(checks.get("facility_role_constants")),
        "check_signatures_implemented": bool(checks.get("_checkSignatures_present")),
        "request_min_max_balance_enforced": bool(checks.get("setRepaid_minMax_present")),
        "request_auto_repaid_deadline_sync": bool(checks.get("syncWithdrawalStatus_present")),
        "virtual_share_offset_formula": bool(checks.get("virtual_share_offset_formula_present")),
        "burn_includes_virtual_offset": bool(checks.get("burn_virtual_offset_in_denominator")),
        "morpho_preliquidate_two_paths": bool(checks.get("preLiquidate_two_paths")),
        "morpho_uses_expected_balances": bool(checks.get("expectedMarketBalances_used")),
        "transfer_guard_address_status": bool(checks.get("transfer_guard_currency")),
    }


def _hypothesis_ledger() -> list[dict]:
    return [
        {
            "id": "H1-prime",
            "summary": "PositionManager share-inflation via external Morpho collateral donation while production-bootstrap is in place.",
            "kill_criteria": [
                "Requires an actual production-bootstrap path to be bypassed.",
                "Bypasses accepted operational mitigation: pausing modules, quarantine, abandonment.",
                "Measured profit must exceed accepted 18-decimal and fresh-PM limits.",
            ],
            "in_scope": True,
            "evidence": "Static-only so far; needs Foundry reproduction against seeded manager.",
        },
        {
            "id": "H3-prime",
            "summary": "Request pull/repay path that exceeds accepted Facilitator/Consumer trust and bypasses minBalance/maxBalance or mint-to-repaid delay.",
            "kill_criteria": [
                "Consumer must exceed onlyOwnerOrRoles(_ROLE_CONSUMER) or misuse SlippageExceeded.",
                "Need independent violation of intended minimum / maximum balance or guardian checks.",
            ],
            "in_scope": True,
            "evidence": "setRepaid applies minBalance + maxBalance + mint-to-repaid delay; pullFunds is _ROLE_PULLER gated.",
        },
        {
            "id": "H4-prime",
            "summary": "Rounding or proportional-distribution edge cases that leave per-position LTV above intended safe LTV.",
            "kill_criteria": [
                "Must produce measurable undercollateralization after the operation.",
                "Must not rely solely on already-detectable bad debt or curated queueing.",
            ],
            "in_scope": True,
            "evidence": "PositionManagerLP.burn mixes virtualShareOffset in denominator; _withdrawProportional uses Bresenham-style running cumulative.",
        },
        {
            "id": "H5-prime",
            "summary": "Async fund state machine path where a non-operator user can force permanent loss/liveness impact.",
            "kill_criteria": [
                "Caller cannot be relied upon to operate via required roles or external systems.",
                "Must not rely on async settlement delays, partial fills, or stale prices.",
            ],
            "in_scope": True,
            "evidence": "State machine ACCEPTED -> PENDING -> PROCESSING -> UNLOCKING -> ENDED plus RECOVERING escape hatch is _OPERATOR_ROLE gated.",
        },
        {
            "id": "H6-prime",
            "summary": "Guardian signature replay/domain/intent-binding failures using honest (not malicious/stale) guardian signatures.",
            "kill_criteria": [
                "Signatures are intentionally trusted; report must show signature bypass with fresh guardian key + valid signature.",
                "Must demonstrate economic loss exceeding accepted SC-wallet replay mitigation documentation.",
            ],
            "in_scope": False,
            "evidence": "SWAP_PARAMS_TYPEHASH lacks signer binding but program doc explicitly says SC-wallet binding responsibility is non-bounty.",
        },
        {
            "id": "H7-prime",
            "summary": "Beacon owner / proxy upgrade path with concrete storage collision or role escalation.",
            "kill_criteria": [
                "Must not rely solely on admin mistakes or compromised owner keys.",
            ],
            "in_scope": "conditional",
            "evidence": "All upgrades are trusted-role gated; would need storage layout proof.",
        },
        {
            "id": "H8-prime",
            "summary": "Reentrancy / callback abuse in pullFunds, repay, or onMorphoRepay paths.",
            "kill_criteria": [
                "Must be performed by a non-Facilitator/MINTER_ROLE liquidator to match Program assumptions.",
                "Reverts must escape ReentrancyGuardTransient / nonReadReentrant protections.",
            ],
            "in_scope": "conditional",
            "evidence": "Both onMorphoRepay and preLiquidate are intentionally nonReentrant-unprotected for liquidators; program disclaims this when callback-capable address owns roles.",
        },
    ]


def main(repo: str | None = None) -> int:
    repo_path = Path(repo) if repo else DEFAULT_REPO
    if not repo_path.is_dir():
        raise SystemExit(f"3F Grunt repo not found at {repo_path}")

    inventory = load_inventory(repo_path)
    invariants = _invariant_status(inventory)
    ledger = _hypothesis_ledger()

    envelope = {
        "schema_version": "v6.16-3f-grunt-static-probe.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "generated_on": date.today().isoformat(),
        "target": "3f-grunt",
        "harness": {
            "name": HARNESS_NAME,
            "platform": HARNESS_PLATFORM,
            "bounty_url": HARNESS_BOUNTY_URL,
            "audit_commits": HARNESS_AUDIT_COMMITS,
            "excluded_files": list(HARNESS_EXCLUDED_FILES),
            "scope_notes": scope_notes(),
        },
        "inventory": {
            "total_files": inventory["total_files"],
            "in_scope_count": len(inventory["in_scope_files"]),
            "out_of_scope_count": len(inventory["out_of_scope_files"]),
            "out_of_scope_files": inventory["out_of_scope_files"],
        },
        "invariants": invariants,
        "eip712_typehashes": EIP712_TYPEHASHES,
        "role_groups": {
            "facility": FACILITY_ROLES,
        },
        "hypothesis_ledger": ledger,
        "submit_ready": False,
        "honest_zero": not all(invariants.values()) or len(ledger) > 0 and all(
            h["in_scope"] in (False, "conditional") for h in ledger[:6]
        ),
    }

    out_dir = ROOT / "data" / "security_results" / "investigations" / f"{date.today().isoformat()}-v6-16-3f-grunt-static-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "grunt_static_probe.json"
    out_path.write_text(json.dumps(envelope, indent=2) + "\n")

    print(json.dumps(envelope, indent=2))
    print(f"--- wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
