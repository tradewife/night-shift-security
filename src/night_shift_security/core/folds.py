"""Temporal splitting for walk-forward validation.

Extracted from RTP research/orchestration/night_shift.py — domain-agnostic.
"""

from dataclasses import dataclass


@dataclass
class Fold:
    """One train/test temporal split."""

    fold_num: int
    train_start_idx: int
    train_end_idx: int
    test_start_idx: int
    test_end_idx: int
    train_size: int
    test_size: int


def create_folds(
    total_items: int,
    num_folds: int,
    test_fold_size: int,
    warmup: int = 0,
) -> list[Fold]:
    """
    Create non-overlapping expanding-window folds.

    Every item appears in exactly one test fold. Train window expands over time.
    """
    if total_items <= warmup + test_fold_size:
        return [
            Fold(
                fold_num=0,
                train_start_idx=0,
                train_end_idx=warmup,
                test_start_idx=warmup,
                test_end_idx=total_items,
                train_size=warmup,
                test_size=total_items - warmup,
            )
        ]

    usable = total_items - warmup
    max_folds = usable // test_fold_size
    actual_folds = min(num_folds, max_folds)
    if actual_folds < 1:
        actual_folds = 1

    if actual_folds < max_folds:
        items_per_fold = test_fold_size
    else:
        items_per_fold = usable // actual_folds

    folds: list[Fold] = []
    test_start = warmup
    for i in range(actual_folds):
        test_end = test_start + items_per_fold if i < actual_folds - 1 else total_items
        folds.append(
            Fold(
                fold_num=i,
                train_start_idx=0,
                train_end_idx=test_start,
                test_start_idx=test_start,
                test_end_idx=test_end,
                train_size=test_start,
                test_size=test_end - test_start,
            )
        )
        test_start = test_end

    return folds