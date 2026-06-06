"""Catalog seed vectors — ground-truth exploit parameters in the search pool."""

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector, ExploitRecord
from night_shift_security.validation.historical_replay import _params_match


def catalog_seed_vectors(catalog: list[ExploitRecord]) -> list[AttackVector]:
    """Generate attack vectors from known exploit parameters (Stage 1 seeds)."""
    vectors: list[AttackVector] = []
    for exploit in catalog:
        vectors.append(
            AttackVector(
                template_id=exploit.template_id,
                parameters=dict(exploit.known_parameters),
                target_id=exploit.state.protocol_id,
                label=f"catalog_seed_{exploit.exploit_id}",
            )
        )
    return vectors


def evaluate_catalog_seeds(
    catalog: list[ExploitRecord],
    gates,
) -> list[AttackCandidateResult]:
    """Evaluate catalog seeds against their historical states."""
    candidates: list[AttackCandidateResult] = []
    for exploit in catalog:
        vector = AttackVector(
            template_id=exploit.template_id,
            parameters=dict(exploit.known_parameters),
            target_id=exploit.state.protocol_id,
            label=f"catalog_seed_{exploit.exploit_id}",
        )
        cand = evaluate_attack_vector(vector, [exploit.state], gate=gates)
        cand.catalog_exploit_id = exploit.exploit_id
        candidates.append(cand)
    return candidates


def is_catalog_anchor(candidate: AttackCandidateResult, catalog: list[ExploitRecord]) -> bool:
    """True if candidate exactly matches a catalog exploit's known parameters."""
    if candidate.catalog_exploit_id:
        return True
    for exploit in catalog:
        if exploit.template_id != candidate.vector.template_id:
            continue
        if _params_match(candidate.vector.parameters, exploit.known_parameters, tolerance=0.0):
            return True
    return False