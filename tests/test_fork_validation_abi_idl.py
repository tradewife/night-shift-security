"""Tests for C6 — ABI/IDL hash requirement on fork candidate set."""

from __future__ import annotations

from night_shift_security.validation.fork_validation import (
    _fork_candidate_set,
    _has_native_bind,
)
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector


def _make_candidate(
    *,
    abi_signature_hash: str = "",
    selector_or_discriminator: str = "",
    source_ref_commit: str = "",
    severity_score: float = 1.0,
) -> AttackCandidateResult:
    metadata = {}
    if abi_signature_hash:
        metadata["abi_signature_hash"] = abi_signature_hash
    if selector_or_discriminator or source_ref_commit:
        entrypoint = {}
        if selector_or_discriminator:
            entrypoint["selector_or_discriminator"] = selector_or_discriminator
        source_ref = {}
        if source_ref_commit:
            source_ref["commit"] = source_ref_commit
        metadata["entrypoint"] = entrypoint
        metadata["source_ref"] = source_ref
    return AttackCandidateResult(
        vector=AttackVector(
            template_id="governance_capture",
            parameters={},
            target_id="test_target",
            metadata=metadata,
        ),
        success_rate=1.0,
        mean_severity_score=severity_score,
        mean_economic_impact_usd=1000000,
        reproducibility=1.0,
        generality=1.0,
        realism_score=1.0,
        invariant_violation_count=1,
        severity_score=severity_score,
    )


# ------------------------------------------------------------------ #
# _has_native_bind tests
# ------------------------------------------------------------------ #


def test_solidity_candidate_with_4byte_abi_hash_accepted():
    """Solidity candidate with 10-char abi_signature_hash (0x + 8 hex) accepts."""
    entry = {
        "entrypoint": {
            "abi_signature_hash": "0x12345678",
        }
    }
    assert _has_native_bind(entry) is True


def test_solidity_candidate_with_full_abi_hash_accepted():
    """Solidity candidate with 66-char abi_signature_hash (0x + 64 hex) accepts."""
    entry = {
        "entrypoint": {
            "abi_signature_hash": "0x" + "ab" * 32,
        }
    }
    assert _has_native_bind(entry) is True


def test_solidity_candidate_without_abi_hash_rejected():
    """Solidity candidate with no abi_signature_hash rejects."""
    entry = {"entrypoint": {}}
    assert _has_native_bind(entry) is False


def test_solidity_candidate_empty_abi_hash_rejected():
    """Solidity candidate with empty abi_signature_hash rejects."""
    entry = {"entrypoint": {"abi_signature_hash": ""}}
    assert _has_native_bind(entry) is False


def test_anchor_candidate_with_selector_and_commit_accepted():
    """Anchor candidate with selector_or_discriminator + source_ref.commit accepts."""
    entry = {
        "entrypoint": {"selector_or_discriminator": "0xabcdef01"},
        "source_ref": {"commit": "abc123"},
    }
    assert _has_native_bind(entry) is True


def test_anchor_candidate_without_commit_rejected():
    """Anchor candidate with selector but no commit rejects."""
    entry = {
        "entrypoint": {"selector_or_discriminator": "0xabcdef01"},
        "source_ref": {},
    }
    assert _has_native_bind(entry) is False


def test_anchor_candidate_without_selector_rejected():
    """Anchor candidate with commit but no selector rejects."""
    entry = {
        "entrypoint": {},
        "source_ref": {"commit": "abc123"},
    }
    assert _has_native_bind(entry) is False


def test_empty_entry_rejected():
    """Empty entry rejects."""
    assert _has_native_bind({}) is False


# ------------------------------------------------------------------ #
# _fork_candidate_set tests (C6 top-N filtering)
# ------------------------------------------------------------------ #


def test_fork_candidate_set_filters_by_native_bind():
    """Top-N binder returns the bound subset, not the full severity subset."""
    c_with_bind = _make_candidate(
        selector_or_discriminator="0xabcdef01",
        source_ref_commit="abc123",
        severity_score=2.0,
    )
    c_no_bind = _make_candidate(severity_score=5.0)
    result = _fork_candidate_set([c_with_bind, c_no_bind], {"top_n": 5})
    # When at least one candidate has native bind, only bound ones returned
    assert c_with_bind in result
    assert c_no_bind not in result


def test_fork_candidate_set_prefers_bound_when_exists():
    """When at least one candidate has a native bind, only bound ones are returned."""
    c_bound1 = _make_candidate(
        selector_or_discriminator="0xabcdef01",
        source_ref_commit="abc123",
        severity_score=3.0,
    )
    c_bound2 = _make_candidate(
        severity_score=2.0,
    )
    c_bound2.vector.target_id = "target2"  # different target to avoid dedup
    c_bound2.vector.metadata["entrypoint"] = {"abi_signature_hash": "0xdeadbeef"}
    c_unbound = _make_candidate(severity_score=5.0)
    c_unbound.vector.target_id = "target3"  # different target to avoid dedup
    result = _fork_candidate_set(
        [c_bound1, c_bound2, c_unbound],
        {"top_n": 5},
    )
    # c_unbound should be excluded since there are bound candidates
    assert c_unbound not in result
    assert c_bound1 in result
    assert c_bound2 in result


def test_fork_candidate_set_respects_top_n():
    """Result respects top_n limit."""
    candidates = [
        _make_candidate(
            selector_or_discriminator=f"0x{i:08x}",
            source_ref_commit=f"commit{i}",
            severity_score=float(i),
        )
        for i in range(10)
    ]
    result = _fork_candidate_set(candidates, {"top_n": 3})
    assert len(result) <= 3
    assert len(result) > 0


def test_fork_candidate_set_excludes_rejected():
    """Rejected candidates are excluded."""
    c_rejected = _make_candidate(
        selector_or_discriminator="0xabcdef01",
        source_ref_commit="abc123",
        severity_score=10.0,
    )
    c_rejected.rejected = True
    c_ok = _make_candidate(
        selector_or_discriminator="0xdeadbeef",
        source_ref_commit="def456",
        severity_score=1.0,
    )
    result = _fork_candidate_set([c_rejected, c_ok], {"top_n": 5})
    assert c_rejected not in result
    assert c_ok in result
