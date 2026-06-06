"""5-stage security research pipeline — adapted from RTP run_night_shift()."""

import time
from pathlib import Path

from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.evaluation import evaluate_attack_vector, rank_candidates
from night_shift_security.core.evolution import darwinian_evolution
from night_shift_security.core.hypothesis import generate_attack_vectors
from night_shift_security.core.results import findings_from_candidates, write_report
from night_shift_security.data.exploit_catalog import catalog_states, get_exploit_catalog
from night_shift_security.domain.attack_templates.base import get_template
from night_shift_security.validation.historical_replay import (
    evaluate_catalog_directly,
    run_rediscovery_test,
)

# Register all attack templates
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401


def log(msg: str) -> None:
    print(msg, flush=True)


def run_security_pipeline(config_path: Path | None = None) -> dict:
    """
    Security research pipeline:

    Stage 1: Hypothesis generation (attack parameter grids)
    Stage 2: Historical exploit validation / rediscovery
    Stage 3: Darwinian evolution of attack strategies
    Stage 4: Security gate enforcement
    → Findings report
    """
    start = time.time()
    config = load_config(config_path)
    gates = gates_from_config(config)
    output_dir = Path(config.get("output_dir", "data/security_results"))
    darwinian_cfg = config.get("darwinian", {})

    log("=" * 70)
    log("NIGHT SHIFT SECURITY — Adversarial Research Pipeline")
    log("=" * 70)

    catalog = get_exploit_catalog()
    states = catalog_states()

    # Stage 0: Sanity check ground truth
    log("\n── Stage 0: Ground Truth Sanity Check ──")
    ground_truth = evaluate_catalog_directly(catalog)
    gt_pass = sum(1 for c in ground_truth if not c.rejected)
    log(f"  {gt_pass}/{len(ground_truth)} known exploits pass gates with exact parameters")

    # Stage 1: Hypothesis generation
    log("\n── Stage 1: Attack Vector Generation ──")
    candidates = []
    for template_id in config.get("templates", ["governance_capture"]):
        template = get_template(template_id)
        vectors = generate_attack_vectors(template)
        log(f"  {template_id}: {len(vectors)} vectors from param grid")
        for vector in vectors:
            candidates.append(evaluate_attack_vector(vector, states, gate=gates))

    log(f"  Total hypotheses evaluated: {len(candidates)}")
    grid_passed = sum(1 for c in candidates if not c.rejected)
    log(f"  Passed gates after grid search: {grid_passed}")

    # Stage 3: Darwinian evolution
    if darwinian_cfg.get("enabled", True):
        log("\n── Stage 3: Darwinian Evolution ──")
        evolved = darwinian_evolution(candidates, states, gates=gates, config=darwinian_cfg)
        candidates.extend(evolved)
        log(f"  Evolved candidates: {len(evolved)}")
        log(f"  Total candidates after evolution: {len(candidates)}")
    else:
        log("\n── Stage 3: Darwinian Evolution (disabled) ──")

    candidates = rank_candidates(candidates)
    passed = [c for c in candidates if not c.rejected]
    log(f"\n── Stage 2/4: Validation Summary ──")
    log(f"  Total candidates: {len(candidates)}")
    log(f"  Passed gates: {len(passed)}")

    # Stage 2b: Rediscovery test
    log("\n── Stage 2b: Rediscovery Test ──")
    rediscovery = run_rediscovery_test(candidates, catalog)
    log(f"  Catalog size: {rediscovery['catalog_size']}")
    log(f"  Rediscovered (gated): {rediscovery['rediscovered']}/{rediscovery['catalog_size']}")
    log(f"  Rediscovered (raw): {rediscovery['raw_rediscovered']}/{rediscovery['catalog_size']}")
    if rediscovery["rediscovered_ids"]:
        log(f"  IDs: {', '.join(rediscovery['rediscovered_ids'])}")

    # Top candidates
    log("\n── Top Candidates ──")
    for c in candidates[:8]:
        status = "PASS" if not c.rejected else "REJECT"
        log(
            f"  [{status}] {c.vector.label}: severity={c.severity_score:.3f} "
            f"impact=${c.mean_economic_impact_usd:,.0f}"
        )

    # Output
    log("\n── Report Generation ──")
    findings = findings_from_candidates(passed, rediscovery.get("rediscovery_map"))
    elapsed = time.time() - start
    md_path, json_path = write_report(findings, candidates, output_dir, elapsed, rediscovery)

    log(f"\n{'=' * 70}")
    log(f"NIGHT SHIFT SECURITY COMPLETE — {elapsed:.0f}s")
    log(f"  Findings: {len(findings)}")
    log(f"  Report: {md_path}")
    log(f"  JSON: {json_path}")
    log(f"{'=' * 70}")

    return {
        "findings": len(findings),
        "candidates_evaluated": len(candidates),
        "candidates_passed": len(passed),
        "rediscovery": rediscovery,
        "report_md": str(md_path),
        "report_json": str(json_path),
        "elapsed_seconds": elapsed,
    }