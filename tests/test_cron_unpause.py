"""Tests for v5 Phase 6 cron unpause — dryrun validation with 2 ready targets.

Covers:
- Manifest has ≥2 ready harnesses (uniswap_v4 + aave_v3)
- Pause gate respects NSS_HIPIF_PAUSE_FOR_NATIVE env var
- Dryrun bootstrap succeeds with pause_for_native=0
- Chain bootstrap header reflects bounty_depth and mode
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "security_results" / "loop" / "native_harness_status.json"
BOOTSTRAP = REPO / "hermes" / "scripts" / "nss-hipif-chain.sh"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_has_at_least_two_ready() -> None:
    """Native manifest must have ready_count ≥ 2 before cron unpause."""
    data = _load_manifest()
    ready = [
        slug
        for slug, entry in (data.get("harnesses") or {}).items()
        if entry.get("status") == "ready"
    ]
    assert data.get("ready_count", 0) >= 2
    assert "uniswap_v4" in ready
    assert "aave_v3" in ready


def test_pause_gate_script_checks_ready_status() -> None:
    """Bootstrap embeds a Python gate that requires at least one ready harness."""
    text = BOOTSTRAP.read_text()
    assert 'entry.get("status") == "ready"' in text
    assert "NSS_HIPIF_PAUSE_FOR_NATIVE" in text


def test_pause_gate_exits_when_no_ready(tmp_path: Path) -> None:
    """When pause=1 and manifest has no ready harness, bootstrap exits 0 (no_run)."""
    loop_dir = tmp_path / "data" / "security_results" / "loop"
    loop_dir.mkdir(parents=True)
    manifest = loop_dir / "native_harness_status.json"
    manifest.write_text(
        json.dumps(
            {
                "harnesses": {
                    "morpho_blue": {"status": "harness_built"},
                }
            }
        )
    )
    # Minimal venv shim so bootstrap can reach the pause gate without full chain.
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    python_link = venv_bin / "python"
    python_link.symlink_to(Path(sys.executable))
    stub_main = tmp_path / "night_shift_security" / "cli"
    stub_main.mkdir(parents=True)
    (stub_main / "__init__.py").write_text("")
    (stub_main / "main.py").write_text(
        'import sys; print("{}"); sys.exit(0)'.format('{"chain_status": "dryrun"}')
    )

    result = subprocess.run(
        ["bash", str(BOOTSTRAP)],
        cwd=tmp_path,
        env={
            **dict(__import__("os").environ),
            "NSS_HIPIF_PAUSE_FOR_NATIVE": "1",
            "NSS_HIPIF_MODE": "dryrun",
            "NSS_REPO": str(tmp_path),
            "HERMES_CRON_SCRIPT_TIMEOUT": "30",
            "PYTHONPATH": str(tmp_path),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    paused = json.loads(manifest.read_text())
    assert paused.get("reason") == "paused_awaiting_native_harness"
    assert "Pausing cron" in result.stdout or "no native harness ready" in result.stdout


def test_dryrun_bootstrap_succeeds_with_pause_disabled() -> None:
    """Dryrun with NSS_HIPIF_PAUSE_FOR_NATIVE=0 reaches HIPIF_CHAIN_READY."""
    result = subprocess.run(
        [
            "bash",
            "-c",
            (
                "NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 "
                "NSS_HIPIF_BOUNTY_DEPTH=1 timeout 60 bash "
                f"{BOOTSTRAP} 2>&1 | head -25"
            ),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=90,
    )
    # head may SIGPIPE (141) — bootstrap output is what matters
    output = result.stdout + result.stderr
    assert "pause_for_native=0" in output
    assert "bounty_depth=1" in output
    assert "mode=dryrun" in output
    assert "HIPIF_CHAIN_READY" in output or "chain_status" in output


def test_manifest_ready_slugs_have_evidence_notes() -> None:
    """Ready harnesses document measured-delta evidence in manifest notes."""
    data = _load_manifest()
    for slug in ("uniswap_v4", "aave_v3"):
        entry = data["harnesses"][slug]
        assert entry["status"] == "ready"
        notes = entry.get("notes", "").lower()
        assert "delta" in notes or "measured" in notes


def test_pause_default_is_one_in_bootstrap() -> None:
    """Script defaults NSS_HIPIF_PAUSE_FOR_NATIVE to 1 when unset."""
    text = BOOTSTRAP.read_text()
    assert 'NSS_HIPIF_PAUSE_FOR_NATIVE="${NSS_HIPIF_PAUSE_FOR_NATIVE:-1}"' in text


def test_cron_yaml_documents_unpause_and_rotation() -> None:
    """Example cron YAML documents Phase 6 production env vars."""
    yaml_text = (REPO / "hermes" / "cron" / "jobs.example.yaml").read_text()
    assert "NSS_HIPIF_PAUSE_FOR_NATIVE=0" in yaml_text
    assert "NSS_PHASE4_ROTATION_ENABLED=1" in yaml_text


def test_morpho_blue_remains_harness_built() -> None:
    """Morpho Blue stays harness_built — no positive delta promotion in Phase 6."""
    data = _load_manifest()
    assert data["harnesses"]["morpho_blue"]["status"] == "harness_built"
    assert data.get("ready_count") == 2