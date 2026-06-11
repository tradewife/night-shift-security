"""Scan Immunefi programs with the Night Shift engine (shoestring / zero-RPC)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from night_shift_security.bounty.discovery_scan import run_bounty_scan
from night_shift_security.bounty.discovery_scan import scan_program as _scan_program
from night_shift_security.data.immunefi_registry import ImmunefiProgram, immunefi_to_bounty, program_summary


def scan_program(program: ImmunefiProgram, config, catalog, gates) -> dict[str, Any]:
    """Backward-compatible scan entry for ImmunefiProgram."""
    return _scan_program(immunefi_to_bounty(program), config, catalog, gates)


def run_immunefi_scan(
    *,
    config_path: Path | None = None,
    ecosystem: str | None = None,
    min_max_bounty_usd: int = 0,
    limit: int | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Scan curated Immunefi programs and write a ranked report."""
    return run_bounty_scan(
        config_path=config_path,
        platform="immunefi",
        ecosystem=ecosystem,
        min_max_bounty_usd=min_max_bounty_usd,
        limit=limit,
        output_dir=output_dir,
    )


# Re-export for tests that import program_summary from scan module
__all__ = ["scan_program", "run_immunefi_scan", "program_summary"]