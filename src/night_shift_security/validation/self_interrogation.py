"""Adversarial self-interrogation gate for candidate triage.

The gate is intentionally deterministic and advisory by default. It attacks a
candidate's assumptions before expensive validation lanes spend fork or
validator budget, then records a structured conviction report in metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from night_shift_security.data.schemas import AttackCandidateResult

InterrogationAction = Literal["proceed", "revise", "discard", "escalate"]

DEFAULT_SELF_INTERROGATION_CONFIG: dict[str, Any] = {
    "enabled": True,
    "mode": "advisory",
    "top_n": 50,
    "proceed_threshold": 0.68,
    "revise_threshold": 0.45,
    "min_impact_usd": 100_000.0,
    "rank_adjustment": False,
    "max_rank_adjustment": 0.035,
}

_BYPASS_GENERATION_METHODS = frozenset({"catalog_seed", "ground_truth"})


@dataclass(frozen=True)
class ConvictionReport:
    candidate_label: str
    conviction_score: float
    recommended_action: InterrogationAction
    adversarial_challenges: list[str] = field(default_factory=list)
    surviving_arguments: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    open_assumptions: list[str] = field(default_factory=list)
    lineage_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["conviction_score"] = round(self.conviction_score, 4)
        return payload


@dataclass
class InterrogationStats:
    analyzed: int = 0
    proceed: int = 0
    revise: int = 0
    discard: int = 0
    escalate: int = 0
    filtered: int = 0
    rank_adjusted: int = 0

    def record(self, action: InterrogationAction) -> None:
        self.analyzed += 1
        if action == "proceed":
            self.proceed += 1
        elif action == "revise":
            self.revise += 1
        elif action == "discard":
            self.discard += 1
        elif action == "escalate":
            self.escalate += 1

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _bounded(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _has_any_key(metadata: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(bool(metadata.get(key)) for key in keys)


def _has_source_binding(metadata: dict[str, Any]) -> bool:
    if _has_any_key(
        metadata,
        (
            "concrete_candidate_id",
            "candidate_id",
            "source_ref",
            "source_commit",
            "selector_or_discriminator",
            "entrypoint",
        ),
    ):
        return True
    return bool(metadata.get("concrete_candidate"))


def _candidate_generation_method(candidate: AttackCandidateResult) -> str:
    return str((candidate.vector.metadata or {}).get("generation_method") or "")


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    text = str(value)
    return [text] if text else []


def _bypasses_filter(candidate: AttackCandidateResult) -> bool:
    meta = candidate.vector.metadata or {}
    if bool(meta.get("bypass_self_interrogation")):
        return True
    if candidate.vector.label.startswith("catalog_seed_"):
        return True
    return _candidate_generation_method(candidate) in _BYPASS_GENERATION_METHODS


def interrogate_candidate(
    candidate: AttackCandidateResult,
    config: dict[str, Any] | None = None,
) -> ConvictionReport:
    """Produce a deterministic conviction report for one evaluated candidate."""
    cfg = {**DEFAULT_SELF_INTERROGATION_CONFIG, **(config or {})}
    metadata = dict(candidate.vector.metadata or {})
    challenges: list[str] = []
    survivors: list[str] = []
    risks: list[str] = []
    assumptions: list[str] = []
    lineage_refs = (
        _string_list(metadata.get("hypothesis_id"))
        + _string_list(metadata.get("parent_ids"))
        + _string_list(metadata.get("lineage"))
    )[:8]

    score = 0.40

    if candidate.rejected:
        challenges.append(f"base gates already rejected: {candidate.rejection_reason or 'unknown'}")
        risks.append("candidate does not currently survive existing deterministic gates")
        score -= 0.22
    else:
        survivors.append("survives existing deterministic gates")
        score += 0.08

    priority = float(metadata.get("priority_score", 0.0) or 0.0)
    novelty = float(metadata.get("novelty_score", 0.0) or 0.0)
    score += 0.08 * _bounded(priority)
    score += 0.05 * _bounded(novelty)
    score += 0.10 * _bounded(candidate.severity_score)
    score += 0.08 * _bounded(candidate.realism_score)
    score += 0.06 * _bounded(candidate.reproducibility)

    min_impact = float(cfg.get("min_impact_usd", 100_000.0) or 0.0)
    if candidate.mean_economic_impact_usd >= min_impact:
        survivors.append("clears configured economic-impact floor")
        score += 0.10
    else:
        challenges.append("economic impact is below configured floor")
        risks.append("may consume validation budget without value-moving output")
        score -= 0.12

    if candidate.invariant_violation_count > 0:
        survivors.append("has at least one invariant violation")
        score += 0.08
    else:
        challenges.append("no invariant violation is currently attached")
        assumptions.append("impact oracle or invariant must be supplied before promotion")
        score -= 0.08

    target_bound = bool(
        candidate.vector.target_id
        or metadata.get("target_slug")
        or metadata.get("target_id")
    )
    if target_bound:
        survivors.append("has a target binding")
        score += 0.06
    else:
        challenges.append("target binding is missing")
        assumptions.append(
            "must bind to a scoped deployed target before fork or validator promotion"
        )
        score -= 0.07

    if _has_source_binding(metadata):
        survivors.append("has source or concrete-candidate binding")
        score += 0.08
    elif target_bound:
        challenges.append("source/entrypoint binding is absent")
        assumptions.append("semantic recon should attach source commit and selector/discriminator")
        score -= 0.05

    if candidate.catalog_analogue or candidate.catalog_exploit_id:
        challenges.append("catalogue analogue risk is high")
        risks.append("must prove this is not only historical replay")
        score -= 0.12

    reproduced = (
        candidate.fork_reproduced
        or candidate.solana_reproduced
        or candidate.foundry_confirmed
    )
    if reproduced:
        survivors.append("has reproduction evidence")
        score += 0.10
    elif cfg.get("stage") == "promotion":
        challenges.append("promotion-stage candidate lacks reproduction evidence")
        score -= 0.18

    if candidate.cpcv_verdict == "DANGER" or candidate.pbo > float(cfg.get("max_pbo", 0.30)):
        challenges.append("overfitting signal is unsafe")
        risks.append("candidate may be fitted to narrow fixtures")
        score -= 0.12
    elif candidate.cpcv_verdict == "SAFE":
        survivors.append("survives CPCV overfitting check")
        score += 0.05

    score = _bounded(score)
    proceed_threshold = float(cfg.get("proceed_threshold", 0.68))
    revise_threshold = float(cfg.get("revise_threshold", 0.45))
    if score >= proceed_threshold:
        action: InterrogationAction = "proceed"
    elif score >= revise_threshold:
        action = "revise"
    elif novelty >= 0.80 and not candidate.rejected:
        action = "escalate"
    else:
        action = "discard"

    return ConvictionReport(
        candidate_label=candidate.vector.label,
        conviction_score=score,
        recommended_action=action,
        adversarial_challenges=challenges[:8],
        surviving_arguments=survivors[:8],
        risks=risks[:8],
        open_assumptions=assumptions[:8],
        lineage_refs=lineage_refs,
    )


def apply_self_interrogation(
    candidates: list[AttackCandidateResult],
    config: dict[str, Any] | None = None,
) -> tuple[list[AttackCandidateResult], InterrogationStats]:
    """Annotate candidates with conviction reports and optionally filter them."""
    cfg = {**DEFAULT_SELF_INTERROGATION_CONFIG, **(config or {})}
    stats = InterrogationStats()
    if not cfg.get("enabled", True):
        return candidates, stats

    top_n = int(cfg.get("top_n", 50) or 0)
    limit = len(candidates) if top_n <= 0 else min(top_n, len(candidates))
    mode = str(cfg.get("mode", "advisory")).lower()
    rank_adjustment = bool(cfg.get("rank_adjustment", False))
    max_adjustment = float(cfg.get("max_rank_adjustment", 0.035) or 0.0)

    for candidate in candidates[:limit]:
        report = interrogate_candidate(candidate, cfg)
        stats.record(report.recommended_action)
        metadata = dict(candidate.vector.metadata or {})
        metadata["self_interrogation"] = report.to_dict()
        metadata["conviction_score"] = report.conviction_score
        metadata["conviction_action"] = report.recommended_action
        candidate.vector.metadata = metadata

        if rank_adjustment and not candidate.rejected and max_adjustment > 0:
            adjustment = (report.conviction_score - 0.5) * 2.0 * max_adjustment
            candidate.severity_score = _bounded(candidate.severity_score + adjustment)
            metadata["self_interrogation_rank_adjustment"] = round(adjustment, 6)
            stats.rank_adjusted += 1

        if (
            mode == "filter"
            and not candidate.rejected
            and not _bypasses_filter(candidate)
            and report.recommended_action in {"discard", "revise"}
        ):
            candidate.rejected = True
            candidate.rejection_reason = f"self_interrogation_{report.recommended_action}"
            stats.filtered += 1

    return candidates, stats
