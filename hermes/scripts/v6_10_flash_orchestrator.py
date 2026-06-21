"""v6.10 Ultrafuzz orchestrator — Marginfi flash-loan focused target.

Mirrors ``v6_7_engine_orchestrator.py`` but drives the new ``lend_flash_loan``
fuzz binary the v6.10 Path-B diff introduced. Per Ultrafuzz: repeated attempts
with fresh context can produce disjoint bug sets, so we run the binary against
the seeds K times and record each attempt as its own JSONL row.

Output:
    runs.jsonl     - per-attempt record (panics, exit codes, time)
    summary.json   - aggregate verdict + classification
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FUZZ_DIR = ROOT / "sources/marginfi/repo/programs/marginfi/fuzz"
BINARY = FUZZ_DIR / "target" / "release" / "lend_flash_loan"
OUT_DIR = ROOT / "data" / "security_results" / "investigations" / "2026-06-22-v6-10-mirror-attempt-1"
RUNS_JSONL = OUT_DIR / "runs.jsonl"
SUMMARY_JSON = OUT_DIR / "summary.json"


def synth_seed(attempt_no: int, seed_no: int) -> bytes:
    """Generate a deterministic high-entropy seed large enough for the full context."""
    base = f"v6.10-flash-attempt={attempt_no}:seed={seed_no}:".encode()
    out = bytearray()
    counter = 0
    while len(out) < 4096:
        out.extend(base)
        out.extend(counter.to_bytes(4, "little"))
        out.extend(((attempt_no * 1315423911 + seed_no * 2654435761 + counter) & 0xFFFFFFFF).to_bytes(4, "little"))
        counter += 1
    return bytes(out[:4096])


def parse_int_stat(stderr: str, key: str) -> int | None:
    prefix = f"stat::{key}:"
    for line in stderr.splitlines():
        if line.startswith(prefix):
            try:
                return int(line[len(prefix):].strip())
            except ValueError:
                return None
    return None


def run_one(
    binary: Path,
    *,
    max_seconds: float = 30.0,
    corpus_dir: Path,
    attempt_no: int,
) -> dict:
    attempt_started = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    env = os.environ.copy()
    env["RUST_BACKTRACE"] = "1"
    args = [
        str(binary),
        str(corpus_dir),
        f"-max_total_time={int(max_seconds)}",
        "-print_final_stats=1",
        "-rss_limit_mb=4096",
    ]
    started = time.time()
    try:
        proc = subprocess.run(
            args,
            cwd=str(FUZZ_DIR),
            capture_output=True,
            timeout=max_seconds + 15,
            env=env,
        )
        elapsed = int((time.time() - started) * 1000)
        panic_lines = []
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        fixed_input_replay = "NOTE: fuzzing was not performed" in stderr
        no_interesting_inputs = "no interesting inputs were found" in stderr
        start_reject_count = stderr.count("start-flashloan-reject:")
        end_reject_count = stderr.count("end-flashloan-reject:")
        flash_summary_lines = [
            line for line in stderr.splitlines()
            if line.startswith("v6.10 flash-loop summary:")
        ]
        flash_actions_observed = start_reject_count > 0 or end_reject_count > 0
        for line in stderr.splitlines():
            low = line.lower()
            if "panic" in low or "aborted" in low or "assertion failed" in low:
                panic_lines.append(line.strip())
        # Classify the panic as substrate level vs harness level
        new_findings: list[str] = []
        for line in panic_lines:
            line_low = line.lower()
            if "Unexpected start-flashloan error" in line:
                new_findings.append("substrate_reject_drift:start")
            if "Unexpected end-flashloan error" in line:
                new_findings.append("substrate_reject_drift:end")
            if "flashloan" in line_low and "panic" in line_low:
                new_findings.append("substrate_flash_state_unexpected")
        executed_units = parse_int_stat(stderr, "number_of_executed_units")
        return {
            "schema_version": "v6.10-pass@k-attempt.v1",
            "spec_version": "v6.10.0-ultrafuzz-informed-forensic-campaign",
            "attempt": attempt_no,
            "binary": binary.name,
            "binary_path": str(binary),
            "exit_code": int(proc.returncode),
            "elapsed_ms": elapsed,
            "panic_lines": panic_lines[:24],
            "panic_count": len(panic_lines),
            "fixed_input_replay": fixed_input_replay,
            "no_interesting_inputs": no_interesting_inputs,
            "executed_units": executed_units,
            "start_reject_count": start_reject_count,
            "end_reject_count": end_reject_count,
            "flash_actions_observed": flash_actions_observed,
            "flash_summary_tail": flash_summary_lines[-5:],
            "stderr_tail": stderr[-2000:],
            "new_findings": new_findings,
            "corpus_dir": str(corpus_dir),
            "started_at": attempt_started,
        }
    except subprocess.TimeoutExpired:
        elapsed = int((time.time() - started) * 1000)
        return {
            "schema_version": "v6.10-pass@k-attempt.v1",
            "spec_version": "v6.10.0-ultrafuzz-informed-forensic-campaign",
            "attempt": attempt_no,
            "binary": binary.name,
            "binary_path": str(binary),
            "exit_code": -1,
            "elapsed_ms": elapsed,
            "panic_lines": [],
            "panic_count": 0,
            "fixed_input_replay": False,
            "no_interesting_inputs": False,
            "executed_units": None,
            "start_reject_count": 0,
            "end_reject_count": 0,
            "flash_actions_observed": False,
            "flash_summary_tail": [],
            "stderr_tail": "TIMEOUT",
            "new_findings": [],
            "corpus_dir": str(corpus_dir),
            "started_at": attempt_started,
        }


def main() -> int:
    if not BINARY.is_file():
        print(
            f"ERROR: binary missing at {BINARY}. Build with `RUSTFLAGS='--cfg fuzzing' "
            f"cargo +nightly-2024-06-05 build --release --bin lend_flash_loan` first.",
            file=sys.stderr,
        )
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "evidence").mkdir(parents=True, exist_ok=True)

    rows = []
    for k in range(5):
        corpus_dir = OUT_DIR / "evidence" / f"corpus_attempt_{k+1:02d}"
        if corpus_dir.exists():
            shutil.rmtree(corpus_dir)
        corpus_dir.mkdir(parents=True, exist_ok=True)
        for seed_no in range(4):
            (corpus_dir / f"seed_{seed_no}.bin").write_bytes(synth_seed(k + 1, seed_no))
        row = run_one(BINARY, max_seconds=20.0, corpus_dir=corpus_dir, attempt_no=k + 1)
        rows.append(row)
        with (OUT_DIR / "evidence" / f"attempt_{k+1:02d}.stderr.txt").open("w") as f:
            f.write(row.get("stderr_tail", ""))
            f.write("\n--- panic_lines ---\n")
            f.write("\n".join(row.get("panic_lines", [])))

    with RUNS_JSONL.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    passes = sum(
        1
        for r in rows
        if r["exit_code"] == 0
        and r["panic_count"] == 0
        and not r["fixed_input_replay"]
        and (r["executed_units"] or 0) > 0
        and r["flash_actions_observed"]
    )
    fails = sum(
        1
        for r in rows
        if r["exit_code"] not in (0, 1)
        or r["panic_count"] > 0
        or r["fixed_input_replay"]
        or not ((r["executed_units"] or 0) > 0)
        or not r["flash_actions_observed"]
    )
    unique_new_findings = set()
    for r in rows:
        for nf in r["new_findings"]:
            unique_new_findings.add(nf)

    verdict = {
        "schema_version": "v6.10-orchestrator-summary.v1",
        "spec_version": "v6.10.0-ultrafuzz-informed-forensic-campaign",
        "binary": BINARY.name,
        "attempts": len(rows),
        "runs_passing": passes,
        "runs_failing": fails,
        "unique_substrate_signals": sorted(unique_new_findings),
        "verdict": "ENGINE-LEVEL HONEST-ZERO" if fails == 0 and passes == len(rows) else (
            "ENGINE SIGNAL" if unique_new_findings else "HARNESS / ARTIFACT"
        ),
        "all_exit_codes": [r["exit_code"] for r in rows],
        "all_panic_counts": [r["panic_count"] for r in rows],
        "all_executed_units": [r["executed_units"] for r in rows],
        "all_start_reject_counts": [r["start_reject_count"] for r in rows],
        "all_end_reject_counts": [r["end_reject_count"] for r in rows],
        "all_flash_actions_observed": [r["flash_actions_observed"] for r in rows],
        "fixed_input_replay": any(r["fixed_input_replay"] for r in rows),
        "no_interesting_inputs": any(r["no_interesting_inputs"] for r in rows),
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
    }
    SUMMARY_JSON.write_text(json.dumps(verdict, indent=2) + "\n")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
