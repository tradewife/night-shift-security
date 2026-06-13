#!/usr/bin/env python3
"""Write Hermes proposals scoped to Wormhole triage-ranked files (score ≥5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from night_shift_security.triage.wormhole_proposals import write_wormhole_triage_proposals  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Wormhole triage-scoped proposals")
    parser.add_argument(
        "--triage",
        type=Path,
        default=REPO / "data/security_results/triage/wormhole_files.json",
    )
    parser.add_argument("--min-score", type=int, default=5)
    parser.add_argument("--max-files", type=int, default=8)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO / "data/security_results/hermes_proposals",
    )
    args = parser.parse_args()

    if not args.triage.is_file():
        print(f"Triage file missing: {args.triage}", file=sys.stderr)
        print("Run: triage files --repo sources/wormhole/repo --slug wormhole", file=sys.stderr)
        return 1

    out_path = write_wormhole_triage_proposals(
        args.triage,
        args.output_dir,
        min_score=args.min_score,
        max_files=args.max_files,
    )
    doc = json.loads(out_path.read_text())
    print(
        json.dumps(
            {
                "path": str(out_path),
                "count": len(doc.get("proposals", [])),
                "triage_source": doc.get("triage_source"),
            },
            indent=2,
        )
    )
    return 0 if doc.get("proposals") else 1


if __name__ == "__main__":
    raise SystemExit(main())