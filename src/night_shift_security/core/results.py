"""Result storage and report generation — mirrors RTP generate_report() pattern."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.schemas import AttackCandidateResult, Finding
from night_shift_security.export.dataset import export_dataset
from night_shift_security.export.disclosure import classify_severity_disclosure


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
                disclosure_status=classify_severity_disclosure(best.severity),
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
        "treasury_drain": [
            "Enforce multisig with hardware wallet signers",
            "Implement per-transaction withdrawal limits",
            "Add time-delayed withdrawals for large amounts",
            "Rotate admin keys and monitor role changes on-chain",
        ],
        "flash_loan_oracle": [
            "Use TWAP oracles with sufficient liquidity depth",
            "Implement multi-oracle median with deviation checks",
            "Add flash-loan detection guards on sensitive operations",
            "Cap borrow amounts relative to pool liquidity",
        ],
        "reentrancy": [
            "Apply checks-effects-interactions pattern",
            "Use OpenZeppelin ReentrancyGuard on all external calls",
            "Update state before token transfers",
            "Disable callbacks on ERC-777/ERC-1155 hooks where not needed",
        ],
        "composability_risk": [
            "Isolate collateral accounting across protocol integrations",
            "Cap borrow amounts relative to external pool liquidity",
            "Add reentrancy guards on cross-protocol callback entrypoints",
            "Monitor and limit composability hops in sensitive operations",
        ],
        "upgradeability_risk": [
            "Use ERC-7201 namespaced storage for upgradeable contracts",
            "Require timelocked governance for implementation upgrades",
            "Disable initializer after deployment; verify proxy initialization",
            "Audit storage layout between proxy and implementation versions",
        ],
        "access_control_escalation": [
            "Enforce OpenZeppelin AccessControl on all privileged functions",
            "Reject zero-address and zero-root initialization values",
            "Add role change monitoring and multisig for admin transfers",
            "Run Slither/mythril for missing onlyRole modifiers",
        ],
    }
    return mitigations.get(template_id, ["Review protocol invariants and add monitoring"])


def write_report(
    findings: list[Finding],
    candidates: list[AttackCandidateResult],
    output_dir: Path,
    run_seconds: float,
    rediscovery_stats: dict,
    monte_carlo: dict | None = None,
    foundry: dict | None = None,
    cpcv: dict | None = None,
    fork: dict | None = None,
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
        "monte_carlo_tested": len(monte_carlo or {}),
        "foundry_confirmed": sum(1 for v in (foundry or {}).values() if v),
        "cpcv_analyzed": len(cpcv or {}),
        "fork_confirmed": sum(1 for r in (fork or {}).values() if r.get("fork_confirmed")),
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
        "## Monte Carlo Stress",
        "",
        f"- Candidates tested: {len(monte_carlo or {})}",
        "",
        "## Foundry Validation",
        "",
        f"- Confirmed on-chain: {sum(1 for v in (foundry or {}).values() if v)}",
        "",
        "## CPCV / PBO Overfitting",
        "",
        f"- Candidates analyzed: {len(cpcv or {})}",
        "",
        "## Mainnet Fork Validation",
        "",
        f"- Fork confirmed: {sum(1 for r in (fork or {}).values() if r.get('fork_confirmed'))}",
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
    lines.append("| Label | Template | Severity | PBO | MC | Fork | Status |")
    lines.append("|-------|----------|----------|-----|-----|------|--------|")
    for c in candidates[:15]:
        status = "PASS" if not c.rejected else f"REJECT: {c.rejection_reason[:25]}"
        mc = f"{c.mc_reproducibility:.0%}" if c.mc_simulations else "—"
        pbo = f"{c.pbo:.0%}" if c.pbo else "—"
        fork_mark = "yes" if c.fork_confirmed else "—"
        lines.append(
            f"| {c.vector.label} | {c.vector.template_id} | {c.severity_score:.3f} "
            f"| {pbo} | {mc} | {fork_mark} | {status} |"
        )

    with open(md_path, "w") as f:
        f.write("\n".join(lines))

    run_meta = {
        "run_at": payload["run_at"],
        "elapsed_seconds": payload["elapsed_seconds"],
        "candidates_evaluated": payload["candidates_evaluated"],
        "candidates_passed_gates": payload["candidates_passed_gates"],
        "rediscovery": rediscovery_stats,
    }
    export_paths = export_dataset(findings, run_meta, output_dir, candidates)
    export_paths_run = export_dataset(findings, run_meta, run_dir, candidates)
    payload["export_paths"] = {k: str(v) for k, v in export_paths.items()}
    payload["export_paths_run"] = {k: str(v) for k, v in export_paths_run.items()}
    with open(json_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

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
        "mc_reproducibility": c.mc_reproducibility,
        "mc_impact_p50_usd": c.mc_impact_p50_usd,
        "mc_impact_p95_usd": c.mc_impact_p95_usd,
        "mc_simulations": c.mc_simulations,
        "foundry_confirmed": c.foundry_confirmed,
        "fork_confirmed": c.fork_confirmed,
        "fork_target_id": c.fork_target_id,
        "simulator_backend": c.simulator_backend,
        "pbo": c.pbo,
        "cpcv_verdict": c.cpcv_verdict,
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