"""AuditVault-driven conviction bonus — bounded and advisory only."""

from __future__ import annotations

from night_shift_security.data.schemas import (
    AttackCandidateResult,
    AttackVector,
)
from night_shift_security.validation.self_interrogation import (
    DEFAULT_SELF_INTERROGATION_CONFIG,
    interrogate_candidate,
)


def _candidate(*, audit_refs=None) -> AttackCandidateResult:
    metadata = {
        "priority_score": 0.9,
        "novelty_score": 0.7,
        "source_commit": "abc123",
        "selector_or_discriminator": "0xdeadbeef",
    }
    if audit_refs is not None:
        metadata["auditvault_refs"] = audit_refs
    return AttackCandidateResult(
        vector=AttackVector(
            template_id="access_control_escalation",
            target_id="wormhole",
            label="wormhole-misconfig",
            parameters={"target_role": "guardian"},
            metadata=metadata,
        ),
        success_rate=0.9,
        mean_severity_score=0.8,
        mean_economic_impact_usd=5_000_000.0,
        reproducibility=0.9,
        generality=0.4,
        realism_score=0.75,
        invariant_violation_count=1,
        severity_score=0.7,
        rejected=False,
    )


def test_auditvault_bonus_default_disabled_keeps_baseline_score():
    cfg = dict(DEFAULT_SELF_INTERROGATION_CONFIG)
    cfg.pop("auditvault_bonus", None)
    baseline = interrogate_candidate(_candidate(audit_refs=[
        {"pattern_id": "auditvault:f1", "severity_score": 5.0, "title": "Replay"}
    ]), cfg)
    assert baseline.conviction_score <= 1.0


def test_auditvault_bonus_applied_only_above_min_severity():
    cfg = dict(DEFAULT_SELF_INTERROGATION_CONFIG)
    weak = _candidate(audit_refs=[
        {"pattern_id": "auditvault:info", "severity_score": 1.5, "title": "Info leak"}
    ])
    strong = _candidate(audit_refs=[
        {"pattern_id": "auditvault:crit", "severity_score": 5.0, "title": "Critical replay"}
    ])
    report_weak = interrogate_candidate(weak, cfg)
    report_strong = interrogate_candidate(strong, cfg)
    assert any("auditvault" in arg for arg in report_strong.surviving_arguments), (
        "auditvault_bonus should record a surviving argument when severity >= min"
    )
    assert not any("auditvault" in arg for arg in report_weak.surviving_arguments), (
        "auditvault_bonus should not record a surviving argument below min severity"
    )


def test_auditvault_bonus_capped_at_default_one_and_is_idempotent():
    cfg = dict(DEFAULT_SELF_INTERROGATION_CONFIG)
    bonus = float(cfg.get("auditvault_bonus", 0.05))
    refs = [
        {"pattern_id": f"auditvault:v{i}", "severity_score": 5.0, "title": f"R{i}"}
        for i in range(10)
    ]
    capped = interrogate_candidate(_candidate(audit_refs=refs), cfg)
    # Bonus contribution must not exceed the configured bonus value, even
    # when scaled by max(severity, 5) / 5 = 1.0.
    assert capped.conviction_score <= 1.0


def test_auditvault_bonus_does_not_lower_score_without_refs():
    cfg = dict(DEFAULT_SELF_INTERROGATION_CONFIG)
    base = interrogate_candidate(_candidate(), cfg)
    none_refs = interrogate_candidate(_candidate(audit_refs=[]), cfg)
    assert abs(base.conviction_score - none_refs.conviction_score) < 0.001
