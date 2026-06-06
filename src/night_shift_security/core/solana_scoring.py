"""Solana reproduction scoring bonus — confidence multiplier, not a gate."""

from night_shift_security.data.schemas import AttackCandidateResult


def solana_score_multiplier(solana_reproduced: bool, config: dict) -> float:
    if not solana_reproduced:
        return 1.0
    return float(config.get("score_multiplier", 1.10))


def reproduction_multiplier(cand: AttackCandidateResult, solana_cfg: dict, fork_cfg: dict) -> float:
    """Pick the stronger single multiplier when both EVM and Solana reproduction apply."""
    fork_mult = float(fork_cfg.get("score_multiplier", 1.20)) if cand.fork_reproduced else 1.0
    solana_mult = solana_score_multiplier(cand.solana_reproduced, solana_cfg)
    return max(fork_mult, solana_mult)


def _ranked_passing(candidates: list[AttackCandidateResult]) -> list[AttackCandidateResult]:
    passing = [c for c in candidates if not c.rejected]
    return sorted(passing, key=lambda c: c.severity_score, reverse=True)


def _rank_index(candidates: list[AttackCandidateResult]) -> dict[str, int]:
    return {str(c.vector.key()): i for i, c in enumerate(_ranked_passing(candidates))}


def apply_solana_scoring_bonus(
    candidates: list[AttackCandidateResult],
    config: dict,
    fork_config: dict | None = None,
) -> dict:
    """
    Apply post-hoc severity bonus to solana-reproduced catalog anchors.

    Does not stack with fork bonus — uses max(EVM, Solana) multiplier on the same base.
    """
    if not config.get("enabled", True):
        return {"adjusted": 0, "rank_changes": [], "score_only_bumps": []}

    fork_config = fork_config or {}
    pre_rank = _rank_index(candidates)
    adjusted = 0
    score_only: list[str] = []

    for cand in candidates:
        if not cand.solana_reproduced:
            continue

        base = cand.severity_score_base if cand.severity_score_base > 0 else cand.severity_score
        if cand.severity_score_base == 0:
            cand.severity_score_base = base

        multiplier = reproduction_multiplier(cand, config, fork_config)
        cand.severity_score = min(base * multiplier, 1.0)
        adjusted += 1

    post_rank = _rank_index(candidates)
    rank_changes: list[dict] = []

    for cand in candidates:
        if not cand.solana_reproduced:
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
                "multiplier": reproduction_multiplier(cand, config, fork_config),
            })
        else:
            score_only.append(label)

    return {
        "adjusted": adjusted,
        "rank_changes": rank_changes,
        "score_only_bumps": score_only,
        "score_multiplier": config.get("score_multiplier", 1.10),
    }