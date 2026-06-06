"""Hypothesis generation — grid search over attack parameter spaces.

Extracted from RTP grid_combos() pattern.
"""

from itertools import product
from typing import Any

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_templates.base import AttackTemplate


def grid_combos(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generate all combinations from a parameter grid."""
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def generate_attack_vectors(
    template: AttackTemplate,
    target_id: str = "",
    label_prefix: str = "",
) -> list[AttackVector]:
    """Stage 1: generate all attack vector hypotheses from a template's param grid."""
    vectors: list[AttackVector] = []
    for i, params in enumerate(grid_combos(template.param_grid())):
        label = f"{label_prefix}{template.template_id}_{i}" if label_prefix else f"{template.template_id}_{i}"
        vectors.append(
            AttackVector(
                template_id=template.template_id,
                parameters=params,
                target_id=target_id,
                label=label,
            )
        )
    return vectors