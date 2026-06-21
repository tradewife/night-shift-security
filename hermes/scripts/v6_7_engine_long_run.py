"""v6.7 proper-mode fuzz run — runs the actual libfuzzer in fuzz mode for a
bounded wall-clock budget (vs the JSONL corpus-replay orchestrator).

Output: ``fuzz_long_run.json``
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FUZZ_DIR = ROOT / "sources/marginfi/repo/programs/marginfi/fuzz"
BINARY_LEND = FUZZ_DIR / "target" / "release" / "lend"
BINARY_LEND_EXT = FUZZ_DIR / "target" / "release" / "lend_extended"
OUT_DIR = ROOT / "data" / "security_results" / "investigations" / "2026-06-21-v6-7-engine"


def run_fuzz(
    binary: Path,
    *,
    seconds: int = 90,
    label: str,
) -> dict:
    env = os.environ.copy()
    env["RUST_BACKTRACE"] = "0"
    started = time.time()
    cmd = [
        str(binary),
        "-max_total_time={}".format(seconds),
        "-timeout_exitcode=100",
        "-error_exitcode=101",
        "-print_final_stats=1",
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(FUZZ_DIR),
        capture_output=True,
        timeout=seconds + 30,
        env=env,
    )
    elapsed_ms = int((time.time() - started) * 1000)
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    cov_lines = [l for l in stdout.splitlines() if "cov:" in l]
    return {
        "schema_version": "v6.7-fuzz-long-run.v1",
        "label": label,
        "binary": binary.name,
        "exit_code": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "timed_out": bool(proc.returncode == 77 or proc.returncode == 100),
        "had_crash": bool(proc.returncode == 101),
        "covered_lines": len(cov_lines),
        "stdout_tail": stdout[-1500:],
        "stderr_tail": stderr[-1500:],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {"schema_version": "v6.7-fuzz-long-summary.v1", "runs": []}
    for binary, label in [
        (BINARY_LEND, "lend_baseline_90s"),
        (BINARY_LEND_EXT, "lend_extended_90s"),
    ]:
        record = run_fuzz(binary, seconds=90, label=label)
        summary["runs"].append(record)
        (OUT_DIR / f"{label}.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
    out = OUT_DIR / "fuzz_long_run.json"
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))
    print(f"\nPersisted: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
