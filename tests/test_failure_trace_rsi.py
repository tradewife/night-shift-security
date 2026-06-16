"""Tests for failure trace RSI."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.orchestration.failure_trace import (
    classify_failure,
    fingerprint_failure,
    summarize_failure_traces,
)


def test_classify_failure_actions():
    assert classify_failure({"error": "missing signer for account"}) == (
        "missing_signer",
        "mutate_actor_or_account_role",
    )
    assert classify_failure({"error": "bad discriminator"}) == (
        "bad_discriminator",
        "refresh_idl_instruction_map",
    )
    assert classify_failure({"markers": {"TOKEN_DELTA": "0"}}) == (
        "no_delta_after_success",
        "downgrade_or_add_impact_oracle",
    )
    assert classify_failure({"failure_class": "triage_surface_requires_measured_delta"}) == (
        "missing_economic_impact",
        "generate_value_moving_poc",
    )
    assert classify_failure({"stdout_tail": "TRIAGE_SURFACE_VERIFIED:1 balance_delta_wei=0"}) == (
        "missing_economic_impact",
        "generate_value_moving_poc",
    )


def test_failure_fingerprint_stable():
    record = {"candidate_id": "c1", "error": "bad discriminator", "artifact": "a"}
    assert fingerprint_failure("kamino", record, "bad_discriminator") == fingerprint_failure(
        "kamino",
        record,
        "bad_discriminator",
    )


def test_summarize_failure_traces_writes_hints_and_stop(tmp_path: Path):
    traces_dir = tmp_path / "traces"
    slug_dir = traces_dir / "kamino"
    slug_dir.mkdir(parents=True)
    record = {"candidate_id": "c1", "error": "bad discriminator", "artifact": "a"}
    for i in range(3):
        (slug_dir / f"{i}.json").write_text(json.dumps(record))
    signatures = tmp_path / "failure_signatures.jsonl"
    hints = tmp_path / "refinement_hints.json"

    summary = summarize_failure_traces(
        "kamino",
        traces_dir=traces_dir,
        signatures_path=signatures,
        hints_path=hints,
    )
    payload = json.loads(hints.read_text())
    assert summary["entries"] == 3
    assert summary["stop_trials"] >= 1
    assert payload["semantic_recon_queued"] is True
    assert payload["entries"][-1]["recommended_action"] == "refresh_idl_instruction_map"
