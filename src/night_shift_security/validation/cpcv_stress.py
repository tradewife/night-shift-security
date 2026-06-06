"""Stage 4b: CPCV + PBO overfitting detection on attack parameters."""

from night_shift_security.core.cpcv import cpcv_attack_params, generate_param_variants, pbo_verdict
from night_shift_security.data.schemas import AttackCandidateResult, ExploitRecord


def run_cpcv_phase(
    candidates: list[AttackCandidateResult],
    catalog: list[ExploitRecord],
    config: dict,
) -> dict[str, dict]:
    """
    Run CPCV/PBO on top candidates per template.

    Rejects candidates where PBO exceeds threshold (likely overfit to
    older exploit patterns).
    """
    top_n = config.get("top_n", 5)
    n_variants = config.get("n_variants", 15)
    n_test_folds = config.get("n_test_folds", 2)
    max_pbo = config.get("max_pbo", 0.30)

    passing = [c for c in candidates if not c.rejected]
    results: dict[str, dict] = {}

    by_template: dict[str, list[AttackCandidateResult]] = {}
    for cand in passing:
        by_template.setdefault(cand.vector.template_id, []).append(cand)

    for template_id, template_cands in by_template.items():
        top = sorted(template_cands, key=lambda c: c.severity_score, reverse=True)[:top_n]
        template_exploits = [e for e in catalog if e.template_id == template_id]
        if len(template_exploits) < 2:
            continue

        for cand in top:
            params_grid = generate_param_variants(cand.vector.parameters, n_variants=n_variants)
            cpcv = cpcv_attack_params(
                template_exploits,
                params_grid,
                template_id,
                n_test_folds=n_test_folds,
            )

            key = str(cand.vector.key())
            verdict = pbo_verdict(cpcv.pbo)
            results[key] = {
                "pbo": cpcv.pbo,
                "verdict": verdict,
                "n_paths": cpcv.n_paths,
                "logit_mean": round(sum(cpcv.logits) / len(cpcv.logits), 4) if cpcv.logits else 0,
            }

            cand.pbo = cpcv.pbo
            cand.cpcv_verdict = verdict

            if cpcv.pbo > max_pbo:
                cand.rejected = True
                cand.rejection_reason = f"pbo={cpcv.pbo:.0%} > {max_pbo:.0%} ({verdict})"

    return results