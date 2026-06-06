"""Cross-track bridge: Security findings → Tokenomics attack surface flags."""

from datetime import datetime, timezone

from night_shift_security.data.schemas import AttackCandidateResult, Finding

# Map security templates to tokenomics design parameters that increase risk
_TEMPLATE_TRIGGERS: dict[str, dict] = {
    "governance_capture": {
        "proposal_threshold_pct_max": 40,
        "execution_delay_days_max": 2,
        "treasury_control": ["governance", "multisig"],
        "attack_surface": "governance",
        "base_penalty": 25,
    },
    "treasury_drain": {
        "treasury_control": ["governance", "multisig", "autonomous"],
        "treasury_pct_min": 30,
        "attack_surface": "treasury",
        "base_penalty": 20,
    },
    "flash_loan_oracle": {
        "treasury_pct_min": 20,
        "treasury_control": ["autonomous", "governance"],
        "attack_surface": "oracle",
        "base_penalty": 18,
    },
    "reentrancy": {
        "treasury_control": ["autonomous", "governance"],
        "attack_surface": "implementation",
        "base_penalty": 15,
    },
    "composability_risk": {
        "treasury_control": ["autonomous", "governance"],
        "treasury_pct_min": 15,
        "attack_surface": "composability",
        "base_penalty": 22,
    },
    "upgradeability_risk": {
        "treasury_control": ["governance", "multisig"],
        "attack_surface": "upgradeability",
        "base_penalty": 24,
    },
    "access_control_escalation": {
        "treasury_control": ["autonomous", "multisig", "governance"],
        "attack_surface": "access_control",
        "base_penalty": 26,
    },
}


def generate_tokenomics_risk_feed(
    findings: list[Finding],
    candidates: list[AttackCandidateResult] | None = None,
) -> dict:
    """
    Generate risk feed consumable by Night Shift Tokenomics.

    Tokenomics uses this to penalize attack_resistance on designs that
    match high-severity security finding patterns.
    """
    ranked = sorted(findings, key=lambda f: f.severity_score, reverse=True)
    patterns = _derive_risk_patterns(ranked)

    return {
        "schema_version": "1.0",
        "source": "night-shift-security",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "findings_count": len(ranked),
        "risk_patterns": patterns,
        "findings_summary": [
            {
                "finding_id": f.finding_id,
                "template_id": f.template_id,
                "severity": f.severity.value,
                "severity_score": round(f.severity_score, 4),
                "economic_impact_usd": round(f.economic_impact_usd, 2),
            }
            for f in ranked[:20]
        ],
        "high_risk_attack_surfaces": _aggregate_surfaces(patterns),
    }


def _derive_risk_patterns(findings: list[Finding]) -> list[dict]:
    """Collapse findings into deduplicated risk patterns per template."""
    seen_templates: set[str] = set()
    patterns: list[dict] = []

    for f in findings:
        if f.template_id in seen_templates:
            continue
        seen_templates.add(f.template_id)

        triggers = _TEMPLATE_TRIGGERS.get(f.template_id, {})
        if not triggers:
            continue

        severity_mult = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.5,
            "low": 0.25,
        }.get(f.severity.value, 0.5)

        penalty = round(triggers.get("base_penalty", 10) * severity_mult * (0.5 + f.severity_score), 1)

        patterns.append({
            "pattern_id": f"{f.template_id}_risk",
            "template_id": f.template_id,
            "attack_surface": triggers.get("attack_surface", f.template_id),
            "severity": f.severity.value,
            "severity_score": round(f.severity_score, 4),
            "penalty": min(penalty, 40),
            "triggers": {k: v for k, v in triggers.items() if k not in ("base_penalty", "attack_surface")},
            "mitigations": f.mitigations[:4],
            "source_finding_id": f.finding_id,
        })

    return patterns


def _aggregate_surfaces(patterns: list[dict]) -> list[dict]:
    surfaces: dict[str, dict] = {}
    for p in patterns:
        surface = p["attack_surface"]
        if surface not in surfaces:
            surfaces[surface] = {
                "attack_surface": surface,
                "pattern_count": 0,
                "max_penalty": 0,
                "templates": [],
            }
        surfaces[surface]["pattern_count"] += 1
        surfaces[surface]["max_penalty"] = max(surfaces[surface]["max_penalty"], p["penalty"])
        surfaces[surface]["templates"].append(p["template_id"])

    return sorted(surfaces.values(), key=lambda s: s["max_penalty"], reverse=True)