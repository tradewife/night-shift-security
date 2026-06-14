"""Block C — score novel candidates and emit human gate before external submit."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.bounty.scoring import compute_bounty_score, resolve_program_for_finding
from night_shift_security.export.loader import findings_from_run_json
from night_shift_security.export.gates import resolve_export_track
from night_shift_security.validation.submission_gates import qualifies_for_submission
from night_shift_security.validation.task_verifier import (
    finding_balance_verified,
    finding_has_credible_reproduction,
)


def score_novel_findings(findings_path: Path) -> dict[str, Any]:
    """Score all findings; highlight non–catalogue-analogue candidates."""
    findings, run_meta = findings_from_run_json(findings_path)
    scored: list[dict[str, Any]] = []
    novel: list[dict[str, Any]] = []
    submit_ready: list[dict[str, Any]] = []

    for finding in findings:
        program = resolve_program_for_finding(finding)
        score = compute_bounty_score(finding, program)
        balance_ok = finding_balance_verified(finding)
        entry = {
            "finding_id": finding.finding_id,
            "target_id": finding.target_id,
            "template_id": finding.template_id,
            "catalog_analogue": finding.catalog_analogue,
            "deployed_viable": finding.deployed_viable,
            "reproduction_tier": finding.reproduction_tier
            or ("fork_reproduced" if finding.fork_reproduced else "simulation"),
            "evidence_grade": finding.evidence_grade,
            "submission_recommendation": score.submission_recommendation,
            "bounty_readiness": round(score.bounty_readiness, 4),
            "expected_payout_proxy_usd": round(score.expected_payout_proxy_usd, 2),
            "balance_verified": balance_ok,
            "qualifies_for_loop_stop": qualifies_for_submission(finding, score),
            "human_gate": _human_gate_status(finding, score, balance_ok),
            "export_track": resolve_export_track(finding),
        }
        scored.append(entry)
        if not finding.catalog_analogue:
            novel.append(entry)
        if entry["qualifies_for_loop_stop"]:
            submit_ready.append(entry)

    scored.sort(key=lambda x: x.get("bounty_readiness", 0), reverse=True)
    novel.sort(key=lambda x: x.get("bounty_readiness", 0), reverse=True)

    return {
        "findings_path": str(findings_path),
        "campaign_id": run_meta.get("campaign_id"),
        "run_at": run_meta.get("run_at"),
        "total": len(scored),
        "novel_count": len(novel),
        "submit_ready_count": len(submit_ready),
        "scored": scored,
        "novel_candidates": novel,
        "submit_ready": submit_ready,
        "best_novel_recommendation": novel[0]["submission_recommendation"] if novel else "hold",
    }


def _human_gate_status(finding, score, balance_ok: bool) -> str:
    if finding.catalog_analogue:
        return "hold_catalogue_analogue"
    if score.submission_recommendation == "submit_now" and not finding_has_credible_reproduction(finding):
        return "hold_synthetic_harness"
    if score.submission_recommendation == "submit_now" and not balance_ok:
        return "hold_pending_balance_verifier"
    if score.submission_recommendation == "submit_now":
        return "approve_for_external_submit"
    if score.submission_recommendation in ("polish_validator", "shoestring_only"):
        return "review_polish"
    return "hold"


def score_novel_batch(findings_paths: list[Path]) -> dict[str, Any]:
    runs = [score_novel_findings(p) for p in findings_paths if p.is_file()]
    all_novel: list[dict[str, Any]] = []
    all_submit: list[dict[str, Any]] = []
    for run in runs:
        for entry in run.get("novel_candidates", []):
            entry = {**entry, "source_findings": run["findings_path"]}
            all_novel.append(entry)
        for entry in run.get("submit_ready", []):
            entry = {**entry, "source_findings": run["findings_path"]}
            all_submit.append(entry)

    all_novel.sort(key=lambda x: x.get("bounty_readiness", 0), reverse=True)
    all_submit.sort(key=lambda x: x.get("bounty_readiness", 0), reverse=True)

    return {
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "runs": runs,
        "novel_candidates": all_novel,
        "submit_ready": all_submit,
        "human_gate_pending": bool(all_submit),
        "kate_action": (
            "review submission_alert.json candidates — external post requires explicit approval"
            if all_submit
            else "no submit_now novel candidates — continue hunt"
        ),
    }


def write_human_gate_report(batch: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "block": "C",
        "human_gate_pending": batch.get("human_gate_pending", False),
        "kate_action": batch.get("kate_action", ""),
        "scored_at": batch.get("scored_at"),
        "novel_candidates": batch.get("novel_candidates", []),
        "submit_ready": batch.get("submit_ready", []),
        "runs_summary": [
            {
                "findings_path": r["findings_path"],
                "campaign_id": r.get("campaign_id"),
                "novel_count": r.get("novel_count"),
                "submit_ready_count": r.get("submit_ready_count"),
                "best_novel_recommendation": r.get("best_novel_recommendation"),
            }
            for r in batch.get("runs", [])
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return output_path