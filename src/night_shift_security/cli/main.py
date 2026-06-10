"""CLI entry point for Night Shift Security."""

import argparse
import json
import sys
from pathlib import Path

from night_shift_security.api.server import serve
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.export.dataset import export_dataset
from night_shift_security.export.disclosure import build_disclosure_report, update_disclosure_status
from night_shift_security.bounty.pipeline import export_bounty_artifacts, export_bounty_pack
from night_shift_security.export.immunefi_submission import export_immunefi_packs
from night_shift_security.export.shoestring_submission import export_shoestring_pack
from night_shift_security.immunefi.investigate import (
    load_scan_report,
    pick_investigation_targets,
    run_investigation_queue,
)
from night_shift_security.immunefi.scan import run_immunefi_scan
from night_shift_security.data.immunefi_registry import list_programs, program_summary
from night_shift_security.export.deduper import dedupe_findings, log_dedupe_report
from night_shift_security.export.loader import findings_from_run_json
from night_shift_security.monitoring.hooks import emit_monitoring_event
from night_shift_security.eval.llm_quality import run_llm_quality_eval
from night_shift_security.knowledge.findings_store import (
    ancestors,
    best_evidence_per_lineage_root,
    campaign_stats,
    descendants,
    lineage_survival_stats,
    load_store,
)
from night_shift_security.orchestration.coordinator import (
    coordinator_status,
    default_state_path,
    ensure_pending_missions,
    init_state,
    load_state,
    plan_missions,
    run_mission_cycle,
    save_state,
)


def _cmd_run(config: Path | None, proposals: Path | None = None) -> int:
    result = run_security_pipeline(config_path=config, proposals_path=proposals)
    return 0 if result["findings"] > 0 or result["rediscovery"]["rediscovered"] > 0 else 1


def _cmd_serve(host: str, port: int, dataset: Path) -> int:
    serve(host=host, port=port, dataset_path=dataset)
    return 0


def _cmd_export(input_path: Path, output_dir: Path) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    paths = export_dataset(findings, run_meta, output_dir, candidates=None)
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


def _cmd_dedupe(input_path: Path, output_dir: Path, re_export: bool) -> int:
    from night_shift_security.core.results import _finding_to_dict

    findings, run_meta = findings_from_run_json(input_path)
    deduped, report = dedupe_findings(findings)
    print(f"Dedupe: {report.before_count} → {report.after_count} (dropped {report.dropped_count})")
    log_dedupe_report(report)

    out_path = input_path.parent / "findings.deduped.json"
    payload = json.loads(input_path.read_text())
    payload["findings_count_raw"] = report.before_count
    payload["findings_count"] = report.after_count
    payload["dedupe"] = report.to_dict()
    payload["findings"] = [_finding_to_dict(f) for f in deduped]
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote: {out_path}")

    if re_export:
        paths = export_dataset(deduped, run_meta, output_dir, dedupe=False)
        for name, path in paths.items():
            print(f"  {name}: {path}")
    return 0


def _cmd_bounty(input_path: Path, output_dir: Path, min_severity: str, with_immunefi: bool) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    if with_immunefi:
        result = export_bounty_artifacts(
            findings,
            run_meta,
            output_dir,
            {
                "min_severity": min_severity,
                "immunefi_packs": True,
                "min_evidence_grade": 3,
            },
        )
        print(f"  bounty_pack: {result.get('submissions_path')}")
        immunefi = result.get("immunefi", {})
        if immunefi:
            print(f"  immunefi_manifest: {immunefi.get('manifest_path')}")
            print(f"  immunefi_packs: {immunefi.get('pack_count', 0)}")
    else:
        path = export_bounty_pack(findings, run_meta, output_dir, min_severity=min_severity)
        print(f"  bounty_pack: {path}")
    return 0


def _cmd_scan(
    config: Path | None,
    ecosystem: str | None,
    min_bounty: int,
    limit: int | None,
    list_only: bool,
) -> int:
    if list_only:
        programs = list_programs(ecosystem=ecosystem, min_max_bounty_usd=min_bounty)
        if limit:
            programs = programs[:limit]
        print(json.dumps([program_summary(p) for p in programs], indent=2))
        return 0

    report = run_immunefi_scan(
        config_path=config,
        ecosystem=ecosystem,
        min_max_bounty_usd=min_bounty,
        limit=limit,
    )
    print(json.dumps(report["summary"], indent=2))
    print(f"  report_json: {report['paths']['json']}")
    print(f"  report_md: {report['paths']['markdown']}")
    return 0


def _cmd_investigate(
    config: Path | None,
    scan_path: Path,
    top_n: int,
    min_grade: int,
    ecosystem: str | None,
    proposals: Path | None,
    dry_run: bool,
) -> int:
    report = load_scan_report(scan_path)
    if dry_run:
        targets = pick_investigation_targets(
            report,
            top_n=top_n,
            min_evidence_grade=min_grade,
            ecosystem=ecosystem,
        )
        print(json.dumps({"targets": targets, "count": len(targets)}, indent=2))
        return 0

    result = run_investigation_queue(
        report,
        top_n=top_n,
        min_evidence_grade=min_grade,
        ecosystem=ecosystem,
        base_config_path=config,
        proposals_path=proposals,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("runs") else 1


def _cmd_submission(input_path: Path, output_dir: Path, min_evidence_grade: int) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    result = export_shoestring_pack(
        findings,
        {**run_meta, "shoestring_mode": True, "zero_rpc": True},
        output_dir,
        min_evidence_grade=min_evidence_grade,
    )
    if not result.get("selected_finding_id"):
        print(f"  no eligible finding: {result.get('reason', 'unknown')}", file=sys.stderr)
        return 1
    print(f"  selected: {result['selected_finding_id']} ({result['catalog_exploit_id']})")
    print(f"  pack_dir: {result['pack_dir']}")
    print(f"  manifest: {result['manifest_path']}")
    return 0


def _cmd_immunefi(input_path: Path, output_dir: Path, min_evidence_grade: int, min_severity: str) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    result = export_immunefi_packs(
        findings,
        run_meta,
        output_dir,
        min_evidence_grade=min_evidence_grade,
        min_severity=min_severity,
    )
    print(f"  immunefi_manifest: {result.get('manifest_path')}")
    print(f"  immunefi_packs: {result.get('pack_count', 0)}")
    return 0


def _cmd_monitor(input_path: Path, webhook: str, alert_file: Path | None) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    config = {
        "enabled": True,
        "min_severity": "high",
        "webhook_url": webhook,
        "alert_file": str(alert_file) if alert_file else "",
    }
    result = emit_monitoring_event(findings, run_meta, config)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_coordinator(
    action: str,
    config: Path | None,
    state_path: Path,
    store_path: Path,
    top_n: int,
    proposals: Path | None,
    campaign_id: str | None,
) -> int:
    if action == "init":
        if config is None:
            print("coordinator init requires --config", file=sys.stderr)
            return 1
        state = init_state(config, state_path=state_path)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if not state_path.is_file():
        print(f"Coordinator state not found: {state_path} (run coordinator init first)", file=sys.stderr)
        return 1

    state = load_state(state_path)
    store = load_store(store_path)

    if action == "status":
        state = ensure_pending_missions(state, store)
        save_state(state, state_path)
        print(json.dumps(coordinator_status(state, store), indent=2, default=str))
        return 0

    if action == "plan":
        state = ensure_pending_missions(state, store)
        save_state(state, state_path)
        missions = plan_missions(state, store, top_n=top_n)
        print(
            json.dumps(
                {
                    "campaign_id": state.campaign_id,
                    "missions": [m.to_dict() for m in missions],
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if action == "cycle":
        result = run_mission_cycle(
            state,
            proposals_path=proposals,
            state_path=state_path,
            store_path=store_path,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "completed" else 1

    print(f"Unknown coordinator action: {action}", file=sys.stderr)
    return 1


def _cmd_knowledge(
    store_path: Path,
    hypothesis_id: str | None,
    stats_only: bool,
    campaign_id: str | None,
) -> int:
    store = load_store(store_path)
    if campaign_id:
        print(json.dumps(campaign_stats(store, campaign_id), indent=2))
        return 0
    if stats_only or not hypothesis_id:
        print(json.dumps(lineage_survival_stats(store), indent=2))
        if not hypothesis_id:
            print(json.dumps(best_evidence_per_lineage_root(store), indent=2, default=str))
        return 0

    print(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "ancestors": ancestors(store, hypothesis_id),
                "descendants": descendants(store, hypothesis_id),
            },
            indent=2,
        )
    )
    return 0


def _cmd_disclose(input_path: Path, finding_id: str | None, status: str | None, report_only: bool) -> int:
    if report_only:
        findings, _ = findings_from_run_json(input_path)
        report = build_disclosure_report(findings)
        print(json.dumps(report, indent=2))
        return 0

    if not finding_id or not status:
        print("disclose requires --finding-id and --status (or --report)", file=__import__("sys").stderr)
        return 1

    result = update_disclosure_status(input_path, finding_id, status)
    print(f"Updated {result['finding_id']} → {result['disclosure_status']}")
    findings, run_meta = findings_from_run_json(input_path)
    export_dataset(findings, run_meta, input_path.parent.parent, candidates=None)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Night Shift Security — adversarial protocol vulnerability research"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config JSON (default: built-in config/default.json)",
    )
    parser.add_argument(
        "--proposals",
        type=Path,
        default=None,
        help="Hermes external proposals JSON (enables llm_expansion.provider=external)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the full security pipeline (default)")

    serve_parser = subparsers.add_parser("serve", help="Serve public findings API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/security_results/dataset/latest.json"),
        help="Path to exported latest.json feed",
    )

    export_parser = subparsers.add_parser("export", help="Export dataset from a prior run JSON")
    export_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to findings.json from a pipeline run",
    )
    export_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results"),
        help="Directory for dataset/ and bridge/ artifacts",
    )

    disclose_parser = subparsers.add_parser("disclose", help="Manage responsible disclosure status")
    disclose_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to findings.json from a pipeline run",
    )
    disclose_parser.add_argument("--finding-id", default=None, help="Finding ID to update")
    disclose_parser.add_argument(
        "--status",
        choices=["draft", "embargoed", "disclosed", "redacted"],
        default=None,
        help="New disclosure status",
    )
    disclose_parser.add_argument(
        "--report",
        action="store_true",
        help="Print disclosure summary report without mutating files",
    )

    bounty_parser = subparsers.add_parser("bounty", help="Export bug-bounty submission pack")
    bounty_parser.add_argument("--input", type=Path, required=True)
    bounty_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    bounty_parser.add_argument("--min-severity", default="high", choices=["low", "medium", "high", "critical"])
    bounty_parser.add_argument(
        "--immunefi",
        action="store_true",
        help="Also emit Immunefi-style markdown + reproduction script packs",
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan curated Immunefi programs with the engine (shoestring / zero-RPC)",
    )
    scan_parser.add_argument("--ecosystem", default=None, choices=["solana", "evm", "multichain", "stacks"])
    scan_parser.add_argument("--min-bounty", type=int, default=0, help="Min max bounty USD")
    scan_parser.add_argument("--limit", type=int, default=None, help="Max programs to scan")
    scan_parser.add_argument("--list", action="store_true", dest="list_only", help="List programs only")

    investigate_parser = subparsers.add_parser(
        "investigate",
        help="Deep-dive top Immunefi scan targets (full pipeline per program)",
    )
    investigate_parser.add_argument(
        "--scan",
        type=Path,
        default=Path("data/security_results/immunefi_scan/latest.json"),
        help="Scan report JSON (default: latest immunefi scan)",
    )
    investigate_parser.add_argument("--top", type=int, default=2, help="Max programs to investigate")
    investigate_parser.add_argument("--min-grade", type=int, default=2, help="Min scan evidence grade")
    investigate_parser.add_argument(
        "--ecosystem",
        default="solana",
        choices=["solana", "evm", "multichain", "stacks", "all"],
    )
    investigate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected targets without running pipeline",
    )

    submission_parser = subparsers.add_parser(
        "submission",
        help="Export single zero-RPC shoestring submission pack (best Level 4+ finding)",
    )
    submission_parser.add_argument("--input", type=Path, required=True)
    submission_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    submission_parser.add_argument("--min-evidence-grade", type=int, default=4)

    immunefi_parser = subparsers.add_parser("immunefi", help="Export Immunefi submission packs only")
    immunefi_parser.add_argument("--input", type=Path, required=True)
    immunefi_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    immunefi_parser.add_argument("--min-evidence-grade", type=int, default=3)
    immunefi_parser.add_argument(
        "--min-severity",
        default="high",
        choices=["low", "medium", "high", "critical"],
    )

    monitor_parser = subparsers.add_parser("monitor", help="Emit monitoring alerts from a prior run")
    monitor_parser.add_argument("--input", type=Path, required=True)
    monitor_parser.add_argument("--webhook", default="", help="Optional webhook URL (overrides NIGHT_SHIFT_WEBHOOK_URL)")
    monitor_parser.add_argument("--alert-file", type=Path, default=None)

    dedupe_parser = subparsers.add_parser("dedupe", help="Deduplicate findings from a prior run JSON")
    dedupe_parser.add_argument("--input", type=Path, required=True)
    dedupe_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    dedupe_parser.add_argument(
        "--re-export",
        action="store_true",
        help="Re-export dataset/ and bridge/ from deduped findings",
    )

    knowledge_parser = subparsers.add_parser("knowledge", help="Query findings store lineage analytics")
    knowledge_parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/findings_store.jsonl"),
        help="Path to findings_store.jsonl",
    )
    knowledge_parser.add_argument(
        "--hypothesis-id",
        default=None,
        help="Inspect lineage for a specific hypothesis ID",
    )
    knowledge_parser.add_argument(
        "--stats",
        action="store_true",
        help="Print aggregate lineage survival stats",
    )
    knowledge_parser.add_argument(
        "--campaign",
        default=None,
        help="Aggregate stats for a campaign_id across runs",
    )

    eval_parser = subparsers.add_parser(
        "eval",
        help="Run LLM hypothesis quality eval (zero-cost mock providers)",
    )
    eval_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results"),
    )

    coordinator_parser = subparsers.add_parser(
        "coordinator",
        help="Deterministic mission coordinator (Layer 6 orchestration)",
    )
    coordinator_parser.add_argument(
        "action",
        choices=["init", "status", "plan", "cycle"],
        help="init | status | plan | cycle",
    )
    coordinator_parser.add_argument(
        "--state",
        type=Path,
        default=default_state_path(),
        help="Path to coordinator_state.json",
    )
    coordinator_parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/findings_store.jsonl"),
        help="Path to findings_store.jsonl",
    )
    coordinator_parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Max missions for plan (default: 3)",
    )
    coordinator_parser.add_argument(
        "--campaign",
        default=None,
        help="Filter status by campaign_id (reserved)",
    )

    args = parser.parse_args()

    try:
        if args.command == "serve":
            sys.exit(_cmd_serve(args.host, args.port, args.dataset))
        if args.command == "export":
            sys.exit(_cmd_export(args.input, args.output_dir))
        if args.command == "disclose":
            sys.exit(_cmd_disclose(args.input, args.finding_id, args.status, args.report))
        if args.command == "bounty":
            sys.exit(_cmd_bounty(args.input, args.output_dir, args.min_severity, args.immunefi))
        if args.command == "scan":
            sys.exit(
                _cmd_scan(args.config, args.ecosystem, args.min_bounty, args.limit, args.list_only)
            )
        if args.command == "investigate":
            eco = None if args.ecosystem == "all" else args.ecosystem
            sys.exit(
                _cmd_investigate(
                    args.config,
                    args.scan,
                    args.top,
                    args.min_grade,
                    eco,
                    args.proposals,
                    args.dry_run,
                )
            )
        if args.command == "submission":
            sys.exit(_cmd_submission(args.input, args.output_dir, args.min_evidence_grade))
        if args.command == "immunefi":
            sys.exit(
                _cmd_immunefi(
                    args.input,
                    args.output_dir,
                    args.min_evidence_grade,
                    args.min_severity,
                )
            )
        if args.command == "monitor":
            sys.exit(_cmd_monitor(args.input, args.webhook, args.alert_file))
        if args.command == "dedupe":
            sys.exit(_cmd_dedupe(args.input, args.output_dir, args.re_export))
        if args.command == "knowledge":
            sys.exit(_cmd_knowledge(args.store, args.hypothesis_id, args.stats, args.campaign))
        if args.command == "eval":
            result = run_llm_quality_eval(output_dir=args.output_dir)
            print(json.dumps(result, indent=2))
            sys.exit(0)
        if args.command == "coordinator":
            sys.exit(
                _cmd_coordinator(
                    args.action,
                    args.config,
                    args.state,
                    args.store,
                    args.top,
                    args.proposals,
                    args.campaign,
                )
            )
        sys.exit(_cmd_run(args.config, args.proposals))
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()