"""Stage 2: validate attack vectors against historical exploit ground truth."""

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.hypothesis import generate_attack_vectors
from night_shift_security.core.scoring import severity_weight
from night_shift_security.data.schemas import AttackCandidateResult, AttackVector, ExploitRecord
from night_shift_security.domain.attack_templates.base import get_template


def _params_match(found: dict, known: dict, tolerance: float = 5.0) -> bool:
    """Check if discovered parameters match known exploit parameters."""
    for key, known_val in known.items():
        found_val = found.get(key)
        if found_val is None:
            return False
        if isinstance(known_val, bool):
            if found_val != known_val:
                return False
        elif isinstance(known_val, (int, float)):
            if abs(float(found_val) - float(known_val)) > tolerance:
                return False
        elif found_val != known_val:
            return False
    return True


def replay_against_exploit(
    vector: AttackVector,
    exploit: ExploitRecord,
) -> bool:
    """Test whether a vector succeeds on a specific historical exploit state."""
    template = get_template(vector.template_id)
    if vector.template_id != exploit.template_id:
        return False
    result = template.execute(exploit.state, vector.parameters)
    return result.success and result.severity.value in ("high", "critical")


def run_rediscovery_test(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
) -> dict:
    """
    Check how many known exploits were rediscovered by passing candidates.

    A rediscovery requires:
    1. Attack succeeds on the historical state
    2. Parameters approximately match known exploit parameters
    """
    rediscovered: list[str] = []
    rediscovery_map: dict[str, str] = {}

    passing = [c for c in candidates if not c.rejected]

    for exploit in catalog:
        for cand in passing:
            if replay_against_exploit(cand.vector, exploit):
                if _params_match(cand.vector.parameters, exploit.known_parameters):
                    if exploit.exploit_id not in rediscovered:
                        rediscovered.append(exploit.exploit_id)
                        rediscovery_map[str(cand.vector.key())] = exploit.exploit_id
                    cand.replay_matches += 1
            cand.replay_total += 1

    # Also test all vectors (including rejected) for raw rediscovery signal
    raw_rediscovered = []
    for exploit in catalog:
        for cand in candidates:
            if replay_against_exploit(cand.vector, exploit):
                if _params_match(cand.vector.parameters, exploit.known_parameters):
                    if exploit.exploit_id not in raw_rediscovered:
                        raw_rediscovered.append(exploit.exploit_id)

    return {
        "catalog_size": len(catalog),
        "rediscovered": len(rediscovered),
        "rediscovered_ids": rediscovered,
        "raw_rediscovered": len(raw_rediscovered),
        "raw_rediscovered_ids": raw_rediscovered,
        "rate": len(rediscovered) / len(catalog) if catalog else 0.0,
        "rediscovery_map": rediscovery_map,
    }


def evaluate_catalog_directly(catalog: list[ExploitRecord]) -> list[AttackCandidateResult]:
    """Evaluate known exploit parameters directly — sanity check that catalog is valid."""
    results: list[AttackCandidateResult] = []
    for exploit in catalog:
        vector = AttackVector(
            template_id=exploit.template_id,
            parameters=exploit.known_parameters,
            target_id=exploit.state.protocol_id,
            label=f"ground_truth_{exploit.exploit_id}",
        )
        cand = evaluate_attack_vector(vector, [exploit.state])
        results.append(cand)
    return results