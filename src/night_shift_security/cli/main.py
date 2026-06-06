"""CLI entry point for Night Shift Security."""

import argparse
import sys
from pathlib import Path

from night_shift_security.core.pipeline import run_security_pipeline


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
    args = parser.parse_args()

    try:
        result = run_security_pipeline(config_path=args.config)
        sys.exit(0 if result["findings"] > 0 or result["rediscovery"]["rediscovered"] > 0 else 1)
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()