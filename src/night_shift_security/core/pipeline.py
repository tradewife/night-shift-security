"""5-stage security research pipeline — adapted from RTP run_night_shift()."""

import time
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.config.loader import gates_from_config, load_config
from night_shift_security.core.evaluation import evaluate_attack_vector, rank_candidates
from night_shift_security.core.fork_scoring import apply_fork_scoring_bonus
from night_shift_security.core.solana_scoring import apply_solana_scoring_bonus
from night_shift_security.core.evolution import darwinian_evolution
from night_shift_security.core.hypothesis import (
    generate_attack_vectors,
    generate_llm_expanded_attack_vectors,
    generate_sampled_attack_vectors,
    resolve_sample_count,
)
from night_shift_security.domain.attack_hypotheses import list_generators, validate_hypothesis
from night_shift_security.domain.attack_hypotheses.structural_filters import apply_structural_filters
from night_shift_security.knowledge.findings_store import record_run
import night_shift_security.domain.attack_hypotheses  # noqa: F401 — register generators
from night_shift_security.core.results import findings_from_candidates, write_report
from night_shift_security.export.deduper import dedupe_findings, log_dedupe_report
from night_shift_security.data.exploit_catalog import catalog_states, get_exploit_catalog
from night_shift_security.domain.attack_templates.base import get_template
from night_shift_security.validation.cpcv_stress import run_cpcv_phase
from night_shift_security.bounty.pipeline import export_bounty_artifacts
from night_shift_security.core.target_harness import evaluate_target_vectors, generate_target_vectors
from night_shift_security.data.target_config import load_live_target, target_fork_ids, target_summary
from night_shift_security.monitoring.hooks import emit_monitoring_event
from night_shift_security.validation.fork_validation import run_fork_validation_phase
from night_shift_security.validation.rpc import rpc_status
from night_shift_security.validation.solana_validation import run_solana_validation_phase
from night_shift_security.validation.solana_rpc import solana_status
from night_shift_security.validation.foundry_validation import run_foundry_phase
from night_shift_security.validation.catalog_seeds import evaluate_catalog_seeds
from night_shift_security.validation.historical_replay import (
    evaluate_catalog_directly,
    run_rediscovery_test,
)
from night_shift_security.validation.monte_carlo_stress import run_monte_carlo_phase
from night_shift_security.validation.validation_layer import refresh_validation_batch
from night_shift_security.export.novel_vectors import export_novel_vector_catalog
from night_shift_security.eval.llm_quality import run_llm_quality_eval

# Register all attack templates
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401


def log(msg: str) -> None:
    print(msg, flush=True)


def run_security_pipeline(
    config_path: Path | None = None,
    *,
    proposals_path: Path | None = None,
) -> dict:
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
    if proposals_path is not None:
        llm_override = dict(config.get("llm_expansion", {}))
        llm_override["enabled"] = True
        llm_override["provider"] = "external"
        llm_override["proposals_path"] = str(proposals_path)
        llm_override.setdefault("fallback", "parametric")
        config["llm_expansion"] = llm_override
    gates = gates_from_config(config)
    output_dir = Path(config.get("output_dir", "data/security_results"))
    darwinian_cfg = config.get("darwinian", {})
    hypothesis_cfg = config.get("hypothesis_generation", {})
    llm_cfg = config.get("llm_expansion", {})
    validation_cfg = config.get("validation_layer", {})
    findings_store_cfg = config.get("findings_store", {})
    monte_carlo_cfg = config.get("monte_carlo", {})
    foundry_cfg = config.get("foundry", {})
    cpcv_cfg = config.get("cpcv", {})
    fork_cfg = config.get("fork_validation", {})
    solana_cfg = config.get("solana_validation", {})
    monitoring_cfg = config.get("monitoring", {})
    bounty_cfg = config.get("bounty", {})
    campaign_cfg = config.get("campaign", {})
    campaign_id = str(campaign_cfg.get("id", "") or "")
    live_target = load_live_target(config)

    log("=" * 70)
    log("NIGHT SHIFT SECURITY — Adversarial Research Pipeline")
    log("=" * 70)

    catalog = get_exploit_catalog()
    states = catalog_states()
    if live_target is not None:
        from night_shift_security.data.target_config import resolve_target_states

        states = resolve_target_states(live_target, catalog)
        log(f"\n── Live Target: {live_target.protocol_name} ({live_target.target_id}) ──")
        log(f"  Chain: {live_target.chain} | Templates: {', '.join(live_target.templates)}")
        if live_target.exploit_id:
            log(f"  Catalog anchor: {live_target.exploit_id}")
        if live_target.immunefi_program:
            log(f"  Immunefi program: {live_target.immunefi_program}")
    if campaign_id:
        log(f"\n── Campaign: {campaign_cfg.get('name', campaign_id)} ({campaign_id}) ──")
        fork_cfg = {**fork_cfg, "targets": target_fork_ids(live_target)}
        solana_cfg = {**solana_cfg, "always_test_catalog_solana_anchors": True}

    # Stage 0: Sanity check ground truth
    log("\n── Stage 0: Ground Truth Sanity Check ──")
    ground_truth = evaluate_catalog_directly(catalog)
    gt_pass = sum(1 for c in ground_truth if not c.rejected)
    log(f"  {gt_pass}/{len(ground_truth)} known exploits pass gates with exact parameters")

    if hypothesis_cfg.get("structural_validation", True):
        from night_shift_security.domain.attack_hypotheses import get_generator

        valid_samples = 0
        for template_id in list_generators():
            generator = get_generator(template_id)
            if generator is None:
                continue
            for hypothesis in generator.sample(3):
                ok, _ = validate_hypothesis(hypothesis)
                if ok:
                    valid_samples += 1
        log(f"  Hypothesis structural validation: {valid_samples} samples OK")

    # Stage 1: Hypothesis generation
    log("\n── Stage 1: Attack Vector Generation ──")
    candidates = []
    samples_per_template = int(hypothesis_cfg.get("samples_per_template", 20))
    sample_fraction = hypothesis_cfg.get("sample_fraction_of_grid")
    grid_enabled = hypothesis_cfg.get("grid_enabled", True)

    if live_target is not None:
        target_vectors = generate_target_vectors(live_target, config, llm_cfg=llm_cfg)
        target_candidates = evaluate_target_vectors(live_target, target_vectors, gates, catalog)
        candidates.extend(target_candidates)
        log(f"  Live target vectors: {len(target_vectors)} evaluated → {len(target_candidates)} candidates")

    template_ids = (
        list(live_target.templates)
        if live_target is not None and live_target.templates
        else config.get("templates", ["governance_capture"])
    )
    for template_id in template_ids if live_target is None else []:
        template = get_template(template_id)
        grid_vectors = generate_attack_vectors(template) if grid_enabled else []
        vectors = list(grid_vectors)
        if grid_enabled:
            log(f"  {template_id}: {len(grid_vectors)} vectors from param grid")

        if hypothesis_cfg.get("enabled", True) and template_id in list_generators():
            sample_count = resolve_sample_count(
                len(grid_vectors) if grid_vectors else samples_per_template,
                samples_per_template,
                sample_fraction,
            )
            sampled = generate_sampled_attack_vectors(template_id, sample_count)
            vectors.extend(sampled)
            log(f"  {template_id}: +{len(sampled)} vectors from hypothesis sampling")

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
                vectors.extend(llm_vectors)
                log(
                    f"  {template_id}: +{len(llm_vectors)} LLM proposal vectors "
                    f"(enabled, validated)"
                )

        filter_cfg = hypothesis_cfg.get("structural_filters", {})
        vectors, filter_stats = apply_structural_filters(vectors, filter_cfg)
        if filter_stats.dropped:
            log(
                f"  {template_id}: {filter_stats.output_count} vectors after structural filters "
                f"(dropped {filter_stats.dropped}: {filter_stats.reasons})"
            )
        else:
            log(f"  {template_id}: {filter_stats.output_count} vectors after structural filters")

        for vector in vectors:
            candidates.append(evaluate_attack_vector(vector, states, gate=gates))

    if live_target is None:
        catalog_seeds = evaluate_catalog_seeds(catalog, gates)
        candidates.extend(catalog_seeds)
        log(f"  Catalog seeds: {len(catalog_seeds)} ground-truth exploit vectors")
    elif live_target.exploit_id:
        anchor = next((e for e in catalog if e.exploit_id == live_target.exploit_id), None)
        if anchor is not None:
            seeds = evaluate_catalog_seeds([anchor], gates)
            candidates.extend(seeds)
            log(f"  Catalog anchor seed: {live_target.exploit_id}")

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

    # Stage 4b: CPCV + PBO overfitting detection
    cpcv_results: dict = {}
    if cpcv_cfg.get("enabled", True):
        log("\n── Stage 4b: CPCV + PBO Overfitting Detection ──")
        cpcv_results = run_cpcv_phase(candidates, catalog, cpcv_cfg)
        log(f"  Candidates analyzed: {len(cpcv_results)}")
        if cpcv_results:
            safe = sum(1 for r in cpcv_results.values() if r["verdict"] == "SAFE")
            danger = sum(1 for r in cpcv_results.values() if r["verdict"] == "DANGER")
            log(f"  SAFE: {safe} | DANGER: {danger}")
            avg_pbo = sum(r["pbo"] for r in cpcv_results.values()) / len(cpcv_results)
            log(f"  Average PBO: {avg_pbo:.0%}")
    else:
        log("\n── Stage 4b: CPCV (disabled) ──")

    # Stage 5: Monte Carlo stress testing
    mc_results: dict = {}
    if monte_carlo_cfg.get("enabled", True):
        log("\n── Stage 5: Monte Carlo Stress Testing ──")
        mc_results = run_monte_carlo_phase(candidates, states, monte_carlo_cfg, catalog=catalog)
        mc_pass = sum(1 for c in candidates if not c.rejected and c.mc_simulations > 0)
        log(f"  Candidates stress-tested: {len(mc_results)}")
        log(f"  Still passing after MC: {mc_pass}")
        if mc_results:
            best_mc = max(mc_results.values(), key=lambda m: m.success_rate)
            log(f"  Best MC reproducibility: {best_mc.success_rate:.0%} ({best_mc.n_simulations} sims)")
    else:
        log("\n── Stage 5: Monte Carlo (disabled) ──")

    # Stage 5b: Foundry validation
    foundry_results: dict = {}
    if foundry_cfg.get("enabled", True):
        log("\n── Stage 5b: Foundry Validation ──")
        foundry_results = run_foundry_phase(candidates, states, foundry_cfg)
        confirmed = sum(1 for v in foundry_results.values() if v)
        backend = next((c.simulator_backend for c in candidates if c.simulator_backend), "mock")
        log(f"  Simulator backend: {backend}")
        log(f"  Foundry confirmed: {confirmed}/{len(foundry_results)}")
    else:
        log("\n── Stage 5b: Foundry Validation (disabled) ──")

    # Stage 5c: Mainnet fork validation (Euler EVM / Mango catalogue)
    fork_results: dict = {}
    if fork_cfg.get("enabled", True):
        log("\n── Stage 5c: Mainnet Fork Validation ──")
        fork_results = run_fork_validation_phase(candidates, catalog, fork_cfg)
        fork_confirmed = sum(1 for r in fork_results.values() if r.get("fork_confirmed"))
        fork_reproduced = sum(1 for c in candidates if c.fork_reproduced)
        from night_shift_security.data.fork_targets import evm_fork_targets
        evm_targets = [t.target_id for t in evm_fork_targets()]
        log(f"  EVM fork targets: {', '.join(evm_targets)}")
        log(f"  Fork confirmed: {fork_confirmed}/{len(fork_results)}")
        log(f"  Fork reproduced (live EVM): {fork_reproduced}")
        rpc = rpc_status()
        log(f"  RPC configured: {rpc['configured']} | live: {rpc['available']}")
    else:
        log("\n── Stage 5c: Fork Validation (disabled) ──")

    fork_bonus_result: dict = {}
    if fork_cfg.get("enabled", True):
        log("\n── Stage 5c′: Fork Scoring Bonus ──")
        fork_bonus_result = apply_fork_scoring_bonus(candidates, fork_cfg)
        log(f"  Bonus applied: {fork_bonus_result.get('adjusted', 0)}")
        if fork_bonus_result.get("rank_changes"):
            log("  Rank movements:")
            for change in fork_bonus_result["rank_changes"]:
                log(
                    f"    {change['label']}: #{change['rank_before']} → #{change['rank_after']} "
                    f"({change['severity_score_base']:.3f} → {change['severity_score']:.3f})"
                )
        if fork_bonus_result.get("score_only_bumps"):
            log(
                f"  Score-only bumps (no rank change): "
                f"{len(fork_bonus_result['score_only_bumps'])}"
            )
        candidates = rank_candidates(candidates)

    # Stage 5c-S: Solana validator / fixture replay
    solana_results: dict = {}
    if solana_cfg.get("enabled", True):
        log("\n── Stage 5c-S: Solana Validation ──")
        solana_results = run_solana_validation_phase(candidates, catalog, solana_cfg)
        solana_confirmed = sum(1 for r in solana_results.values() if r.get("solana_confirmed"))
        solana_reproduced = sum(1 for c in candidates if c.solana_reproduced)
        from night_shift_security.data.solana_targets import solana_catalog_targets
        solana_target_ids = [t.target_id for t in solana_catalog_targets()]
        log(f"  Solana targets: {', '.join(solana_target_ids)}")
        log(f"  Solana confirmed: {solana_confirmed}/{len(solana_results)}")
        log(f"  Solana reproduced (strict): {solana_reproduced}")
        solana_rpc = solana_status()
        log(
            f"  Solana RPC configured: {solana_rpc['configured']} | "
            f"live: {solana_rpc['available']} | validator: {solana_rpc['validator_installed']}"
        )
    else:
        log("\n── Stage 5c-S: Solana Validation (disabled) ──")

    solana_bonus_result: dict = {}
    if solana_cfg.get("enabled", True):
        log("\n── Stage 5c-S′: Solana Scoring Bonus ──")
        solana_bonus_result = apply_solana_scoring_bonus(candidates, solana_cfg, fork_cfg)
        log(f"  Bonus applied: {solana_bonus_result.get('adjusted', 0)}")
        if solana_bonus_result.get("rank_changes"):
            log("  Rank movements:")
            for change in solana_bonus_result["rank_changes"]:
                log(
                    f"    {change['label']}: #{change['rank_before']} → #{change['rank_after']} "
                    f"({change['severity_score_base']:.3f} → {change['severity_score']:.3f})"
                )
        if solana_bonus_result.get("score_only_bumps"):
            log(
                f"  Score-only bumps (no rank change): "
                f"{len(solana_bonus_result['score_only_bumps'])}"
            )
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

    # Refresh validation metadata (grades after reproduction; preserve fork/solana bonuses)
    refresh_validation_batch(
        candidates,
        {
            **validation_cfg,
            "level_1_mc_min": monte_carlo_cfg.get("min_reproducibility", 0.70),
            "max_pbo": cpcv_cfg.get("max_pbo", 0.30),
        },
        apply_scoring=False,
    )
    passed = [c for c in candidates if not c.rejected]

    # Stage 5d: Deduplication (before export / monitoring / bounty)
    log("\n── Stage 5d: Findings Deduplication ──")
    raw_findings = findings_from_candidates(passed, rediscovery.get("rediscovery_map"))
    findings, dedupe_report = dedupe_findings(raw_findings)
    log_dedupe_report(dedupe_report, log=log)

    store_stats: dict = {}
    if findings_store_cfg.get("enabled", True):
        log("\n── Stage 5e: Findings Store ──")
        run_meta_for_store = {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "campaign_id": campaign_id,
        }
        store_result = record_run(candidates, findings, run_meta_for_store, findings_store_cfg)
        store_stats = store_result.to_dict()
        log(
            f"  Store: +{store_result.added} records "
            f"({store_result.findings} promoted, {store_result.lineage_roots} lineage roots)"
        )
        log(f"  Path: {store_result.store_path}")
    else:
        log("\n── Stage 5e: Findings Store (disabled) ──")

    log("\n── Stage 5f: Novel Vector Catalog ──")
    novel_cfg = config.get("novel_vectors", {"enabled": True})
    novel_path = ""
    if novel_cfg.get("enabled", True):
        novel_path = str(
            export_novel_vector_catalog(
                candidates,
                {"run_at": datetime.now(timezone.utc).isoformat(), "campaign_id": campaign_id},
                output_dir,
                min_novelty_score=float(novel_cfg.get("min_novelty_score", 0.0)),
                include_rejected=bool(novel_cfg.get("include_rejected", True)),
            )
        )
        log(f"  Catalog: {novel_path}")

    # Output
    log("\n── Report Generation ──")
    elapsed = time.time() - start
    md_path, json_path = write_report(
        findings, candidates, output_dir, elapsed, rediscovery,
        monte_carlo=mc_results, foundry=foundry_results,
        cpcv=cpcv_results, fork=fork_results, solana=solana_results,
        dedupe_report=dedupe_report,
    )

    import json
    with open(json_path) as f:
        report_payload = json.load(f)
    export_paths = report_payload.get("export_paths", {})

    # Stage 6: Monitoring + bug-bounty export
    monitoring_result: dict = {}
    if monitoring_cfg.get("enabled", True) and findings:
        log("\n── Stage 6: Monitoring Hooks ──")
        run_meta = {
            "run_at": report_payload.get("run_at"),
            "min_severity": monitoring_cfg.get("min_severity", "high"),
        }
        monitoring_result = emit_monitoring_event(findings, run_meta, monitoring_cfg)
        log(f"  Alerts emitted: {monitoring_result.get('emitted', 0)}")
        if monitoring_result.get("sinks"):
            log(f"  Sinks: {', '.join(monitoring_result['sinks'])}")

    bounty_result: dict = {}
    if bounty_cfg.get("enabled", True) and findings:
        log("\n── Stage 6b: Bug Bounty Export ──")
        run_meta_bounty = {
            "run_at": report_payload.get("run_at"),
            "engine_version": config.get("version", "v2.0"),
            "shoestring_mode": bounty_cfg.get("shoestring_pack", False),
            "campaign_id": campaign_id,
        }
        if live_target is not None:
            run_meta_bounty["live_target"] = target_summary(live_target)
        bounty_result = export_bounty_artifacts(
            findings,
            run_meta_bounty,
            output_dir,
            bounty_cfg,
        )
        log(f"  Bounty pack: {bounty_result.get('submissions_path', '—')}")
        immunefi = bounty_result.get("immunefi", {})
        if immunefi:
            log(f"  Immunefi packs: {immunefi.get('pack_count', 0)}")
            log(f"  Immunefi manifest: {immunefi.get('manifest_path', '—')}")
        shoestring = bounty_result.get("shoestring", {})
        if shoestring.get("selected_finding_id"):
            log(f"  Shoestring pack: {shoestring.get('pack_dir', '—')}")
            log(f"  Selected: {shoestring.get('selected_finding_id')} ({shoestring.get('reproduction_method')})")

    llm_eval_result: dict = {}
    if config.get("llm_quality_eval", {}).get("enabled", False):
        log("\n── LLM Quality Eval ──")
        llm_eval_result = run_llm_quality_eval(output_dir=output_dir)
        log(f"  Winner: {llm_eval_result.get('winner', '—')}")
        if llm_eval_result.get("output_path"):
            log(f"  Report: {llm_eval_result['output_path']}")

    log(f"\n{'=' * 70}")
    log(f"NIGHT SHIFT SECURITY COMPLETE — {elapsed:.0f}s")
    log(f"  Findings: {len(findings)}")
    log(f"  Report: {md_path}")
    log(f"  JSON: {json_path}")
    if export_paths:
        log(f"  Public feed: {export_paths.get('feed', '—')}")
        log(f"  Tokenomics bridge: {export_paths.get('tokenomics_bridge', '—')}")
    log(f"{'=' * 70}")

    return {
        "findings": len(findings),
        "candidates_evaluated": len(candidates),
        "candidates_passed": len(passed),
        "rediscovery": rediscovery,
        "report_md": str(md_path),
        "report_json": str(json_path),
        "elapsed_seconds": elapsed,
        "monte_carlo_tested": len(mc_results),
        "foundry_confirmed": sum(1 for v in foundry_results.values() if v),
        "cpcv_analyzed": len(cpcv_results),
        "fork_confirmed": sum(1 for r in fork_results.values() if r.get("fork_confirmed")),
        "fork_reproduced": sum(1 for c in candidates if c.fork_reproduced),
        "fork_scoring": fork_bonus_result,
        "solana_confirmed": sum(1 for r in solana_results.values() if r.get("solana_confirmed")),
        "solana_reproduced": sum(1 for c in candidates if c.solana_reproduced),
        "solana_scoring": solana_bonus_result,
        "export_paths": export_paths,
        "monitoring": monitoring_result,
        "bounty_pack": bounty_result.get("submissions_path", ""),
        "bounty": bounty_result,
        "live_target": target_summary(live_target) if live_target else None,
        "dedupe": dedupe_report.to_dict(),
        "findings_store": store_stats,
        "campaign_id": campaign_id,
        "novel_vector_catalog": novel_path,
        "llm_quality_eval": llm_eval_result,
    }