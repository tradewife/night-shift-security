"""Tests for Wormhole triage-scoped proposal builder."""

import json
from pathlib import Path

from night_shift_security.triage.wormhole_proposals import build_wormhole_triage_proposals


def test_build_proposals_from_triage(tmp_path: Path):
    triage = tmp_path / "wormhole_files.json"
    triage.write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "solana/modules/token_bridge/core.rs",
                        "score": 5,
                        "signals": ["tier5:bridge"],
                    },
                    {
                        "path": "solana/solitaire/program/src/event_cpi.rs",
                        "score": 4,
                        "signals": ["tier4:cpi"],
                    },
                ]
            }
        )
    )
    proposals = build_wormhole_triage_proposals(triage, min_score=5, max_files=5)
    assert len(proposals) >= 2
    templates = {p["template"] for p in proposals}
    assert "access_control_escalation" in templates or "composability_risk" in templates
    assert all("ranked_file" in p for p in proposals)