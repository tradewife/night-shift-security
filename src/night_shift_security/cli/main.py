"""CLI entry point for Night Shift Security."""

import argparse
import json
import sys
from pathlib import Path

from night_shift_security.api.server import serve
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.export.dataset import export_dataset
from night_shift_security.export.disclosure import build_disclosure_report, update_disclosure_status
from night_shift_security.export.loader import findings_from_run_json


def _cmd_run(config: Path | None) -> int:
    result = run_security_pipeline(config_path=config)
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

    args = parser.parse_args()

    try:
        if args.command == "serve":
            sys.exit(_cmd_serve(args.host, args.port, args.dataset))
        if args.command == "export":
            sys.exit(_cmd_export(args.input, args.output_dir))
        if args.command == "disclose":
            sys.exit(_cmd_disclose(args.input, args.finding_id, args.status, args.report))
        sys.exit(_cmd_run(args.config))
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()