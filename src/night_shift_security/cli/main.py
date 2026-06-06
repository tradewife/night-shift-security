"""CLI entry point for Night Shift Security."""

import argparse
import sys
from pathlib import Path

from night_shift_security.api.server import serve
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.export.dataset import export_dataset
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

    args = parser.parse_args()

    try:
        if args.command == "serve":
            sys.exit(_cmd_serve(args.host, args.port, args.dataset))
        if args.command == "export":
            sys.exit(_cmd_export(args.input, args.output_dir))
        sys.exit(_cmd_run(args.config))
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()