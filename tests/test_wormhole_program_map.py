"""Tests for Wormhole Block B program mapping."""

from pathlib import Path

from night_shift_security.data.recon import load_recon
from night_shift_security.triage.wormhole_program_map import (
    WORMHOLE_CANONICAL,
    build_wormhole_map,
    scan_repo_for_program_ids,
    write_wormhole_recon,
)


def test_canonical_includes_core_ethereum_and_solana():
    assert WORMHOLE_CANONICAL["core"]["ethereum"].startswith("0x")
    assert WORMHOLE_CANONICAL["core"]["solana"].startswith("worm")


def test_scan_repo_finds_declare_id(tmp_path: Path):
    prog = tmp_path / "programs" / "wormhole"
    prog.mkdir(parents=True)
    (prog / "lib.rs").write_text(
        'declare_id!("worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth");\n'
    )
    found = scan_repo_for_program_ids(tmp_path)
    assert any(p.address.startswith("worm") for p in found)
    assert any(p.signal == "declare_id!" for p in found)


def test_build_wormhole_map_without_repo():
    payload = build_wormhole_map()
    assert payload["target_id"] == "wormhole"
    assert "core_ethereum" in payload["canonical_flat"]
    assert payload["primary_programs"]["core_solana"] == WORMHOLE_CANONICAL["core"]["solana"]


def test_write_wormhole_recon(tmp_path: Path):
    out = tmp_path / "recon.json"
    payload = write_wormhole_recon(out)
    assert out.is_file()
    assert payload["programs"]["core_ethereum"] == WORMHOLE_CANONICAL["core"]["ethereum"]
    assert len(payload["invariants"]) >= 4
    assert payload["threat_model"]["exclude_analogue"] == "nomad-bridge-2022-proxy"


def test_load_wormhole_recon_after_write(tmp_path: Path, monkeypatch):
    recon_dir = tmp_path / "sources" / "wormhole"
    recon_dir.mkdir(parents=True)
    out = recon_dir / "recon.json"
    write_wormhole_recon(out)

    import night_shift_security.data.recon as recon_mod

    monkeypatch.setattr(recon_mod, "_RECON_ROOT", tmp_path / "sources")
    loaded = load_recon("wormhole")
    assert loaded is not None
    assert loaded["programs"]["token_bridge_solana"] == WORMHOLE_CANONICAL["token_bridge"]["solana"]