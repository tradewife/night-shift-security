#!/usr/bin/env python3
"""Export Immunefi draft pack from a strict validator-backed catalog anchor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
from night_shift_security.core.gates import SecurityGate
from night_shift_security.core.results import findings_from_candidates
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import Finding
from night_shift_security.export.immunefi_submission import export_immunefi_packs
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.evidence_grading import (
    evidence_grade_label,
    shoestring_evidence_grade_candidate,
)
from night_shift_security.validation.solana_validation import run_solana_validation_phase


def _permissive_gates() -> SecurityGate:
    return SecurityGate(
        MIN_REPRODUCIBILITY=0.0,
        MIN_SEVERITY_SCORE=0.0,
        MIN_ECONOMIC_IMPACT_USD=0.0,
        MIN_INVARIANT_VIOLATIONS=0,
        MIN_REALISM_SCORE=0.0,
        MIN_GENERALITY=0.0,
    )


def _write_findings_json(
    findings: list[Finding],
    path: Path,
    *,
    exploit_id: str,
) -> None:
    from dataclasses import asdict

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": 0.0,
        "candidates_evaluated": 1,
        "candidates_passed_gates": 1,
        "findings_count": len(findings),
        "grant_demo_exploit_id": exploit_id,
        "reproduction_path": "solana_validator",
        "findings": [asdict(f) for f in findings],
    }
    for item in payload["findings"]:
        item["severity"] = item["severity"].value if hasattr(item["severity"], "value") else item["severity"]
        item["invariant_violations"] = [
            asdict(v) if hasattr(v, "__dataclass_fields__") else v for v in item.get("invariant_violations", [])
        ]
        item["reproduction_steps"] = [
            asdict(s) if hasattr(s, "__dataclass_fields__") else s for s in item.get("reproduction_steps", [])
        ]
    path.write_text(json.dumps(payload, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant-demo Immunefi pack from validator catalog anchor")
    parser.add_argument(
        "--exploit-id",
        default=os.environ.get("GRANT_DEMO_EXPLOIT_ID", "mango-markets-2022"),
        help="Catalog exploit_id (solend-whale-2022, cashio-2022, mango-markets-2022)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results"),
    )
    parser.add_argument("--skip-validator", action="store_true", help="Use existing solana evidence on seed only")
    args = parser.parse_args()

    if not args.skip_validator and os.environ.get("SOLANA_USE_VALIDATOR", "").lower() not in ("1", "true", "yes"):
        print("Set SOLANA_USE_VALIDATOR=1 and SOLANA_MAINNET_RPC_URL for strict validator export", file=sys.stderr)
        return 2

    catalog = get_exploit_catalog()
    seeds = evaluate_catalog_seeds(catalog, _permissive_gates())
    seed = next((s for s in seeds if s.catalog_exploit_id == args.exploit_id), None)
    if seed is None:
        print(f"No catalog seed for {args.exploit_id!r}", file=sys.stderr)
        return 1

    if not args.skip_validator:
        run_solana_validation_phase(
            [seed],
            catalog,
            {"top_n": 0, "always_test_catalog_solana_anchors": True},
        )

    if not seed.solana_reproduced:
        print(f"Strict reproduction failed for {args.exploit_id}", file=sys.stderr)
        print(f"  method={seed.solana_evidence.get('method')}", file=sys.stderr)
        return 1

    impact = float(seed.solana_evidence.get("impact_usd") or 0)
    if impact > 0:
        seed.mean_economic_impact_usd = impact
    seed.evidence_grade = shoestring_evidence_grade_candidate(seed)
    seed.evidence_grade_label = evidence_grade_label(seed.evidence_grade)
    seed.catalog_analogue = True
    seed.reproduction_tier = "solana_validator"

    rediscovery = {str(seed.vector.key()): args.exploit_id}
    findings = findings_from_candidates([seed], rediscovery)
    if not findings:
        print("No findings from candidate (missing successful attack result?)", file=sys.stderr)
        return 1

    run_dir = args.output_dir / "grant_demo" / args.exploit_id
    findings_path = run_dir / "findings.json"
    _write_findings_json(findings, findings_path, exploit_id=args.exploit_id)

    run_meta = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "grant_demo": True,
        "catalog_exploit_id": args.exploit_id,
        "reproduction_method": seed.solana_evidence.get("method"),
        "x402_proxy_note": "SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989 (dedicated wallet)",
    }
    result = export_immunefi_packs(
        findings,
        run_meta,
        args.output_dir,
        min_evidence_grade=3,
        min_severity="medium",
    )

    print(f"findings_json: {findings_path}")
    print(f"immunefi_manifest: {result.get('manifest_path')}")
    print(f"immunefi_packs: {result.get('pack_count', 0)}")
    for pack in result.get("packs", []):
        print(f"  pack: {pack.get('finding_id')} -> {pack.get('markdown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())