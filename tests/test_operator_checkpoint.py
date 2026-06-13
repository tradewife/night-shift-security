"""Tests for operator checkpoint persistence."""

import json
from pathlib import Path

from night_shift_security.orchestration.operator_checkpoint import (
    clear_checkpoint,
    load_checkpoint,
    save_checkpoint,
    write_checkpoint,
)


def test_checkpoint_round_trip(tmp_path: Path):
    path = tmp_path / "checkpoint.json"
    payload = write_checkpoint(
        target_slug="kamino",
        active_hypothesis="klend oracle stale borrow",
        next_commands=["bounty loop --trials 5"],
        context_reason="rollover",
        path=path,
    )
    assert payload["target_slug"] == "kamino"
    assert payload["session_id"]

    loaded = load_checkpoint(path)
    assert loaded["active_hypothesis"] == "klend oracle stale borrow"
    assert loaded["next_commands"] == ["bounty loop --trials 5"]


def test_clear_checkpoint(tmp_path: Path):
    path = tmp_path / "checkpoint.json"
    save_checkpoint({"target_slug": "wormhole"}, path)
    assert path.is_file()
    clear_checkpoint(path)
    assert not path.is_file()


def test_default_checkpoint_is_valid_json_shape():
    data = load_checkpoint(Path("/nonexistent/checkpoint.json"))
    assert data["version"] == 1
    assert "ranked_files" in data
    json.dumps(data)