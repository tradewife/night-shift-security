"""Tests for v4 semantic recon and concrete candidates."""

from __future__ import annotations

import json
from pathlib import Path

from night_shift_security.semantic import build_semantic_map, write_semantic_artifacts
from night_shift_security.semantic.candidates import build_candidate_seeds
from night_shift_security.knowledge.concrete_candidates import load_candidate_records, upsert_candidates


def test_semantic_map_extracts_solidity_entrypoints(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Bridge.sol").write_text(
        """
contract Bridge {
    address public owner;
    modifier onlyOwner() { _; }
    function completeTransfer(bytes calldata vaa) external {
        token.transfer(msg.sender, 1);
    }
    function upgrade(address impl) public onlyOwner {
        implementation = impl;
    }
}
"""
    )

    semantic_map = build_semantic_map("wormhole", repo)
    names = {e["name"] for e in semantic_map["entrypoints"]}
    assert {"completeTransfer", "upgrade"}.issubset(names)
    assert semantic_map["summary"]["bridge_flows"] >= 1
    assert semantic_map["summary"]["value_flows"] >= 1
    assert semantic_map["summary"]["authority_signals"] >= 1


def test_semantic_map_extracts_anchor_idl_and_rust(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "target" / "idl").mkdir(parents=True)
    (repo / "programs" / "klend" / "src").mkdir(parents=True)
    (repo / "target" / "idl" / "klend.json").write_text(
        json.dumps(
            {
                "instructions": [
                    {
                        "name": "borrowObligationLiquidity",
                        "accounts": [
                            {"name": "owner", "signer": True},
                            {"name": "reserveLiquiditySupply", "writable": True},
                        ],
                    }
                ]
            }
        )
    )
    (repo / "programs" / "klend" / "src" / "lib.rs").write_text(
        """
#[derive(Accounts)]
pub struct RefreshReserve {}

pub fn refresh_reserve(ctx: Context<RefreshReserve>) -> Result<()> {
    Ok(())
}
"""
    )

    semantic_map = build_semantic_map("kamino", repo)
    names = {e["name"] for e in semantic_map["entrypoints"]}
    assert "borrowObligationLiquidity" in names
    assert "refresh_reserve" in names
    assert semantic_map["summary"]["value_flows"] >= 1
    assert semantic_map["summary"]["oracle_reads"] >= 1


def test_semantic_map_skips_non_idl_json_arrays(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package-lock.json").write_text(json.dumps([{"not": "an idl"}]))
    semantic_map = build_semantic_map("wormhole", repo)
    assert semantic_map["summary"]["entrypoints"] == 0


def test_write_semantic_artifacts_and_candidate_seeds(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Vault.sol").write_text(
        """
contract Vault {
    function withdraw(uint256 amount) external {
        payable(msg.sender).transfer(amount);
    }
}
"""
    )
    out = tmp_path / "semantic"
    result = write_semantic_artifacts("vault", repo, out)
    assert result["summary"]["entrypoints"] == 1
    assert Path(result["paths"]["code_map"]).is_file()
    seeds_path = Path(result["paths"]["candidate_seeds"])
    lines = [json.loads(line) for line in seeds_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["candidate_schema_version"] == 4
    assert lines[0]["target_pinned"] is True
    assert lines[0]["entrypoint"]["name"] == "withdraw"


def test_candidate_filter_bridge_kind(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Bridge.sol").write_text(
        """
contract Bridge {
    function completeTransfer(bytes calldata vaa) external {}
    function deposit(uint256 amount) external {}
}
"""
    )
    semantic_map = build_semantic_map("wormhole", repo)
    candidates = build_candidate_seeds(semantic_map, target_slug="wormhole", kind="bridge")
    assert candidates
    assert all(c.invariant["id"] == "bridge_accounting" for c in candidates)


def test_concrete_candidate_store_upserts(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "Vault.sol").write_text("contract Vault { function withdraw(uint256 amount) external {} }")
    semantic_map = build_semantic_map("vault", repo)
    candidates = build_candidate_seeds(semantic_map, target_slug="vault")
    store = tmp_path / "concrete_candidates.jsonl"
    first = upsert_candidates(candidates, store)
    second = upsert_candidates(candidates, store)
    assert first["after"] == 1
    assert second["after"] == 1
    assert len(load_candidate_records(store)) == 1
