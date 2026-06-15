"""Tests for Opengrep/SARIF candidate ingestion."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.semantic import build_semantic_map
from night_shift_security.tools.opengrep import findings_to_candidates, load_sarif, sarif_results


def _sarif() -> dict:
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "opengrep",
                        "rules": [{"id": "nss.bridge.unchecked-message-processing", "name": "bridge"}],
                    }
                },
                "results": [
                    {
                        "ruleId": "nss.bridge.unchecked-message-processing",
                        "level": "warning",
                        "message": {"text": "bridge message processing"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "Bridge.sol"},
                                    "region": {"startLine": 4},
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_sarif_results_extracts_location_and_rule(tmp_path: Path):
    path = tmp_path / "opengrep.sarif"
    path.write_text(json.dumps(_sarif()))
    findings = sarif_results(load_sarif(path))
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "nss.bridge.unchecked-message-processing"
    assert findings[0]["file"] == "Bridge.sol"
    assert findings[0]["trusted"] is False


def test_sarif_findings_convert_to_candidates(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Bridge.sol").write_text(
        """
contract Bridge {
    function completeTransfer(bytes calldata vaa) external {
    }
}
"""
    )
    semantic_map = build_semantic_map("wormhole", repo)
    candidates = findings_to_candidates(sarif_results(_sarif()), semantic_map, slug="wormhole")
    assert len(candidates) == 1
    candidate = candidates[0].to_dict()
    assert candidate["target_slug"] == "wormhole"
    assert candidate["candidate_schema_version"] == 4
    assert candidate["provenance"]["source"] == "opengrep"
    assert candidate["provenance"]["rule_id"] == "nss.bridge.unchecked-message-processing"
