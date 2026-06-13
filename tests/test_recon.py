"""Tests for protocol recon loader."""

from night_shift_security.data.recon import load_recon, merge_recon_into_target_config


def test_load_kamino_recon():
    recon = load_recon("kamino")
    assert recon is not None
    assert recon["target_id"] == "kamino"
    assert len(recon.get("invariants", [])) >= 3
    assert "klend" in recon.get("programs", {})


def test_load_wormhole_recon():
    recon = load_recon("wormhole")
    assert recon is not None
    assert recon["target_id"] == "wormhole"
    assert recon["programs"]["core_solana"].startswith("worm")
    assert recon["threat_model"]["exclude_analogue"] == "nomad-bridge-2022-proxy"


def test_merge_recon_into_target_config():
    merged = merge_recon_into_target_config({
        "target_id": "kamino",
        "protocol_name": "Kamino",
        "chain": "solana",
        "templates": ["flash_loan_oracle"],
        "program_id": "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",
    })
    meta = merged["state_overrides"]["metadata"]
    assert "recon_invariants" in meta
    assert merged.get("exploit_id") == "mango-markets-2022"