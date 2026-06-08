"""
WFA (Walk-Forward Analysis) integration for Night Shift Security Validation Layer.

Wires the domain-agnostic research/engine/validation.py harness into the
existing structural filter + validation pipeline.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

from night_shift_security.data.schemas import AttackVector
from research.engine.validation import (
    CandidateResult,
    DarwinianConfig,
    FoldEvaluator,
    FoldOutcome,
    OverfittingConfig,
    WFAConfig,
    create_folds,
    darwinian_evolution,
    evaluate_candidate,
    run_coarse_screen,
    run_fine_refinement,
)


def make_security_fold_evaluator(
    simulator: Callable[[Any, Any, dict], FoldOutcome]
) -> FoldEvaluator:
    """Wrap a security simulation function into the FoldEvaluator Protocol."""
    def evaluator(data: Any, fold: Any, params: dict) -> FoldOutcome:
        return simulator(data, fold, params)
    return evaluator


def apply_wfa_validation_to_attack_vectors(
    vectors: List[AttackVector],
    simulator: Callable[[Any, Any, dict], FoldOutcome],
    data: Any,
    wfa_config: Optional[WFAConfig] = None,
    overfitting_config: Optional[OverfittingConfig] = None,
    darwinian_config: Optional[DarwinianConfig] = None,
) -> tuple[List[CandidateResult], dict[str, Any]]:
    """
    Run full WFA + Darwinian survivor selection on attack vectors that have
    already passed structural_filters.

    This is the recommended integration point after apply_structural_filters().
    """
    cfg = wfa_config or WFAConfig()
    of_cfg = overfitting_config or OverfittingConfig()
    d_cfg = darwinian_config or DarwinianConfig()

    evaluator = make_security_fold_evaluator(simulator)

    folds = create_folds(
        total_bars=len(data) if hasattr(data, "__len__") else 10_000,
        num_folds=cfg.num_folds,
        test_fold_bars=cfg.test_fold_bars,
        warmup_bars=cfg.warmup_bars,
    )

    # Convert AttackVector list to param grid style for coarse screen
    param_grid = {"vector": [v.parameters for v in vectors]}

    coarse = run_coarse_screen(
        data, param_grid, evaluator, of_cfg, screen_window_bars=720
    )

    top = sorted([c for c in coarse if not c.rejected],
                 key=lambda r: r.survivor_score, reverse=True)[:80]

    fine = run_fine_refinement(
        data, folds, top, {}, evaluator, of_cfg, compute_fragility=True
    )

    survivors = darwinian_evolution(
        data, folds, fine, evaluator, d_cfg, of_cfg
    )

    stats = {
        "input_vectors": len(vectors),
        "coarse_candidates": len(coarse),
        "fine_candidates": len(fine),
        "final_survivors": len(survivors),
    }

    return survivors, stats
