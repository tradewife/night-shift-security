"""Tests for the KAST / M0 Solana M Extensions sidecar helpers."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from night_shift_security.native import kast
from night_shift_security.semantic.selectors import anchor_discriminator


def test_harness_metadata_constants() -> None:
    assert kast.HARNESS_TARGET == "kast"
    assert kast.HARNESS_PLATFORM == "immunefi"
    assert kast.HARNESS_CHAIN == "solana"
    assert kast.HARNESS_NAME == "KAST M0 Solana M Extensions"
    assert kast.HARNESS_VERSION.startswith("v6.27")


def test_program_ids_shape() -> None:
    ids = kast.program_ids()
    assert ids["m_ext"] == kast.M_EXT_PROGRAM
    assert ids["ext_swap"] == kast.EXT_SWAP_PROGRAM
    assert ids["earn_program"] == kast.EARN_PROGRAM
    assert ids["wm_extension"] == kast.WM_EXTENSION
    assert ids["system"] == kast.SYSTEM_PROGRAM
    for pubkey in (kast.M_EXT_PROGRAM, kast.EXT_SWAP_PROGRAM, kast.EARN_PROGRAM, kast.WM_EXTENSION):
        assert re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", pubkey)


def test_variant_builds_have_expected_matrix_and_files() -> None:
    builds = kast.variant_builds()
    assert set(builds) == {
        "ext_swap_migrate",
        "m_ext_scaled_ui",
        "m_ext_no_yield",
        "m_ext_crank",
        "m_ext_no_yield_migrate",
    }
    for build in builds.values():
        assert build.so_path.is_file(), build.so_path
        assert build.idl_path.is_file(), build.idl_path
        assert build.types_path.is_file(), build.types_path


def test_load_manifest_reads_pinned_commit() -> None:
    manifest = kast.load_manifest()
    assert manifest["target"] == "kast"
    assert manifest["source_commit"] == "c12a23acd8baeba92d4d9f64feb47837ddccca09"
    assert manifest["source_path_defaulted"] is False
    assert manifest["programs"]["m_ext"] == kast.M_EXT_PROGRAM


def test_load_manifest_fallback_when_missing(tmp_path: Path) -> None:
    manifest = kast.load_manifest(tmp_path / "missing.json")
    assert manifest["target"] == "kast"
    assert manifest["source_path_defaulted"] is True


def test_validate_feature_flags_accepts_valid_configs() -> None:
    assert kast.validate_feature_flags(["scaled-ui"]) == "scaled-ui"
    assert kast.validate_feature_flags(["no-yield"]) == "no-yield"
    assert kast.validate_feature_flags(["crank"]) == "crank"
    assert kast.validate_feature_flags(["crank", "migrate", "wm"]) == "crank"


def test_validate_feature_flags_rejects_invalid_configs() -> None:
    with pytest.raises(ValueError, match="no_yield_feature_enabled"):
        kast.validate_feature_flags([])
    with pytest.raises(ValueError, match="multiple_yield_features_enabled"):
        kast.validate_feature_flags(["scaled-ui", "crank"])
    with pytest.raises(ValueError, match="invalid_crank_migrate_without_wm"):
        kast.validate_feature_flags(["crank", "migrate"])


def test_load_idl_addresses_match_variants() -> None:
    assert kast.load_idl("m_ext_scaled_ui")["address"] == kast.M_EXT_PROGRAM
    assert kast.load_idl("m_ext_crank")["address"] == kast.M_EXT_PROGRAM
    assert kast.load_idl("m_ext_no_yield")["address"] == kast.M_EXT_PROGRAM
    assert kast.load_idl("ext_swap_migrate")["address"] == kast.EXT_SWAP_PROGRAM


def test_variant_instruction_surfaces_are_distinct() -> None:
    scaled = set(kast.instruction_names("m_ext_scaled_ui"))
    crank = set(kast.instruction_names("m_ext_crank"))
    no_yield = set(kast.instruction_names("m_ext_no_yield"))

    assert "set_fee" in scaled
    assert "claim_fees" in scaled
    assert "sync" in scaled
    assert "claim_for" not in scaled

    assert "claim_for" in crank
    assert "add_earner" in crank
    assert "transfer_earner" in crank
    assert "sync" in crank
    assert "claim_fees" not in crank

    assert "claim_fees" in no_yield
    assert "sync" not in no_yield
    assert "claim_for" not in no_yield


def test_union_instruction_names_captures_migration_and_core_paths() -> None:
    union = kast.union_instruction_names()
    assert "wrap" in union
    assert "unwrap" in union
    assert "migrate_m" in union
    assert "initialize_global" in union


def test_discriminators_match_anchor_helper_for_each_variant() -> None:
    for variant in ("m_ext_scaled_ui", "m_ext_no_yield", "m_ext_crank", "m_ext_no_yield_migrate"):
        for name, value in kast.discriminators(variant).items():
            assert re.fullmatch(r"0x[0-9a-f]{16}", value)
            assert value == anchor_discriminator(name)


def test_load_idl_rejects_unknown_variant() -> None:
    with pytest.raises(KeyError, match="unknown_variant:bogus"):
        kast.load_idl("bogus")


def test_compute_scaled_ui_yield_conserves_amounts() -> None:
    breakdown = kast.compute_scaled_ui_yield(before=1_000_000, after=1_125_000, fee_bps=400)
    assert breakdown.gross_yield == 125_000
    assert breakdown.fee_amount == 5_000
    assert breakdown.distributable == 120_000
    assert breakdown.fee_amount + breakdown.distributable == breakdown.gross_yield


def test_compute_scaled_ui_yield_rejects_bad_inputs() -> None:
    with pytest.raises(ValueError, match="fee_bps_out_of_range"):
        kast.compute_scaled_ui_yield(1, 2, 10_001)
    with pytest.raises(ValueError, match="negative_gross_yield"):
        kast.compute_scaled_ui_yield(2, 1, 0)
    with pytest.raises(ValueError, match="negative_balance"):
        kast.compute_scaled_ui_yield(-1, 0, 0)


def test_compute_crank_claim_uses_same_fee_conservation() -> None:
    breakdown = kast.compute_crank_claim(claimable_yield=50_000, fee_bps=250)
    assert breakdown.before == 0
    assert breakdown.after == 50_000
    assert breakdown.gross_yield == 50_000
    assert breakdown.fee_amount == 1_250
    assert breakdown.distributable == 48_750


def test_pending_yield_conserved_accepts_non_negative_totals() -> None:
    assert kast.pending_yield_conserved(0, 10, 20) is True
    assert kast.pending_yield_conserved(-1, 0) is False


def test_compute_sync_outcome_updates_ext_index_only_when_vault_active() -> None:
    synced = kast.compute_sync_outcome(
        previous_ext_index=1_000_000_000_000,
        previous_m_index=1_000_000_000_000,
        current_m_index=1_000_000_500_000,
    )
    assert synced.new_ext_index == 1_000_000_500_000
    frozen = kast.compute_sync_outcome(
        previous_ext_index=1_000_000_000_000,
        previous_m_index=1_000_000_000_000,
        current_m_index=1_000_000_500_000,
        vault_initialized=False,
    )
    assert frozen.new_ext_index == 1_000_000_000_000


def test_compute_crank_claim_outcome_models_claim_and_fee() -> None:
    outcome = kast.compute_crank_claim_outcome(
        snapshot_balance=1_000_000,
        last_claim_index=1_000_000_000_000,
        global_index=1_100_000_000_000,
        fee_bps=500,
        ext_supply=5_000_000,
        ext_collateral=6_000_000,
    )
    assert outcome.rewards == 100_000
    assert outcome.fee_amount == 5_000
    assert outcome.distributable == 95_000


def test_compute_crank_claim_outcome_rejects_frozen_and_insolvent_claims() -> None:
    with pytest.raises(ValueError, match="already_claimed_or_frozen"):
        kast.compute_crank_claim_outcome(
            snapshot_balance=1,
            last_claim_index=10,
            global_index=10,
            fee_bps=0,
        )
    with pytest.raises(ValueError, match="insufficient_collateral"):
        kast.compute_crank_claim_outcome(
            snapshot_balance=1_000_000,
            last_claim_index=1_000_000_000_000,
            global_index=1_100_000_000_000,
            fee_bps=0,
            ext_supply=5_950_000,
            ext_collateral=6_000_000,
        )


def test_compute_claim_fees_principal_rounds_conservatively() -> None:
    claimed = kast.compute_claim_fees_principal(
        vault_principal=1_500_000,
        ext_supply_principal=1_000_000,
        ext_index=1_050_000_000_000,
        m_index=1_100_000_000_000,
    )
    assert claimed > 0


def test_earner_state_transfer_and_recipient_changes_preserve_indices() -> None:
    state = kast.EarnerState(
        user="user",
        user_token_account="uta",
        earn_manager="manager-a",
        last_claim_index=123,
        last_claim_timestamp=456,
    )
    moved = kast.transfer_earner_state(state, "manager-b")
    assert moved.earn_manager == "manager-b"
    assert moved.last_claim_index == state.last_claim_index
    recipient = kast.set_recipient_state(moved, "rta")
    assert recipient.recipient_token_account == "rta"
    assert recipient.earn_manager == moved.earn_manager


def test_detect_authority_role_collisions_groups_multi_role_actors() -> None:
    collisions = kast.detect_authority_role_collisions(
        {
            "admin": "alice",
            "wrap_authority": "alice",
            "earn_manager": "bob",
            "permanent_delegate": "alice",
            "close_mint_authority": None,
        }
    )
    assert collisions == {"alice": ["admin", "wrap_authority", "permanent_delegate"]}
