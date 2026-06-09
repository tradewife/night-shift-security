"""Load findings from a prior pipeline run JSON."""

import json
from pathlib import Path

from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity


def findings_from_run_json(path: Path) -> tuple[list[Finding], dict]:
    """Parse findings.json from a pipeline run."""
    with open(path) as f:
        payload = json.load(f)

    findings: list[Finding] = []
    for item in payload.get("findings", []):
        findings.append(
            Finding(
                finding_id=item["finding_id"],
                template_id=item["template_id"],
                target_id=item.get("target_id", ""),
                severity=Severity(item["severity"]),
                severity_score=float(item["severity_score"]),
                economic_impact_usd=float(item["economic_impact_usd"]),
                capital_required_usd=float(item.get("capital_required_usd", 0)),
                reproducibility=float(item.get("reproducibility", 0)),
                parameters=item.get("parameters", {}),
                invariant_violations=[
                    InvariantViolation(
                        invariant_id=v["invariant_id"],
                        description=v.get("description", ""),
                        expected=v.get("expected", ""),
                        actual=v.get("actual", ""),
                    )
                    for v in item.get("invariant_violations", [])
                ],
                reproduction_steps=[
                    ReproductionStep(
                        action=s["action"],
                        actor=s["actor"],
                        details=s.get("details", {}),
                    )
                    for s in item.get("reproduction_steps", [])
                ],
                mitigations=item.get("mitigations", []),
                confidence=float(item.get("confidence", 0)),
                rediscovered_exploit_id=item.get("rediscovered_exploit_id", "") or "",
                disclosure_status=item.get("disclosure_status", ""),
                hypothesis_id=item.get("hypothesis_id", "") or "",
                parent_ids=list(item.get("parent_ids", [])),
                lineage=list(item.get("lineage", [])),
                generation_method=item.get("generation_method", "") or "",
                priority_score=float(item.get("priority_score", 0.0)),
                novelty_score=float(item.get("novelty_score", 0.0)),
                reproduction_tier=item.get("reproduction_tier", "simulation"),
                deployed_viable=bool(item.get("deployed_viable", False)),
                catalog_analogue=bool(item.get("catalog_analogue", False)),
                submission_readiness=item.get("submission_readiness", "draft"),
                fork_reproduced=bool(item.get("fork_reproduced", False)),
                fork_block_number=int(item.get("fork_block_number", 0)),
                fork_evidence=dict(item.get("fork_evidence", {})),
                solana_confirmed=bool(item.get("solana_confirmed", False)),
                solana_reproduced=bool(item.get("solana_reproduced", False)),
                solana_slot=int(item.get("solana_slot", 0)),
                solana_evidence=dict(item.get("solana_evidence", {})),
                evidence_grade=int(item.get("evidence_grade", 0)),
                evidence_grade_label=item.get("evidence_grade_label", "none"),
            )
        )

    run_meta = {
        "run_at": payload.get("run_at"),
        "elapsed_seconds": payload.get("elapsed_seconds"),
        "candidates_evaluated": payload.get("candidates_evaluated", 0),
        "candidates_passed_gates": payload.get("candidates_passed_gates", 0),
        "rediscovery": payload.get("rediscovery", {}),
    }
    return findings, run_meta