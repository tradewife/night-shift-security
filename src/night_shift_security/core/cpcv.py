"""Combinatorial Purged Cross-Validation + PBO — ported from RTP robustness.py.

Adapted for security: temporal splits on historical exploits detect
attack-parameter overfitting (discovering params that work in-sample
on older incidents but fail on held-out newer ones).
"""

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

import numpy as np

from night_shift_security.data.schemas import AttackVector, ContractState, ExploitRecord
from night_shift_security.domain.attack_templates.base import get_template


@dataclass
class TemporalFold:
    """One temporal train/test split over exploit records."""

    fold_num: int
    train_exploit_ids: list[str]
    test_exploit_ids: list[str]
    train_years: list[int]
    test_years: list[int]


@dataclass
class CPCVResult:
    """Result of CPCV + PBO analysis."""

    n_folds: int
    n_test_folds: int
    n_paths: int
    pbo: float
    logits: list[float] = field(default_factory=list)
    oos_scores: list[float] = field(default_factory=list)
    is_scores: list[float] = field(default_factory=list)
    path_results: list[dict] = field(default_factory=list)


def create_temporal_folds(
    exploits: list[ExploitRecord],
    n_folds: int = 4,
) -> list[TemporalFold]:
    """
    Split exploit catalog into temporal folds ordered by year.

    Each fold's test set is one year-group; train is all prior years.
    """
    sorted_exploits = sorted(exploits, key=lambda e: (e.year, e.exploit_id))
    years = sorted({e.year for e in sorted_exploits})
    if len(years) < 2:
        mid = len(sorted_exploits) // 2
        return [
            TemporalFold(
                fold_num=0,
                train_exploit_ids=[e.exploit_id for e in sorted_exploits[:mid]],
                test_exploit_ids=[e.exploit_id for e in sorted_exploits[mid:]],
                train_years=years[:1] if years else [],
                test_years=years[1:] if len(years) > 1 else years,
            )
        ]

    folds: list[TemporalFold] = []
    for i, test_year in enumerate(years[1:], start=1):
        train_ids = [e.exploit_id for e in sorted_exploits if e.year < test_year]
        test_ids = [e.exploit_id for e in sorted_exploits if e.year == test_year]
        if not train_ids or not test_ids:
            continue
        folds.append(
            TemporalFold(
                fold_num=i - 1,
                train_exploit_ids=train_ids,
                test_exploit_ids=test_ids,
                train_years=sorted({e.year for e in sorted_exploits if e.year < test_year}),
                test_years=[test_year],
            )
        )

    return folds[:n_folds] if folds else []


def _attack_score(vector: AttackVector, exploit: ExploitRecord) -> float:
    """Fitness score for one attack vector on one exploit (higher = more dangerous)."""
    if vector.template_id != exploit.template_id:
        return 0.0
    template = get_template(vector.template_id)
    result = template.execute(exploit.state, vector.parameters)
    if not result.success:
        return 0.0
    severity_weight = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
    sw = severity_weight.get(result.severity.value, 0.5)
    impact_factor = min(result.economic_impact_usd / 1_000_000, 10.0) / 10.0
    return sw * impact_factor


def _evaluate_params_on_exploits(
    params: dict[str, Any],
    template_id: str,
    exploit_ids: list[str],
    exploit_map: dict[str, ExploitRecord],
) -> float:
    vector = AttackVector(template_id=template_id, parameters=params)
    scores = [
        _attack_score(vector, exploit_map[eid])
        for eid in exploit_ids
        if eid in exploit_map
    ]
    return float(np.median(scores)) if scores else 0.0


def generate_param_variants(
    base_params: dict[str, Any],
    n_variants: int = 15,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Generate parameter variants around a base config for CPCV grid."""
    rng = np.random.default_rng(seed)
    variants = [dict(base_params)]
    numeric_keys = [k for k, v in base_params.items() if isinstance(v, (int, float))]

    for _ in range(n_variants - 1):
        variant = dict(base_params)
        if not numeric_keys:
            variants.append(variant)
            continue
        n_perturb = rng.integers(1, min(3, len(numeric_keys) + 1))
        keys = rng.choice(numeric_keys, size=n_perturb, replace=False)
        for key in keys:
            delta = rng.uniform(0.08, 0.20) * rng.choice([-1, 1])
            original = variant[key]
            if isinstance(original, int):
                variant[key] = max(1, int(original * (1 + delta)))
            else:
                variant[key] = max(0.01, round(original * (1 + delta), 4))
        variants.append(variant)

    return variants


def cpcv_attack_params(
    exploits: list[ExploitRecord],
    params_grid: list[dict[str, Any]],
    template_id: str,
    n_test_folds: int = 2,
) -> CPCVResult:
    """
    CPCV over temporal exploit folds.

    For each combinatorial test-fold combination:
    1. Find best IS params on train exploits
    2. Rank those params OOS on test exploits
    3. Compute logit; PBO = fraction of negative logits
    """
    folds = create_temporal_folds(exploits)
    exploit_map = {e.exploit_id: e for e in exploits}

    if len(folds) < n_test_folds:
        # Not enough temporal diversity to evaluate overfitting.
        # Return pbo=0 (no signal) rather than pbo=1.0 (false danger).
        return CPCVResult(
            n_folds=len(folds),
            n_test_folds=n_test_folds,
            n_paths=0,
            pbo=0.0,
        )

    fold_indices = list(range(len(folds)))
    test_combos = list(combinations(fold_indices, min(n_test_folds, len(folds))))

    logits: list[float] = []
    oos_scores: list[float] = []
    is_scores: list[float] = []
    path_results: list[dict] = []

    for path_idx, test_indices in enumerate(test_combos):
        train_indices = [i for i in fold_indices if i not in test_indices]

        train_ids: list[str] = []
        test_ids: list[str] = []
        for ti in train_indices:
            train_ids.extend(folds[ti].train_exploit_ids + folds[ti].test_exploit_ids)
        for ti in test_indices:
            test_ids.extend(folds[ti].test_exploit_ids)

        train_ids = list(dict.fromkeys(train_ids))
        test_ids = list(dict.fromkeys(test_ids))

        best_is_score = -1.0
        best_params: dict[str, Any] | None = None
        for params in params_grid:
            is_score = _evaluate_params_on_exploits(params, template_id, train_ids, exploit_map)
            if is_score > best_is_score:
                best_is_score = is_score
                best_params = params

        if best_params is None:
            logits.append(-5.0)
            continue

        oos_score = _evaluate_params_on_exploits(best_params, template_id, test_ids, exploit_map)

        all_test_scores = [
            _evaluate_params_on_exploits(p, template_id, test_ids, exploit_map)
            for p in params_grid
        ]
        rank = sum(1 for s in all_test_scores if s <= oos_score)
        n_params = len(all_test_scores)
        denominator = n_params - rank + 1
        logit = float(np.log(rank / denominator)) if denominator > 0 and rank > 0 else -5.0

        logits.append(round(logit, 4))
        oos_scores.append(round(oos_score, 4))
        is_scores.append(round(best_is_score, 4))
        path_results.append({
            "path": path_idx,
            "test_folds": list(test_indices),
            "train_folds": train_indices,
            "best_is_score": round(best_is_score, 4),
            "oos_score": round(oos_score, 4),
            "rank": rank,
            "n_params": n_params,
            "logit": round(logit, 4),
        })

    n_negative = sum(1 for l in logits if l < 0)
    pbo = n_negative / len(logits) if logits else 1.0

    return CPCVResult(
        n_folds=len(folds),
        n_test_folds=n_test_folds,
        n_paths=len(test_combos),
        pbo=round(pbo, 4),
        logits=logits,
        oos_scores=oos_scores,
        is_scores=is_scores,
        path_results=path_results,
    )


def pbo_verdict(pbo: float) -> str:
    if pbo < 0.15:
        return "SAFE"
    if pbo < 0.30:
        return "ELEVATED"
    return "DANGER"