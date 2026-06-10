#!/usr/bin/env python3
"""Write hermes_proposals for Immunefi cross-target investigate (per-program templates)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS
from night_shift_security.domain.attack_hypotheses.base import AttackHypothesis, validate_hypothesis

REPO = Path(__file__).resolve().parents[2]

TEMPLATE_VARIANTS: dict[str, list[dict]] = {
    "flash_loan_oracle": [
        {
            "loan_fraction_of_ceiling": 0.75,
            "price_skew_severity": 1.2,
            "oracle_dependency_score": 0.88,
        },
        {
            "loan_fraction_of_ceiling": 0.2,
            "price_skew_severity": 0.7,
            "oracle_dependency_score": 0.72,
        },
    ],
    "composability_risk": [
        {
            "chain_depth": 0.88,
            "leverage_intensity": 0.75,
            "callback_chain_likelihood": 0.85,
        },
        {
            "chain_depth": 0.35,
            "leverage_intensity": 0.5,
            "callback_chain_likelihood": 0.6,
        },
    ],
    "reentrancy": [
        {
            "recursion_intensity": 0.8,
            "callback_exploitability": 0.85,
            "target_function_preference": "withdraw",
        },
    ],
    "governance_capture": [
        {
            "quorum_threshold": 0.12,
            "participation_rate": 0.35,
            "whale_concentration": 0.7,
            "proposal_timing_window_blocks": 200,
            "flash_loan_boost": 0.25,
        },
    ],
    "treasury_drain": [
        {
            "drain_fraction": 0.65,
            "admin_compromise_likelihood": 0.7,
            "multisig_weakness": 0.55,
            "withdrawal_velocity": 0.8,
        },
    ],
}


def _program(slug: str):
    for program in IMMUNEFI_PROGRAMS:
        if program.slug == slug:
            return program
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Write scan-target proposals JSON")
    parser.add_argument("--slug", required=True, help="Immunefi program slug (e.g. raydium)")
    args = parser.parse_args()

    program = _program(args.slug)
    if program is None:
        print(f"Unknown program slug: {args.slug}", file=sys.stderr)
        return 1

    proposals: list[dict] = []
    for template in program.templates:
        for parameters in TEMPLATE_VARIANTS.get(template, []):
            hypothesis = AttackHypothesis(
                hypothesis_id="probe",
                template=template,
                parameters=parameters,
                metadata={},
            )
            valid, reason = validate_hypothesis(hypothesis)
            if not valid:
                print(f"Skip {template}: {reason}", file=sys.stderr)
                continue
            proposals.append(
                {
                    "template": template,
                    "parameters": parameters,
                    "delegate_note": (
                        f"cross-target {program.slug} analogue {program.catalog_analogue}"
                    ),
                }
            )

    if not proposals:
        print("No valid proposals generated", file=sys.stderr)
        return 1

    run_id = f"{program.slug}-cross-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    doc = {
        "run_id": run_id,
        "campaign_id": f"immunefi-{program.slug}-cross",
        "target_slug": program.slug,
        "catalog_analogue": program.catalog_analogue,
        "proposals": proposals,
    }
    out_dir = REPO / "data/security_results/hermes_proposals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    latest = out_dir / "latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_path.name)
    print(json.dumps({"path": str(out_path), "slug": program.slug, "count": len(proposals)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())