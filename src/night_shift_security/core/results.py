"""Result storage and report generation — mirrors RTP generate_report() pattern."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, Finding


def findings_from_candidates(
    candidates: list[AttackCandidateResult],
    rediscovery_map: dict[str, str] | None = None,
) -> list[Finding]:
    """Convert gate-passing candidates into reportable findings."""
    findings: list[Finding] = []
    rediscovery_map = rediscovery_map or {}

    for i, cand in enumerate(candidates):
        if cand.rejected:
            continue
        best = next((r for r in cand.results if r.success), None)
        if not best:
            continue

        vector_key = str(cand.vector.key())
        findings.append(
            Finding(
                finding_id=f"NSS-{i+1:04d}",
                template_id=cand.vector.template_id,
                target_id=cand.vector.target_id,
                severity=best.severity,
                severity_score=cand.severity_score,
                economic_impact_usd=cand.mean_economic_impact_usd,
                capital_required_usd=best.capital_required_usd,
                reproducibility=cand.reproducibility,
                parameters=cand.vector.parameters,
                invariant_violations=best.invariant_violations,
                reproduction_steps=best.reproduction_steps,
                mitigations=_suggest_mitigations(cand.vector.template_id),
                confidence=min(cand.reproducibility * cand.realism_score, 1.0),
                rediscovered_exploit_id=rediscovery_map.get(vector_key, ""),
            )
        )

    return findings


def _suggest_mitigations(template_id: str) -> list[str]:
    mitigations = {
        "governance_capture": [
            "Raise proposal threshold above largest concentrated holder",
            "Add timelock with community review window",
            "Implement vote delegation caps",
            "Require multisig for treasury transfers above threshold",
        ],
    }
    return mitigations.get(template_id, ["Review protocol invariants and add monitoring"])


def write_report(
    findings: list[Finding],
    candidates: list[AttackCandidateResult],
    output_dir: Path,
    run_seconds: float,
    rediscovery_stats: dict,
) -> tuple[Path, Path]:
    """Write markdown report and JSON results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    run_dir = output_dir / date_str
    run_dir.mkdir(parents=True, exist_ok=True)

    json_path = run_dir / "findings.json"
    md_path = run_dir / "report.md"

    payload = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(run_seconds, 1),
        "candidates_evaluated": len(candidates),
        "candidates_passed_gates": sum(1 for c in candidates if not c.rejected),
        "findings_count": len(findings),
        "rediscovery": rediscovery_stats,
        "findings": [_finding_to_dict(f) for f in findings],
        "top_candidates": [_candidate_to_dict(c) for c in candidates[:20]],
    }

    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    lines = [
        "# Night Shift Security — Run Report",
        "",
        f"**Run at:** {payload['run_at']}",
        f"**Duration:** {run_seconds:.0f}s",
        f"**Candidates evaluated:** {len(candidates)}",
        f"**Passed gates:** {payload['candidates_passed_gates']}",
        f"**Findings:** {len(findings)}",
        "",
        "## Rediscovery Test",
        "",
        f"- Known exploits in catalog: {rediscovery_stats.get('catalog_size', 0)}",
        f"- Rediscovered: {rediscovery_stats.get('rediscovered', 0)}",
        f"- Rediscovery rate: {rediscovery_stats.get('rate', 0):.0%}",
        "",
    ]

    if findings:
        lines.append("## Findings")
        lines.append("")
        for f in findings:
            lines.extend(_finding_markdown(f))
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("No findings passed all security gates this run.")
        lines.append("")

    lines.append("## Top Candidates (including rejected)")
    lines.append("")
    lines.append("| Label | Template | Severity Score | Success Rate | Status |")
    lines.append("|-------|----------|----------------|--------------|--------|")
    for c in candidates[:15]:
        status = "PASS" if not c.rejected else f"REJECT: {c.rejection_reason[:40]}"
        lines.append(
            f"| {c.vector.label} | {c.vector.template_id} | {c.severity_score:.3f} "
            f"| {c.success_rate:.0%} | {status} |"
        )

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    return md_path, json_path


def _finding_to_dict(f: Finding) -> dict:
    d = asdict(f)
    d["severity"] = f.severity.value
    return d


def _candidate_to_dict(c: AttackCandidateResult) -> dict:
    return {
        "label": c.vector.label,
        "template_id": c.vector.template_id,
        "parameters": c.vector.parameters,
        "severity_score": c.severity_score,
        "success_rate": c.success_rate,
        "rejected": c.rejected,
        "rejection_reason": c.rejection_reason,
        "replay_matches": c.replay_matches,
        "replay_total": c.replay_total,
    }


def _finding_markdown(f: Finding) -> list[str]:
    lines = [
        f"### {f.finding_id}: {f.template_id} on {f.target_id or 'generic'}",
        "",
        f"- **Severity:** {f.severity.value.upper()} (score: {f.severity_score:.3f})",
        f"- **Economic impact:** ${f.economic_impact_usd:,.0f}",
        f"- **Capital required:** ${f.capital_required_usd:,.0f}",
        f"- **Reproducibility:** {f.reproducibility:.0%}",
        f"- **Confidence:** {f.confidence:.0%}",
    ]
    if f.rediscovered_exploit_id:
        lines.append(f"- **Rediscovered exploit:** {f.rediscovered_exploit_id}")
    lines.append("")
    lines.append("**Parameters:**")
    for k, v in f.parameters.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    if f.invariant_violations:
        lines.append("**Invariant violations:**")
        for v in f.invariant_violations:
            lines.append(f"- `{v.invariant_id}`: expected {v.expected}, got {v.actual}")
        lines.append("")
    if f.reproduction_steps:
        lines.append("**Reproduction steps:**")
        for i, step in enumerate(f.reproduction_steps, 1):
            lines.append(f"{i}. [{step.actor}] {step.action}")
        lines.append("")
    if f.mitigations:
        lines.append("**Suggested mitigations:**")
        for m in f.mitigations:
            lines.append(f"- {m}")
        lines.append("")
    return lines