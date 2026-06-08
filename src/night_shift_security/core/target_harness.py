"""Live-target harness — scope hypothesis generation to a specific protocol."""

from __future__ import annotations

from typing import Any

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.hypothesis import (
    generate_attack_vectors,
    generate_llm_expanded_attack_vectors,
    generate_sampled_attack_vectors,
    resolve_sample_count,
)
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector, ExploitRecord
from night_shift_security.data.target_config import LiveTarget, resolve_target_states, scoped_template_ids
from night_shift_security.domain.attack_hypotheses.structural_filters import apply_structural_filters
from night_shift_security.domain.attack_templates.base import get_template


def generate_target_vectors(
    target: LiveTarget,
    config: dict[str, Any],
    *,
    llm_cfg: dict[str, Any] | None = None,
) -> list[AttackVector]:
    """Generate attack vectors scoped to a live target."""
    hypothesis_cfg = config.get("hypothesis_generation", {})
    llm_cfg = llm_cfg or config.get("llm_expansion", {})
    samples_per_template = int(hypothesis_cfg.get("samples_per_template", 20))
    sample_fraction = hypothesis_cfg.get("sample_fraction_of_grid")
    grid_enabled = hypothesis_cfg.get("grid_enabled", True)
    filter_cfg = hypothesis_cfg.get("structural_filters", {})

    vectors: list[AttackVector] = []
    for template_id in scoped_template_ids(target, config):
        template = get_template(template_id)
        if template is None:
            continue

        grid_vectors = (
            generate_attack_vectors(template, target_id=target.target_id, label_prefix=f"{target.target_id}_")
            if grid_enabled
            else []
        )
        template_vectors = list(grid_vectors)

        if hypothesis_cfg.get("enabled", True):
            sample_count = resolve_sample_count(
                len(grid_vectors) if grid_vectors else samples_per_template,
                samples_per_template,
                sample_fraction,
            )
            sampled = generate_sampled_attack_vectors(
                template_id,
                sample_count,
                target_id=target.target_id,
                label_prefix=f"{target.target_id}_hyp_",
            )
            template_vectors.extend(sampled)

            if llm_cfg.get("enabled", False):
                max_seeds = int(llm_cfg.get("max_seeds", 5))
                variants_per_seed = int(llm_cfg.get("variants_per_seed", 2))
                llm_vectors = generate_llm_expanded_attack_vectors(
                    template_id,
                    sampled[:max_seeds],
                    variants_per_seed=variants_per_seed,
                    enabled=True,
                    fallback=str(llm_cfg.get("fallback", "parametric")),
                    provider_config=llm_cfg,
                )
                for vector in llm_vectors:
                    vector.target_id = target.target_id
                template_vectors.extend(llm_vectors)

        filtered, _ = apply_structural_filters(template_vectors, filter_cfg)
        for vector in filtered:
            vector.target_id = target.target_id
            vector.metadata.setdefault("live_target_id", target.target_id)
            if target.exploit_id:
                vector.metadata.setdefault("catalog_exploit_id", target.exploit_id)
        vectors.extend(filtered)

    return vectors


def evaluate_target_vectors(
    target: LiveTarget,
    vectors: list[AttackVector],
    gates,
    catalog: list[ExploitRecord] | None = None,
) -> list[AttackCandidateResult]:
    """Evaluate vectors against target-specific contract states."""
    states = resolve_target_states(target, catalog)
    candidates: list[AttackCandidateResult] = []
    for vector in vectors:
        cand = evaluate_attack_vector(vector, states, gate=gates)
        if target.exploit_id:
            cand.catalog_exploit_id = target.exploit_id
        candidates.append(cand)
    return candidates