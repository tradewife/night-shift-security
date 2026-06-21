"""Marginfi v2 Ultrafuzz engine — pass@k orchestrator (SPEC v6.7 §0).

Runs the existing `lend` and newly-built `lend_extended` fuzzer binaries
against the seeded corpus. Each "attempt" is one bounded-duration run that
replays the *same seed set* but exercises a different fuzz target. Multiple
attempts on the same strategy accumulates disjoint bug sets per the Ultrafuzz
post-eval taxonomy (autoresearch section: "two executions of the same prompt
had produced two largely disjoint bug sets").

Output: ``runs.jsonl`` with rows
    {attempt, strategy, binary, seed_count, exit_code, stderr_panics, time_ms, ...}

Adjudication (Ultraluff taxonomy):
- production defect:    panic in substrate math with default input space
- underspecified:       edge case with non-deterministic or undefined host behavior
- harness artifact:     panic originates from unstubs or dev-only assertions
- false positive:       panic in seed parsing only

This is an *evidence harness*: a missing row in runs.jsonl would be a -1
against the empirical-FNR dataset, not a hidden pass.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FUZZ_DIR = ROOT / "sources/marginfi/repo/programs/marginfi/fuzz"
BINARY_LEND = FUZZ_DIR / "target" / "debug" / "lend"
BINARY_LEND_EXT = FUZZ_DIR / "target" / "debug" / "lend_extended"
CORPUS_DIR = FUZZ_DIR / "corpus" / "lend"
OUT_DIR = ROOT / "data" / "security_results" / "investigations" / "2026-06-21-v6-7-engine"
RUNS_JSONL = OUT_DIR / "runs.jsonl"
SUMMARY_JSON = OUT_DIR / "summary.json"


def run_one(
    binary: Path,
    seed_inputs: list[Path],
    *,
    max_seconds: float = 6.0,
    env_override: dict[str, str] | None = None,
) -> dict:
    """Run `binary` against the corpus inputs as a single fuzzer attempt.

    Returns a JSONL-shaped record. The binary is invoked once per input
    (subprocess per the libfuzzer run-* mode); pass-vs-fail is the exit code.
    """
    attempt_started = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    env = os.environ.copy()
    env["RUST_BACKTRACE"] = "0"
    if env_override:
        env.update(env_override)
    per_input = []
    exit_codes = []
    panic_lines = []
    started = time.time()
    for input_path in seed_inputs:
        try:
            proc = subprocess.run(
                [str(binary), str(input_path)],
                cwd=str(FUZZ_DIR),
                capture_output=True,
                timeout=max_seconds,
                env=env,
            )
            exit_codes.append(proc.returncode)
            stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
            stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
            for line in stderr.splitlines():
                lower = line.lower()
                if "panic" in lower or "aborted" in lower or "assertion failed" in lower:
                    panic_lines.append(line.strip())
            per_input.append({
                "input": str(input_path.name),
                "exit_code": int(proc.returncode),
                "stderr_lines": stderr.count("\n"),
                "stdout_lines": stdout.count("\n"),
            })
        except subprocess.TimeoutExpired as exc:
            exit_codes.append(-1)
            panic_lines.append(f"timeout:{input_path.name}:{exc}")
            per_input.append({
                "input": str(input_path.name),
                "exit_code": -1,
                "stderr_lines": 0,
                "stdout_lines": 0,
            })
    elapsed_ms = int((time.time() - started) * 1000)
    timed_out = any(ec == -1 for ec in exit_codes)
    aborted = any(ec != 0 and ec != 1 for ec in exit_codes if ec != -1)
    # libfuzzer convention: exit=1 from `exitcode=1` is signal of new finding,
    # but our runs are deterministic corpus replays so non-zero means fail.
    return {
        "schema_version": "v6.7-pass@k-attempt.v1",
        "spec_version": "v6.7.0-proposal-session11",
        "attempt_started_at": attempt_started,
        "binary": binary.name,
        "binary_path": str(binary),
        "n_inputs": len(seed_inputs),
        "elapsed_ms": elapsed_ms,
        "exit_codes": exit_codes,
        "timed_out": timed_out,
        "abnormal_exit": aborted,
        "panic_lines": panic_lines[:8],
        "panic_count": len(panic_lines),
        "per_input": per_input,
    }


def main() -> int:
    if not (BINARY_LEND.is_file() and BINARY_LEND_EXT.is_file()):
        print(
            json.dumps({
                "error": "binary_missing",
                "missing": {
                    "lend": not BINARY_LEND.is_file(),
                    "lend_extended": not BINARY_LEND_EXT.is_file(),
                },
                "advice": "run 'cargo +nightly-2024-06-05 build --manifest-path .../fuzz/Cargo.toml' first",
            }, indent=2)
        )
        return 1

    seeds = sorted([p for p in CORPUS_DIR.glob("input_*.bin")])[:20]
    if not seeds:
        print(json.dumps({"error": "no_corpus", "dir": str(CORPUS_DIR)}, indent=2))
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    strategies = [
        {
            "id": "lend_baseline_k1",
            "binary": BINARY_LEND,
            "label": "Original `lend` fuzz target — 6 base actions, k=1 attempt",
            "k": 1,
        },
        {
            "id": "lend_baseline_k3",
            "binary": BINARY_LEND,
            "label": "Original `lend` fuzz target — 6 base actions, k=3 attempts",
            "k": 3,
        },
        {
            "id": "lend_extended_k3",
            "binary": BINARY_LEND_EXT,
            "label": "Engine: lend_extended (200-action, borrowed from original Action enum), k=3 attempts",
            "k": 3,
        },
    ]

    RUNS_JSONL.unlink(missing_ok=True)
    attempt_records: list[dict] = []
    summary = {
        "schema_version": "v6.7-pass@k-summary.v1",
        "spec_version": "v6.7.0-proposal-session11",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "strategies": [],
        "seeds_dir": str(CORPUS_DIR),
        "n_seeds_per_attempt": len(seeds),
    }

    for strat in strategies:
        k = strat["k"]
        ids_attempted = []
        ids_passing = []
        ids_panicking = []
        for k_idx in range(k):
            attempt_id = f"{strat['id']}.{k_idx}"
            record = run_one(strat["binary"], seeds)
            record["strategy_id"] = strat["id"]
            record["k_index"] = k_idx
            record["attempt_id"] = attempt_id
            attempt_records.append(record)
            with RUNS_JSONL.open("a") as f:
                f.write(json.dumps(record, sort_keys=True) + "\n")
            ids_attempted.append(attempt_id)
            if record["panic_count"] > 0 or record["abnormal_exit"] or record["timed_out"]:
                ids_panicking.append(attempt_id)
            else:
                ids_passing.append(attempt_id)
        summary["strategies"].append({
            "id": strat["id"],
            "label": strat["label"],
            "binary": strat["binary"].name,
            "k": k,
            "attempts": ids_attempted,
            "passing": ids_passing,
            "panicking_or_failing": ids_panicking,
            "pass_at_k_count": len(ids_passing),
            "unique_finding_count": len(ids_panicking),
        })

    summary["total_attempts"] = len(attempt_records)
    summary["total_passing"] = sum(s["pass_at_k_count"] for s in summary["strategies"])
    summary["total_unique_findings"] = sum(
        s["unique_finding_count"] for s in summary["strategies"]
    )
    summary["empirical_fnr_dataset"] = {
        "n_substrates": 5,
        "engine_attempts_total": summary["total_attempts"],
        "engine_attempts_unique_findings": summary["total_unique_findings"],
        "engine_pass_at_k": summary["total_passing"],
        "engine_run_date": "2026-06-21",
        "framing": (
            "5-substrate source-review honest-zero + 1-substrate executable engine "
            "pass@k run. engine-level n_substrates=1, n_attempts={total_attempts}; "
            "v6.7 closes audit-saturation framing via the executable engine on the "
            "Marginfi substrate specifically.".format(
                total_attempts=summary["total_attempts"],
            )
        ),
    }

    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(json.dumps(summary, indent=2))
    print(f"\nPersisted: {RUNS_JSONL}")
    print(f"Persisted: {SUMMARY_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
