"""Hypothesis generation — grid search and parameterized sampling.

Extracted from RTP grid_combos() pattern; extended with attack_hypotheses layer.
"""

from itertools import product
from typing import Any

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses import (
    get_generator,
    hypothesis_to_attack_vector,
)
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


def generate_sampled_attack_vectors(
    template_id: str,
    n: int,
    target_id: str = "",
    label_prefix: str = "hyp_",
) -> list[AttackVector]:
    """Stage 1 expansion: sample parameterized hypotheses via HypothesisGenerator."""
    generator = get_generator(template_id)
    if generator is None or n <= 0:
        return []

    vectors: list[AttackVector] = []
    for i, hypothesis in enumerate(generator.sample(n)):
        label = f"{label_prefix}{template_id}_{i}"
        vectors.append(hypothesis_to_attack_vector(hypothesis, target_id=target_id, label=label))
    return vectors


def resolve_sample_count(
    grid_size: int,
    samples_per_template: int,
    sample_fraction_of_grid: float | None,
) -> int:
    """Resolve sampled vector count from absolute or grid-relative config."""
    if sample_fraction_of_grid is not None:
        return max(1, int(grid_size * float(sample_fraction_of_grid)))
    return samples_per_template


def generate_llm_expanded_attack_vectors(
    template_id: str,
    seeds: list[AttackVector],
    variants_per_seed: int,
    enabled: bool = False,
    fallback: str = "parametric",
) -> list[AttackVector]:
    """Stage 1 LLM expansion: untrusted proposals validated before pipeline handoff."""
    from night_shift_security.domain.attack_hypotheses import (
        LLMExpansionOrchestrator,
        attack_vector_to_hypothesis,
        hypothesis_to_attack_vector,
        validate_hypothesis,
    )

    if variants_per_seed <= 0 or not seeds:
        return []

    orchestrator = LLMExpansionOrchestrator(enabled=enabled, fallback=fallback)
    vectors: list[AttackVector] = []
    for seed_idx, seed_vector in enumerate(seeds):
        seed_hypothesis = attack_vector_to_hypothesis(
            seed_vector,
            generation_method="llm_seed",
        )
        for variant_idx, proposal in enumerate(
            orchestrator.propose_variants(seed_hypothesis, n=variants_per_seed)
        ):
            ok, _ = validate_hypothesis(proposal)
            if not ok:
                continue
            label = f"llm_{template_id}_{seed_idx}_{variant_idx}"
            vectors.append(
                hypothesis_to_attack_vector(proposal, target_id=seed_vector.target_id, label=label)
            )
    return vectors