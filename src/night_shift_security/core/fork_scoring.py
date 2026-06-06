"""Fork reproduction scoring bonus — confidence multiplier, not a gate."""

from night_shift_security.data.schemas import AttackCandidateResult


def fork_score_multiplier(fork_reproduced: bool, config: dict) -> float:
    if not fork_reproduced:
        return 1.0
    return float(config.get("score_multiplier", 1.20))


def _ranked_passing(candidates: list[AttackCandidateResult]) -> list[AttackCandidateResult]:
    passing = [c for c in candidates if not c.rejected]
    return sorted(passing, key=lambda c: c.severity_score, reverse=True)


def _rank_index(candidates: list[AttackCandidateResult]) -> dict[str, int]:
    return {str(c.vector.key()): i for i, c in enumerate(_ranked_passing(candidates))}


def apply_fork_scoring_bonus(
    candidates: list[AttackCandidateResult],
    config: dict,
) -> dict:
    """
    Apply post-hoc severity bonus to fork-reproduced catalog anchors.

    Returns audit metadata including rank movements among passing candidates.
    """
    if not config.get("enabled", True):
        return {"adjusted": 0, "rank_changes": [], "score_only_bumps": []}

    pre_rank = _rank_index(candidates)
    adjusted = 0
    score_only: list[str] = []

    for cand in candidates:
        if not cand.fork_reproduced:
            continue
        base = cand.severity_score
        cand.severity_score_base = base
        multiplier = fork_score_multiplier(True, config)
        cand.severity_score = min(base * multiplier, 1.0)
        adjusted += 1

    post_rank = _rank_index(candidates)
    rank_changes: list[dict] = []

    for cand in candidates:
        if not cand.fork_reproduced:
            continue
        key = str(cand.vector.key())
        before = pre_rank.get(key)
        after = post_rank.get(key)
        if before is None or after is None:
            continue
        label = cand.vector.label or key
        if after < before:
            rank_changes.append({
                "label": label,
                "exploit_id": cand.catalog_exploit_id,
                "rank_before": before + 1,
                "rank_after": after + 1,
                "severity_score_base": round(cand.severity_score_base, 4),
                "severity_score": round(cand.severity_score, 4),
            })
        else:
            score_only.append(label)

    return {
        "adjusted": adjusted,
        "rank_changes": rank_changes,
        "score_only_bumps": score_only,
        "score_multiplier": config.get("score_multiplier", 1.20),
    }