"""CLI entry point for Night Shift Security."""

import argparse
import json
import sys
from pathlib import Path

from night_shift_security.api.server import serve
from night_shift_security.core.pipeline import run_security_pipeline
from night_shift_security.export.dataset import export_dataset
from night_shift_security.export.disclosure import build_disclosure_report, update_disclosure_status
from night_shift_security.bounty.candidates import rank_findings_by_bounty_score, write_bounty_candidates_jsonl
from night_shift_security.bounty.discovery_scan import list_programs_for_platform, run_bounty_scan
from night_shift_security.bounty.pipeline import export_bounty_artifacts, export_bounty_pack


from night_shift_security.export.immunefi_submission import export_bounty_export_tracks, export_immunefi_packs
from night_shift_security.platform.sync import platform_diff, sync_platforms
from night_shift_security.platform.solodit import sync_solodit_findings, write_solodit_patterns
from night_shift_security.platform.auditvault import (
    auditvault_summary,
    sync_auditvault_findings,
    write_auditvault_ids,
    write_auditvault_patterns,
)
from night_shift_security.export.shoestring_submission import export_shoestring_pack
from night_shift_security.immunefi.investigate import (
    load_scan_report,
    pick_investigation_targets,
    run_investigation_queue,
)
from night_shift_security.immunefi.scan import run_immunefi_scan
from night_shift_security.data.immunefi_registry import list_programs, program_summary
from night_shift_security.export.deduper import dedupe_findings, log_dedupe_report
from night_shift_security.export.loader import findings_from_run_json
from night_shift_security.monitoring.hooks import emit_monitoring_event
from night_shift_security.native import (
    HarnessStatus,
    load_manifest as load_native_harness_manifest,
    save_manifest as save_native_harness_manifest,
    upsert_harness as upsert_native_harness,
)
from night_shift_security.eval.llm_quality import run_llm_quality_eval
from night_shift_security.knowledge.findings_store import (
    ancestors,
    best_evidence_per_lineage_root,
    campaign_stats,
    descendants,
    lineage_survival_stats,
    load_store,
)
from night_shift_security.orchestration.coordinator import (
    coordinator_status,
    default_state_path,
    ensure_pending_missions,
    init_state,
    load_state,
    plan_missions,
    run_mission_cycle,
    save_state,
)


def _cmd_run(config: Path | None, proposals: Path | None = None) -> int:
    result = run_security_pipeline(config_path=config, proposals_path=proposals)
    return 0 if result["findings"] > 0 or result["rediscovery"]["rediscovered"] > 0 else 1


def _cmd_serve(host: str, port: int, dataset: Path) -> int:
    serve(host=host, port=port, dataset_path=dataset)
    return 0


def _cmd_export(input_path: Path, output_dir: Path) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    paths = export_dataset(findings, run_meta, output_dir, candidates=None)
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


def _cmd_dedupe(input_path: Path, output_dir: Path, re_export: bool) -> int:
    from night_shift_security.core.results import _finding_to_dict

    findings, run_meta = findings_from_run_json(input_path)
    deduped, report = dedupe_findings(findings)
    print(f"Dedupe: {report.before_count} → {report.after_count} (dropped {report.dropped_count})")
    log_dedupe_report(report)

    out_path = input_path.parent / "findings.deduped.json"
    payload = json.loads(input_path.read_text())
    payload["findings_count_raw"] = report.before_count
    payload["findings_count"] = report.after_count
    payload["dedupe"] = report.to_dict()
    payload["findings"] = [_finding_to_dict(f) for f in deduped]
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote: {out_path}")

    if re_export:
        paths = export_dataset(deduped, run_meta, output_dir, dedupe=False)
        for name, path in paths.items():
            print(f"  {name}: {path}")
    return 0


def _cmd_hipif(
    action: str,
    *,
    task: str | None,
    context_path: Path,
    text: str | None,
    subgoal: str | None,
    hipif_action: str | None,
    observation: str | None,
    outcome: str | None,
    metrics_json: str | None,
) -> int:
    from night_shift_security.orchestration import hipif as hf

    if action == "init":
        if not task:
            print("hipif init requires --task", file=sys.stderr)
            return 1
        ctx = hf.init_context(task, context_path)
        print(json.dumps(ctx.to_dict(), indent=2, default=str))
        return 0

    if action == "read":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        payload = ctx.to_dict()
        payload["next_subgoal_hint"] = hf.subgoal_action_hint(ctx.current_subgoal)
        payload["submit_ready"] = hf.submit_ready()
        print(json.dumps(payload, indent=2, default=str))
        return 0

    if action == "parse":
        if not text:
            print("hipif parse requires --text", file=sys.stderr)
            return 1
        parsed = hf.parse_agent_turn(text)
        print(json.dumps(parsed.to_dict(), indent=2, default=str))
        return 0 if parsed.format_ok else 1

    if action == "ground":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        sg = subgoal or ctx.current_subgoal
        act = hipif_action or ""
        result = hf.grounding_check(ctx, sg, act)
        print(json.dumps(result.to_dict(), indent=2, default=str))
        return 0 if result.ok else 1

    if action == "record":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        if not hipif_action:
            print("hipif record requires --action", file=sys.stderr)
            return 1
        rep = hf.repetition_monitor(ctx.local_history, hipif_action, observation=observation or "")
        if rep.blocked:
            print(json.dumps(rep.to_dict(), indent=2, default=str))
            return 1
        ctx = hf.record_step(ctx, hipif_action, observation or "")
        hf.save_context(ctx, context_path)
        print(json.dumps({"recorded": True, "step_count": len(ctx.local_history)}, indent=2))
        return 0

    if action == "fold":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        if not outcome:
            print("hipif fold requires --outcome", file=sys.stderr)
            return 1
        metrics: dict = {}
        if metrics_json:
            metrics = json.loads(metrics_json)
        subgoal_id = (subgoal or ctx.current_subgoal).strip()
        auth = hf.authorize_fold(ctx, subgoal_id)
        if not auth.ok:
            print(json.dumps(auth.to_dict(), indent=2), file=sys.stderr)
            print(f"HIPIF fold blocked: {auth.error}", file=sys.stderr)
            return 1
        ctx = hf.history_folder(ctx, subgoal_id, outcome, metrics=metrics)
        if hf.submit_ready():
            ctx.chain_status = "submit_ready"
        hf.save_context(ctx, context_path)
        folded = ctx.folded_history[-1] if ctx.folded_history else None
        print(
            json.dumps(
                {
                    "folded": folded.to_dict() if folded else None,
                    "compact": folded.compact_line() if folded else "",
                    "current_subgoal": ctx.current_subgoal,
                    "chain_status": ctx.chain_status,
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if action == "next":
        ctx = hf.load_context(context_path)
        if ctx is None:
            nxt = hf.CHAIN_SUBGOALS[0]
            print(json.dumps({"subgoal": nxt, "hint": hf.subgoal_action_hint(nxt)}, indent=2))
            return 0
        nxt = hf.next_subgoal_id(ctx) or ctx.current_subgoal
        print(
            json.dumps(
                {
                    "current_subgoal": ctx.current_subgoal,
                    "next_subgoal": nxt,
                    "hint": hf.subgoal_action_hint(ctx.current_subgoal),
                    "chain_status": ctx.chain_status,
                },
                indent=2,
            )
        )
        return 0

    if action == "status":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        validation = hf.validate_chain_complete(ctx)
        pending = hf.first_pending_subgoal(ctx)
        print(
            json.dumps(
                {
                    "chain_status": ctx.chain_status,
                    "current_subgoal": ctx.current_subgoal,
                    "bulk_phase_complete": ctx.bulk_phase_complete,
                    "bulk_deterministic_complete": hf.bulk_deterministic_complete(ctx),
                    "agent_phase_ready": hf.agent_phase_ready(ctx),
                    "folds": validation.folds,
                    "expected_folds": validation.expected,
                    "pending_subgoal": pending,
                    "agent_subgoals": sorted(hf.AGENT_SUBGOALS),
                    "complete": validation.ok,
                    "errors": validation.errors,
                    "submit_ready": hf.submit_ready(),
                },
                indent=2,
            )
        )
        return 0

    if action == "gate":
        ctx = hf.load_context(context_path)
        if ctx is None:
            print(f"HIPIF context not found: {context_path}", file=sys.stderr)
            return 1
        validation = hf.validate_chain_complete(ctx)
        print(json.dumps(validation.to_dict(), indent=2))
        if validation.ok:
            return 0
        print("HIPIF chain incomplete — cron must not mark success.", file=sys.stderr)
        return 1

    print(f"Unknown hipif action: {action}", file=sys.stderr)
    return 1


def _cmd_improve(loop_state: Path, store_path: Path) -> int:
    from night_shift_security.knowledge.findings_store import load_store
    from night_shift_security.orchestration.bounty_loop import load_loop_state
    from night_shift_security.orchestration.recursive_improvement import analyze_loop_state

    state = load_loop_state(loop_state)
    store = load_store(store_path)
    report = analyze_loop_state(state, store)
    print(json.dumps(report, indent=2, default=str))
    return 0


def _cmd_bounty_loop(
    iterations: int,
    trials: int | None,
    stop_on_submit: bool,
    refresh_scan: bool,
    min_bounty: int,
    min_grade: int,
    state_path: Path | None,
    scan_path: Path | None,
    config: Path | None,
    proposals: Path | None,
    target: str | None,
) -> int:
    from night_shift_security.orchestration.bounty_loop import run_bounty_loop

    result = run_bounty_loop(
        iterations=iterations,
        trials=trials,
        stop_on_submit=stop_on_submit,
        refresh_scan=refresh_scan,
        min_bounty=min_bounty,
        min_grade=min_grade,
        state_path=state_path,
        scan_path=scan_path,
        config_path=config,
        proposals_path=proposals,
        target_slug=target,
    )
    print(json.dumps(result, indent=2, default=str))
    final = result.get("final_status")
    if final == "submit_ready":
        print(
            "  ALERT: submission-qualified finding — human gate required "
            "(see data/security_results/loop/submission_alert.json)",
            file=sys.stderr,
        )
        return 0
    if final == "exhausted":
        return 1
    if final == "failed":
        return 1
    return 0


def _cmd_triage_files(
    repo: Path,
    slug: str,
    min_score: int,
    output: Path,
) -> int:
    from night_shift_security.triage.file_ranker import write_rank_report

    payload = write_rank_report(repo, output, slug=slug, min_score=min_score)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_triage_patches(
    repo: Path,
    slug: str,
    max_commits: int,
    output: Path,
    ranked_paths: list[str],
) -> int:
    from night_shift_security.triage.git_patches import write_patch_report

    summary = write_patch_report(
        repo,
        output,
        slug=slug,
        max_commits=max_commits,
        ranked_paths=ranked_paths,
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


def _cmd_invariants_test(
    recon_path: Path,
    output_dir: Path,
    use_hypothesis: bool,
    max_examples: int,
) -> int:
    from night_shift_security.invariants.pbt import run_invariant_tests

    result = run_invariant_tests(
        recon_path,
        use_hypothesis=use_hypothesis,
        max_examples=max_examples,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = result.get("target_id") or recon_path.stem
    out_path = output_dir / f"{slug}_invariants.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({**result, "output": str(out_path)}, indent=2, default=str))
    return 0 if result.get("failed", 0) == 0 else 1


def _cmd_semantic_map(
    slug: str,
    repo: Path,
    output: Path | None,
    kind: str | None,
    store: Path | None,
) -> int:
    from night_shift_security.semantic import write_semantic_artifacts

    out_dir = output or Path("data/security_results/semantic") / slug
    result = write_semantic_artifacts(slug, repo, out_dir, kind=kind, store_path=store)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_semantic_candidates(
    slug: str,
    semantic_dir: Path | None,
    kind: str | None,
    output: Path | None,
    store: Path | None,
) -> int:
    from night_shift_security.semantic.candidates import build_candidate_seeds, write_candidates_jsonl

    base = semantic_dir or Path("data/security_results/semantic") / slug
    code_map_path = base / "code_map.json"
    if not code_map_path.is_file():
        print(f"semantic code_map missing: {code_map_path}", file=sys.stderr)
        return 1
    semantic_map = json.loads(code_map_path.read_text())
    candidates = build_candidate_seeds(semantic_map, target_slug=slug, kind=kind)
    out_path = output or base / "candidate_seeds.jsonl"
    write_candidates_jsonl(candidates, out_path)
    store_result = None
    if store is not None:
        from night_shift_security.knowledge.concrete_candidates import upsert_candidates

        store_result = upsert_candidates(candidates, store)
    print(
        json.dumps(
            {
                "slug": slug,
                "candidate_count": len(candidates),
                "output": str(out_path),
                "candidate_store": store_result,
            },
            indent=2,
        )
    )
    return 0


def _cmd_tools_opengrep(
    slug: str,
    repo: Path,
    rules: Path,
    out: Path | None,
    semantic_dir: Path | None,
    store: Path | None,
    tool: str | None,
) -> int:
    from night_shift_security.tools.opengrep import run_opengrep

    out_dir = out or Path("data/security_results/semantic") / slug
    sem_dir = semantic_dir or Path("data/security_results/semantic") / slug
    result = run_opengrep(
        slug=slug,
        repo=repo,
        out_dir=out_dir,
        rules_dir=rules,
        semantic_map_path=sem_dir / "code_map.json",
        store_path=store,
        tool=tool,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("ok", "tool_missing") else 1


def _cmd_tools_offchain(
    tool_name: str,
    scope: Path,
    out: Path,
    target: str | None,
) -> int:
    from night_shift_security.tools.offchain import run_offchain_tool

    result = run_offchain_tool(tool_name=tool_name, scope_path=scope, out_dir=out, target=target)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("ok", "tool_missing", "scope_not_enabled") else 1


def _cmd_poc_generate(
    candidate_id: str,
    store: Path,
    foundry_root: Path,
    solana_root: Path,
) -> int:
    from night_shift_security.knowledge.concrete_candidates import load_candidate_records
    from night_shift_security.pocgen import generate_poc_for_candidate
    from night_shift_security.semantic.candidates import ConcreteCandidate

    candidate = None
    for record in load_candidate_records(store):
        if record.get("candidate_id") == candidate_id:
            candidate = ConcreteCandidate.from_dict(record)
            break
    if candidate is None:
        print(f"candidate not found: {candidate_id}", file=sys.stderr)
        return 1
    result = generate_poc_for_candidate(
        candidate,
        foundry_root=foundry_root,
        solana_root=solana_root,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_poc_verify(candidate_id: str, store: Path, artifact: Path | None, output_dir: Path) -> int:
    from night_shift_security.pocgen import verify_candidate_poc

    result = verify_candidate_poc(
        candidate_id,
        store_path=store,
        artifact_path=artifact,
        output_dir=output_dir,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in ("passed", "failed_closed", "tool_missing") else 1


def _cmd_traces_summarize(slug: str, traces_dir: Path, signatures: Path, hints: Path) -> int:
    from night_shift_security.orchestration.failure_trace import summarize_failure_traces

    result = summarize_failure_traces(
        slug,
        traces_dir=traces_dir,
        signatures_path=signatures,
        hints_path=hints,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_native_status(manifest: Path) -> int:
    import json

    payload = load_native_harness_manifest(manifest)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_native_mark(
    manifest: Path,
    slug: str,
    name: str,
    platform: str,
    chain: str,
    contract_address: str,
    source_commit: str,
    status: str,
    notes: str,
) -> int:
    import json

    entry = HarnessStatus(
        slug=slug,
        name=name or slug,
        platform=platform,
        chain=chain,
        contract_address=contract_address,
        source_commit=source_commit,
        status=status,
        notes=notes,
    )
    payload = upsert_native_harness(entry, manifest)
    save_native_harness_manifest(payload, manifest)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_operator_forge_test(match_test: str, fork_block: int | None, fork_url: str | None) -> int:
    from night_shift_security.operator.foundry_tools import run_forge_test

    result = run_forge_test(match_test=match_test, fork_block=fork_block, fork_url=fork_url)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def _cmd_operator_cast_call(
    to: str,
    signature: str,
    args_list: list[str],
    rpc_url: str | None,
    from_addr: str | None,
) -> int:
    from night_shift_security.operator.foundry_tools import run_cast_call

    result = run_cast_call(
        to=to,
        signature=signature,
        args=args_list,
        rpc_url=rpc_url,
        from_addr=from_addr,
    )
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def _cmd_operator_anvil(action: str, fork_block: int | None, fork_url: str | None, use_docker: bool) -> int:
    from night_shift_security.operator.foundry_tools import start_anvil_fork, stop_anvil_fork

    if action == "stop":
        result = stop_anvil_fork()
    else:
        result = start_anvil_fork(
            fork_url=fork_url,
            fork_block=fork_block,
            use_docker=use_docker,
        )
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def _cmd_operator_sandbox(action: str, fork_block: int | None, fork_url: str | None) -> int:
    from night_shift_security.operator.anvil_sandbox import (
        sandbox_status,
        start_docker_sandbox,
        stop_docker_sandbox,
    )

    if action == "status":
        print(json.dumps(sandbox_status(), indent=2))
        return 0
    if action == "stop":
        result = stop_docker_sandbox()
    else:
        result = start_docker_sandbox(fork_url=fork_url, fork_block=fork_block)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if result.success else 1


def _cmd_novel_score(inputs: list[Path], output: Path) -> int:
    from night_shift_security.orchestration.novel_gate import (
        score_novel_batch,
        write_human_gate_report,
    )

    batch = score_novel_batch(inputs)
    report_path = write_human_gate_report(batch, output)
    print(
        json.dumps(
            {
                "human_gate_report": str(report_path),
                "novel_count": len(batch.get("novel_candidates", [])),
                "submit_ready_count": len(batch.get("submit_ready", [])),
                "human_gate_pending": batch.get("human_gate_pending"),
                "kate_action": batch.get("kate_action"),
            },
            indent=2,
        )
    )
    return 0


def _cmd_impact_oracle(
    oracle: str,
    getter: str,
    pair: str,
    rpc_url: str | None,
    threshold_pct: float,
    token0_decimals: int,
    token1_decimals: int,
) -> int:
    from night_shift_security.impact.oracle_arbitrage import compare_oracle_vs_dex

    result = compare_oracle_vs_dex(
        oracle=oracle,
        price_sig=getter,
        pair=pair,
        rpc_url=rpc_url,
        token0_decimals=token0_decimals,
        token1_decimals=token1_decimals,
        divergence_threshold_pct=threshold_pct,
    )
    print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0


def _cmd_impact_tvs(
    base_pool: str,
    siblings_path: Path,
    holder: str | None,
    rpc_url: str | None,
) -> int:
    from night_shift_security.impact.tvs_maximization import (
        load_sibling_registry,
        rank_sibling_pools,
    )

    siblings = load_sibling_registry(siblings_path)
    result = rank_sibling_pools(
        base_pool=base_pool,
        siblings=siblings,
        holder=holder,
        rpc_url=rpc_url,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ranked") else 1


def _cmd_triage_wormhole_map(
    repo: Path | None,
    output: Path,
    recon_output: Path | None,
) -> int:
    from night_shift_security.triage.wormhole_program_map import (
        build_wormhole_map,
        write_wormhole_recon,
    )

    payload = build_wormhole_map(repo_root=repo)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n")
    recon_path = recon_output or Path("sources/wormhole/recon.json")
    recon = write_wormhole_recon(recon_path, repo_root=repo)
    print(
        json.dumps(
            {
                "map_output": str(output),
                "recon_output": str(recon_path),
                "discovered_count": payload["discovered_count"],
                "primary_programs": recon["programs"],
            },
            indent=2,
        )
    )
    return 0


def _cmd_operator_slither(
    project_root: Path,
    triage_json: Path | None,
    min_score: int,
    files: list[str],
) -> int:
    from night_shift_security.operator.slither_tools import (
        load_ranked_files_from_triage,
        run_slither_on_files,
    )

    ranked = list(files)
    if triage_json:
        ranked = load_ranked_files_from_triage(triage_json, min_score=min_score)
    result = run_slither_on_files(ranked, project_root=project_root)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success") else 1


def _cmd_operator_checkpoint(
    action: str,
    path: Path,
    target_slug: str,
    active_hypothesis: str,
    context_reason: str,
    next_commands: list[str],
) -> int:
    from night_shift_security.orchestration.operator_checkpoint import (
        clear_checkpoint,
        load_checkpoint,
        write_checkpoint,
    )

    if action == "read":
        print(json.dumps(load_checkpoint(path), indent=2, default=str))
        return 0
    if action == "clear":
        clear_checkpoint(path)
        print(json.dumps({"status": "cleared", "path": str(path)}, indent=2))
        return 0
    payload = write_checkpoint(
        target_slug=target_slug,
        active_hypothesis=active_hypothesis,
        next_commands=next_commands,
        context_reason=context_reason,  # type: ignore[arg-type]
        path=path,
    )
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_bounty_score(
    input_path: Path,
    output_dir: Path,
    min_score: float,
    min_evidence_grade: int,
    append: bool,
) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    scored = rank_findings_by_bounty_score(
        findings,
        min_readiness=min_score,
        min_evidence_grade=min_evidence_grade,
    )
    if not scored:
        print("  no qualifying findings for bounty score", file=sys.stderr)
        return 1

    candidates_path = output_dir / "bounty" / "bounty_candidates.jsonl"
    write_bounty_candidates_jsonl(
        scored,
        candidates_path,
        run_at=run_meta.get("run_at"),
        append=append,
    )
    payload = [
        {
            "finding_id": s.finding.finding_id,
            "target_id": s.finding.target_id,
            "bounty_readiness": s.score.bounty_readiness,
            "expected_payout_proxy_usd": s.score.expected_payout_proxy_usd,
            "submission_recommendation": s.score.submission_recommendation,
            "platform": s.score.platform,
            "program_slug": s.score.program_slug,
        }
        for s in scored
    ]
    print(json.dumps({"candidates": payload, "count": len(payload)}, indent=2))
    print(f"  bounty_candidates: {candidates_path}")
    return 0


def _cmd_bounty_export(input_path: Path, output_dir: Path, min_severity: str, with_immunefi: bool) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    if with_immunefi:
        result = export_bounty_artifacts(
            findings,
            run_meta,
            output_dir,
            {
                "min_severity": min_severity,
                "immunefi_packs": True,
                "min_evidence_grade": 3,
            },
        )
        print(f"  bounty_pack: {result.get('submissions_path')}")
        immunefi = result.get("immunefi", {})
        if immunefi:
            print(f"  immunefi_manifest: {immunefi.get('manifest_path')}")
            print(f"  immunefi_packs: {immunefi.get('pack_count', 0)}")
    else:
        path = export_bounty_pack(findings, run_meta, output_dir, min_severity=min_severity)
        print(f"  bounty_pack: {path}")
    return 0


def _cmd_scan(
    config: Path | None,
    ecosystem: str | None,
    min_bounty: int,
    limit: int | None,
    list_only: bool,
    platform: str,
) -> int:
    if list_only:
        from night_shift_security.data.bounty_program import program_summary as bounty_summary

        programs = list_programs_for_platform(platform, ecosystem=ecosystem, min_max_bounty_usd=min_bounty)
        if limit:
            programs = programs[:limit]
        print(json.dumps([bounty_summary(p) for p in programs], indent=2))
        return 0

    report = run_bounty_scan(
        config_path=config,
        platform=platform,
        ecosystem=ecosystem,
        min_max_bounty_usd=min_bounty,
        limit=limit,
    )
    print(json.dumps(report["summary"], indent=2))
    print(f"  report_json: {report['paths']['json']}")
    print(f"  report_md: {report['paths']['markdown']}")
    if report.get("legacy_paths"):
        print(f"  immunefi_legacy: {report['legacy_paths']['immunefi_json']}")
    return 0


def _cmd_investigate(
    config: Path | None,
    scan_path: Path,
    top_n: int,
    min_grade: int,
    ecosystem: str | None,
    proposals: Path | None,
    dry_run: bool,
    exclude_slugs: list[str] | None,
) -> int:
    report = load_scan_report(scan_path)
    exclude = list(exclude_slugs or [])
    if dry_run:
        targets = pick_investigation_targets(
            report,
            top_n=top_n,
            min_evidence_grade=min_grade,
            ecosystem=ecosystem,
            exclude_slugs=exclude or None,
        )
        print(json.dumps({"targets": targets, "count": len(targets), "exclude": exclude}, indent=2))
        return 0

    result = run_investigation_queue(
        report,
        top_n=top_n,
        min_evidence_grade=min_grade,
        ecosystem=ecosystem,
        exclude_slugs=exclude or None,
        base_config_path=config,
        proposals_path=proposals,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("runs") else 1


def _cmd_submission(input_path: Path, output_dir: Path, min_evidence_grade: int) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    result = export_shoestring_pack(
        findings,
        {**run_meta, "shoestring_mode": True, "zero_rpc": True},
        output_dir,
        min_evidence_grade=min_evidence_grade,
    )
    if not result.get("selected_finding_id"):
        print(f"  no eligible finding: {result.get('reason', 'unknown')}", file=sys.stderr)
        return 1
    print(f"  selected: {result['selected_finding_id']} ({result['catalog_exploit_id']})")
    print(f"  pack_dir: {result['pack_dir']}")
    print(f"  manifest: {result['manifest_path']}")
    return 0


def _cmd_immunefi(input_path: Path, output_dir: Path, min_evidence_grade: int, min_severity: str) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    result = export_bounty_export_tracks(
        findings,
        run_meta,
        output_dir,
        min_evidence_grade=min_evidence_grade,
        min_severity=min_severity,
    )
    research = result.get("research_surface", {})
    submittable = result.get("submittable", {})
    print(f"  research_manifest: {research.get('manifest_path')}")
    print(f"  research_packs: {research.get('pack_count', 0)}")
    print(f"  submittable_manifest: {submittable.get('manifest_path')}")
    print(f"  submittable_packs: {submittable.get('pack_count', 0)}")
    return 0


def _cmd_platform(
    action: str,
    output_dir: Path,
    skip_network: bool,
    *,
    max_pages: int = 2,
    page_size: int = 100,
    scope: str = "target-plus-pattern",
    min_quality: int = 3,
    input_path: Path | None = None,
    patterns_output: Path | None = None,
    auditvault_repo: Path | None = None,
    auditvault_input: Path | None = None,
    auditvault_patterns_output: Path | None = None,
    auditvault_ids_output: Path | None = None,
) -> int:
    if action == "sync":
        result = sync_platforms(output_dir, skip_network=skip_network)
        print(json.dumps(result, indent=2))
        return 0
    if action == "diff":
        report = platform_diff(output_dir)
        print(json.dumps(report, indent=2))
        return 0
    if action == "solodit-sync":
        result = sync_solodit_findings(
            output_dir,
            scope=scope,
            page_size=page_size,
            max_pages_per_query=max_pages,
            min_quality=min_quality,
        )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in ("ok", "skipped_missing_key") else 1
    if action == "solodit-patterns":
        source = input_path or output_dir / "solodit_findings.json"
        result = write_solodit_patterns(
            source,
            patterns_output or Path("data/security_results/knowledge/solodit_patterns.jsonl"),
        )
        print(json.dumps(result, indent=2))
        return 0
    if action == "auditvault-sync":
        result = sync_auditvault_findings(auditvault_repo, output_dir)
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in ("ok", "parsed_with_warnings", "skipped_no_repo") else 1
    if action == "auditvault-patterns":
        source = auditvault_input or output_dir / "auditvault_findings.json"
        result = write_auditvault_patterns(
            source,
            auditvault_patterns_output
            or Path("data/security_results/knowledge/auditvault_patterns.jsonl"),
        )
        # Always emit ids index so RSI / self-interrogation can use it.
        ids_result = write_auditvault_ids(
            json.loads(source.read_text()) if source.is_file() else {"findings": []},
            auditvault_ids_output
            or Path("data/security_results/knowledge/auditvault_ids.jsonl"),
        )
        print(json.dumps({"patterns": result, "ids": ids_result}, indent=2))
        return 0 if result.get("pattern_count", 0) > 0 or result.get("status") == "skipped_no_repo" else 1
    if action == "auditvault-summary":
        summary = auditvault_summary(
            auditvault_input or output_dir / "auditvault_findings.json"
        )
        print(json.dumps(summary, indent=2))
        return 0
    print(f"Unknown platform action: {action}", file=sys.stderr)
    return 1


def _cmd_monitor(input_path: Path, webhook: str, alert_file: Path | None) -> int:
    findings, run_meta = findings_from_run_json(input_path)
    config = {
        "enabled": True,
        "min_severity": "high",
        "webhook_url": webhook,
        "alert_file": str(alert_file) if alert_file else "",
    }
    result = emit_monitoring_event(findings, run_meta, config)
    print(json.dumps(result, indent=2, default=str))
    return 0


def _cmd_coordinator(
    action: str,
    config: Path | None,
    state_path: Path,
    store_path: Path,
    top_n: int,
    proposals: Path | None,
    campaign_id: str | None,
) -> int:
    if action == "init":
        if config is None:
            print("coordinator init requires --config", file=sys.stderr)
            return 1
        state = init_state(config, state_path=state_path)
        print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if not state_path.is_file():
        print(f"Coordinator state not found: {state_path} (run coordinator init first)", file=sys.stderr)
        return 1

    state = load_state(state_path)
    store = load_store(store_path)

    if action == "status":
        state = ensure_pending_missions(state, store)
        save_state(state, state_path)
        print(json.dumps(coordinator_status(state, store), indent=2, default=str))
        return 0

    if action == "plan":
        state = ensure_pending_missions(state, store)
        save_state(state, state_path)
        missions = plan_missions(state, store, top_n=top_n)
        print(
            json.dumps(
                {
                    "campaign_id": state.campaign_id,
                    "missions": [m.to_dict() for m in missions],
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if action == "cycle":
        result = run_mission_cycle(
            state,
            proposals_path=proposals,
            state_path=state_path,
            store_path=store_path,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "completed" else 1

    print(f"Unknown coordinator action: {action}", file=sys.stderr)
    return 1


def _cmd_knowledge(
    store_path: Path,
    hypothesis_id: str | None,
    stats_only: bool,
    campaign_id: str | None,
    bounty_ready: bool,
    min_score: float,
) -> int:
    store = load_store(store_path)
    if bounty_ready:
        from night_shift_security.data.schemas import Finding, InvariantViolation, ReproductionStep, Severity

        findings: list[Finding] = []
        for record in store.records:
            if record.evidence_grade < 3 or record.rejected:
                continue
            findings.append(
                Finding(
                    finding_id=record.finding_id or record.hypothesis_id,
                    template_id=record.template_id,
                    target_id=record.target_id,
                    severity=Severity.HIGH,
                    severity_score=record.severity_score,
                    economic_impact_usd=0.0,
                    capital_required_usd=0.0,
                    reproducibility=1.0,
                    parameters=record.parameters,
                    invariant_violations=[],
                    reproduction_steps=[],
                    evidence_grade=record.evidence_grade,
                    evidence_grade_label=record.evidence_grade_label,
                    axis_survival_rate=record.axis_survival_rate,
                    priority_score=record.priority_score,
                    novelty_score=record.novelty_score,
                    reproduction_tier=record.reproduction_tier,
                    deployed_viable=record.deployed_viable,
                    catalog_analogue=record.catalog_analogue,
                )
            )
        ranked = rank_findings_by_bounty_score(findings, min_readiness=min_score, min_evidence_grade=3)
        payload = [
            {
                "hypothesis_id": s.finding.hypothesis_id if hasattr(s.finding, "hypothesis_id") else s.finding.finding_id,
                "finding_id": s.finding.finding_id,
                "template_id": s.finding.template_id,
                "target_id": s.finding.target_id,
                "bounty_readiness": s.score.bounty_readiness,
                "expected_payout_proxy_usd": s.score.expected_payout_proxy_usd,
                "submission_recommendation": s.score.submission_recommendation,
            }
            for s in ranked[:50]
        ]
        print(json.dumps({"bounty_ready": payload, "count": len(payload)}, indent=2))
        return 0

    if campaign_id:
        print(json.dumps(campaign_stats(store, campaign_id), indent=2))
        return 0
    if stats_only or not hypothesis_id:
        print(json.dumps(lineage_survival_stats(store), indent=2))
        if not hypothesis_id:
            print(json.dumps(best_evidence_per_lineage_root(store), indent=2, default=str))
        return 0

    print(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "ancestors": ancestors(store, hypothesis_id),
                "descendants": descendants(store, hypothesis_id),
            },
            indent=2,
        )
    )
    return 0


def _cmd_disclose(input_path: Path, finding_id: str | None, status: str | None, report_only: bool) -> int:
    if report_only:
        findings, _ = findings_from_run_json(input_path)
        report = build_disclosure_report(findings)
        print(json.dumps(report, indent=2))
        return 0

    if not finding_id or not status:
        print("disclose requires --finding-id and --status (or --report)", file=__import__("sys").stderr)
        return 1

    result = update_disclosure_status(input_path, finding_id, status)
    print(f"Updated {result['finding_id']} → {result['disclosure_status']}")
    findings, run_meta = findings_from_run_json(input_path)
    export_dataset(findings, run_meta, input_path.parent.parent, candidates=None)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Night Shift Security — adversarial protocol vulnerability research"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config JSON (default: built-in config/default.json)",
    )
    parser.add_argument(
        "--proposals",
        type=Path,
        default=None,
        help="Hermes external proposals JSON (enables llm_expansion.provider=external)",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("run", help="Run the full security pipeline (default)")

    serve_parser = subparsers.add_parser("serve", help="Serve public findings API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/security_results/dataset/latest.json"),
        help="Path to exported latest.json feed",
    )

    export_parser = subparsers.add_parser("export", help="Export dataset from a prior run JSON")
    export_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to findings.json from a pipeline run",
    )
    export_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results"),
        help="Directory for dataset/ and bridge/ artifacts",
    )

    disclose_parser = subparsers.add_parser("disclose", help="Manage responsible disclosure status")
    disclose_parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to findings.json from a pipeline run",
    )
    disclose_parser.add_argument("--finding-id", default=None, help="Finding ID to update")
    disclose_parser.add_argument(
        "--status",
        choices=["draft", "embargoed", "disclosed", "redacted"],
        default=None,
        help="New disclosure status",
    )
    disclose_parser.add_argument(
        "--report",
        action="store_true",
        help="Print disclosure summary report without mutating files",
    )

    bounty_parser = subparsers.add_parser("bounty", help="Bug-bounty export and scoring")
    bounty_sub = bounty_parser.add_subparsers(dest="bounty_action", required=True)

    bounty_export = bounty_sub.add_parser("export", help="Export bug-bounty submission pack")
    bounty_export.add_argument("--input", type=Path, required=True)
    bounty_export.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    bounty_export.add_argument("--min-severity", default="high", choices=["low", "medium", "high", "critical"])
    bounty_export.add_argument(
        "--immunefi",
        action="store_true",
        help="Also emit Immunefi-style markdown + reproduction script packs",
    )

    bounty_score = bounty_sub.add_parser("score", help="Score findings by bounty readiness")
    bounty_score.add_argument("--input", type=Path, required=True)
    bounty_score.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    bounty_score.add_argument("--min-score", type=float, default=0.0, help="Min bounty_readiness (0-1)")
    bounty_score.add_argument("--min-evidence-grade", type=int, default=3)
    bounty_score.add_argument("--append", action="store_true", help="Append to bounty_candidates.jsonl")

    bounty_loop = bounty_sub.add_parser(
        "loop",
        help="Autonomous Immunefi+Cantina hunt until submit_now qualifies (human gate)",
    )
    bounty_loop.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Max loop ticks per invocation (default: 1)",
    )
    bounty_loop.add_argument(
        "--trials",
        type=int,
        default=None,
        help="Independent attempts on the same target before advancing queue (e.g. 30)",
    )
    bounty_loop.add_argument(
        "--no-stop-on-submit",
        action="store_true",
        help="Continue after submit_ready (default: stop and write alert)",
    )
    bounty_loop.add_argument(
        "--refresh-scan",
        action="store_true",
        help="Re-run unified bounty scan before picking target",
    )
    bounty_loop.add_argument("--min-bounty", type=int, default=250_000, help="Min max bounty USD")
    bounty_loop.add_argument("--min-grade", type=int, default=1, help="Min scan evidence grade")
    bounty_loop.add_argument(
        "--state",
        type=Path,
        default=Path("data/security_results/loop/state.json"),
        help="Loop state JSON path",
    )
    bounty_loop.add_argument(
        "--scan",
        type=Path,
        default=Path("data/security_results/bounty_scan/latest.json"),
        help="Unified scan report (used when not --refresh-scan)",
    )
    bounty_loop.add_argument(
        "--target",
        default=None,
        help="Force a program slug; required for target-pinned proposal execution",
    )

    semantic_parser = subparsers.add_parser("semantic", help="Semantic recon and concrete candidates")
    semantic_sub = semantic_parser.add_subparsers(dest="semantic_action", required=True)
    semantic_map = semantic_sub.add_parser("map", help="Build code-aware semantic artifacts")
    semantic_map.add_argument("--slug", required=True, help="Target slug")
    semantic_map.add_argument("--repo", type=Path, required=True, help="Target repository root")
    semantic_map.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default data/security_results/semantic/{slug})",
    )
    semantic_map.add_argument("--kind", default=None, help="Optional candidate family filter")
    semantic_map.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/concrete_candidates.jsonl"),
        help="Upsert candidate seeds into this JSONL store",
    )

    semantic_candidates = semantic_sub.add_parser("candidates", help="Build candidate seeds from code_map.json")
    semantic_candidates.add_argument("--slug", required=True, help="Target slug")
    semantic_candidates.add_argument(
        "--semantic-dir",
        type=Path,
        default=None,
        help="Semantic artifact directory (default data/security_results/semantic/{slug})",
    )
    semantic_candidates.add_argument("--kind", default=None, help="Optional candidate family filter")
    semantic_candidates.add_argument("--from-opengrep", action="store_true", help="Reserved for opengrep joins")
    semantic_candidates.add_argument("--output", type=Path, default=None)
    semantic_candidates.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/concrete_candidates.jsonl"),
        help="Upsert candidate seeds into this JSONL store",
    )

    tools_parser = subparsers.add_parser("tools", help="External tool ingestion")
    tools_sub = tools_parser.add_subparsers(dest="tools_action", required=True)
    tools_opengrep = tools_sub.add_parser("opengrep", help="Run Opengrep/Semgrep and ingest SARIF")
    tools_opengrep.add_argument("--slug", required=True)
    tools_opengrep.add_argument("--repo", type=Path, required=True)
    tools_opengrep.add_argument("--rules", type=Path, default=Path("rules/nss"))
    tools_opengrep.add_argument("--out", type=Path, default=None)
    tools_opengrep.add_argument("--semantic-dir", type=Path, default=None)
    tools_opengrep.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/concrete_candidates.jsonl"),
    )
    tools_opengrep.add_argument("--tool", default=None, help="Explicit opengrep/semgrep binary path")
    tools_offchain = tools_sub.add_parser("offchain", help="Run scoped off-chain recon tooling")
    tools_offchain.add_argument("--tool-name", required=True, choices=["bbot", "spiderfoot", "strix", "caido"])
    tools_offchain.add_argument("--scope", type=Path, required=True, help="JSON scope file enabling web/API/domain")
    tools_offchain.add_argument("--out", type=Path, default=Path("data/security_results/offchain"))
    tools_offchain.add_argument("--target", default=None, help="Override scoped domain/API target")

    poc_parser = subparsers.add_parser("poc", help="Generate and verify candidate-specific PoCs")
    poc_sub = poc_parser.add_subparsers(dest="poc_action", required=True)
    poc_generate = poc_sub.add_parser("generate", help="Generate a candidate-specific verifier")
    poc_generate.add_argument("--candidate-id", required=True)
    poc_generate.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/concrete_candidates.jsonl"),
    )
    poc_generate.add_argument("--foundry-root", type=Path, default=Path("foundry/generated"))
    poc_generate.add_argument("--solana-root", type=Path, default=Path("solana/generated"))

    poc_verify = poc_sub.add_parser("verify", help="Run a generated candidate verifier")
    poc_verify.add_argument("--candidate-id", required=True)
    poc_verify.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/concrete_candidates.jsonl"),
    )
    poc_verify.add_argument("--artifact", type=Path, default=None)
    poc_verify.add_argument("--output-dir", type=Path, default=Path("data/security_results/poc"))

    traces_parser = subparsers.add_parser("traces", help="Failure trace summarization and RSI hints")
    traces_sub = traces_parser.add_subparsers(dest="traces_action", required=True)
    traces_summary = traces_sub.add_parser("summarize", help="Summarize failed traces for a target")
    traces_summary.add_argument("--slug", required=True)
    traces_summary.add_argument("--traces-dir", type=Path, default=Path("data/security_results/traces"))
    traces_summary.add_argument(
        "--signatures",
        type=Path,
        default=Path("data/security_results/knowledge/failure_signatures.jsonl"),
    )
    traces_summary.add_argument(
        "--hints",
        type=Path,
        default=Path("data/security_results/loop/refinement_hints.json"),
    )

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan curated Immunefi + Cantina programs (shoestring / zero-RPC)",
    )
    scan_parser.add_argument(
        "--platform",
        default="immunefi",
        choices=["immunefi", "cantina", "all"],
        help="Bounty platform filter (default: immunefi for cron compat)",
    )
    scan_parser.add_argument("--ecosystem", default=None, choices=["solana", "evm", "multichain", "stacks"])
    scan_parser.add_argument("--min-bounty", type=int, default=0, help="Min max bounty USD")
    scan_parser.add_argument("--limit", type=int, default=None, help="Max programs to scan")
    scan_parser.add_argument("--list", action="store_true", dest="list_only", help="List programs only")

    investigate_parser = subparsers.add_parser(
        "investigate",
        help="Deep-dive top Immunefi scan targets (full pipeline per program)",
    )
    investigate_parser.add_argument(
        "--scan",
        type=Path,
        default=Path("data/security_results/immunefi_scan/latest.json"),
        help="Scan report JSON (default: latest immunefi scan)",
    )
    investigate_parser.add_argument("--top", type=int, default=2, help="Max programs to investigate")
    investigate_parser.add_argument("--min-grade", type=int, default=2, help="Min scan evidence grade")
    investigate_parser.add_argument(
        "--ecosystem",
        default="solana",
        choices=["solana", "evm", "multichain", "stacks", "all"],
    )
    investigate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected targets without running pipeline",
    )
    investigate_parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="SLUG",
        help="Skip program slug(s) when ranking targets (repeatable)",
    )

    submission_parser = subparsers.add_parser(
        "submission",
        help="Export single zero-RPC shoestring submission pack (best Level 4+ finding)",
    )
    submission_parser.add_argument("--input", type=Path, required=True)
    submission_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    submission_parser.add_argument("--min-evidence-grade", type=int, default=4)

    platform_parser = subparsers.add_parser(
        "platform",
        help="Sync Immunefi/Cantina listings and diff against curated registry",
    )
    platform_sub = platform_parser.add_subparsers(dest="platform_action", required=True)
    platform_sync = platform_sub.add_parser("sync", help="Sync live platform listings to JSON")
    platform_sync.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    platform_sync.add_argument(
        "--all",
        action="store_true",
        help="Sync Immunefi + Cantina (default behavior)",
    )
    platform_sync.add_argument(
        "--skip-network",
        action="store_true",
        help="Reuse existing platform JSON on disk",
    )
    platform_diff_parser = platform_sub.add_parser("diff", help="Show curated vs live listing gaps")
    platform_diff_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    solodit_sync_parser = platform_sub.add_parser("solodit-sync", help="Sync Cyfrin Solodit findings corpus")
    solodit_sync_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    solodit_sync_parser.add_argument(
        "--scope",
        choices=["target-plus-pattern", "targets-only", "broad-high-quality"],
        default="target-plus-pattern",
    )
    solodit_sync_parser.add_argument("--max-pages", type=int, default=2)
    solodit_sync_parser.add_argument("--page-size", type=int, default=100)
    solodit_sync_parser.add_argument("--min-quality", type=int, default=3)
    solodit_patterns_parser = platform_sub.add_parser(
        "solodit-patterns",
        help="Distill synced Solodit findings into compact pattern JSONL",
    )
    solodit_patterns_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    solodit_patterns_parser.add_argument("--input", type=Path, default=None)
    solodit_patterns_parser.add_argument(
        "--patterns-output",
        type=Path,
        default=Path("data/security_results/knowledge/solodit_patterns.jsonl"),
    )

    auditvault_sync_parser = platform_sub.add_parser(
        "auditvault-sync",
        help="Sync the local Auditware AuditVault repo into normalized JSON",
    )
    auditvault_sync_parser.add_argument(
        "--repo",
        type=Path,
        default=Path("sources/auditvault/repo"),
        help="Path to the local clone of https://github.com/Auditware/AuditVault",
    )
    auditvault_sync_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    auditvault_patterns_parser = platform_sub.add_parser(
        "auditvault-patterns",
        help="Distill AuditVault findings into compact pattern + ids JSONL",
    )
    auditvault_patterns_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    auditvault_patterns_parser.add_argument("--input", type=Path, default=None)
    auditvault_patterns_parser.add_argument(
        "--patterns-output",
        type=Path,
        default=Path("data/security_results/knowledge/auditvault_patterns.jsonl"),
    )
    auditvault_patterns_parser.add_argument(
        "--ids-output",
        type=Path,
        default=Path("data/security_results/knowledge/auditvault_ids.jsonl"),
    )
    auditvault_summary_parser = platform_sub.add_parser(
        "auditvault-summary",
        help="Print non-evidence AuditVault summary metrics for HIPIF dashboards",
    )
    auditvault_summary_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/platform"),
    )
    auditvault_summary_parser.add_argument("--input", type=Path, default=None)

    immunefi_parser = subparsers.add_parser("immunefi", help="Export Immunefi submission packs only")
    immunefi_parser.add_argument("--input", type=Path, required=True)
    immunefi_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    immunefi_parser.add_argument("--min-evidence-grade", type=int, default=3)
    immunefi_parser.add_argument(
        "--min-severity",
        default="high",
        choices=["low", "medium", "high", "critical"],
    )

    monitor_parser = subparsers.add_parser("monitor", help="Emit monitoring alerts from a prior run")
    monitor_parser.add_argument("--input", type=Path, required=True)
    monitor_parser.add_argument("--webhook", default="", help="Optional webhook URL (overrides NIGHT_SHIFT_WEBHOOK_URL)")
    monitor_parser.add_argument("--alert-file", type=Path, default=None)

    dedupe_parser = subparsers.add_parser("dedupe", help="Deduplicate findings from a prior run JSON")
    dedupe_parser.add_argument("--input", type=Path, required=True)
    dedupe_parser.add_argument("--output-dir", type=Path, default=Path("data/security_results"))
    dedupe_parser.add_argument(
        "--re-export",
        action="store_true",
        help="Re-export dataset/ and bridge/ from deduped findings",
    )

    knowledge_parser = subparsers.add_parser("knowledge", help="Query findings store lineage analytics")
    knowledge_parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/findings_store.jsonl"),
        help="Path to findings_store.jsonl",
    )
    knowledge_parser.add_argument(
        "--hypothesis-id",
        default=None,
        help="Inspect lineage for a specific hypothesis ID",
    )
    knowledge_parser.add_argument(
        "--stats",
        action="store_true",
        help="Print aggregate lineage survival stats",
    )
    knowledge_parser.add_argument(
        "--campaign",
        default=None,
        help="Aggregate stats for a campaign_id across runs",
    )
    knowledge_parser.add_argument(
        "--bounty-ready",
        action="store_true",
        help="Rank store records with evidence grade >= 3 by bounty readiness",
    )
    knowledge_parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Min bounty_readiness when using --bounty-ready",
    )

    eval_parser = subparsers.add_parser(
        "eval",
        help="Run LLM hypothesis quality eval (zero-cost mock providers)",
    )
    eval_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results"),
    )

    hipif_parser = subparsers.add_parser(
        "hipif",
        help="HIPIF folded context — hierarchical planning hooks",
    )
    hipif_parser.add_argument(
        "action",
        choices=["init", "read", "parse", "ground", "record", "fold", "next", "status", "gate"],
        help="init | read | parse | ground | record | fold | next | status | gate",
    )
    hipif_parser.add_argument(
        "--context",
        type=Path,
        default=Path("data/security_results/hipif/folded_context.json"),
        help="Folded context JSON path",
    )
    hipif_parser.add_argument("--task", default=None, help="Task description for init")
    hipif_parser.add_argument("--text", default=None, help="Agent turn text for parse")
    hipif_parser.add_argument("--subgoal", default=None, help="Subgoal id for ground/fold")
    hipif_parser.add_argument("--action-cmd", default=None, dest="hipif_action", help="CLI action for ground/record")
    hipif_parser.add_argument("--observation", default=None, help="Observation for record")
    hipif_parser.add_argument("--outcome", default=None, help="Fold outcome summary")
    hipif_parser.add_argument("--metrics", default=None, dest="metrics_json", help="JSON metrics for fold")

    improve_parser = subparsers.add_parser(
        "improve",
        help="Analyze loop state + findings store for deterministic RSI signals",
    )
    improve_parser.add_argument(
        "--loop-state",
        type=Path,
        default=Path("data/security_results/loop/state.json"),
        help="Bounty loop state JSON",
    )
    improve_parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/findings_store.jsonl"),
        help="Findings store JSONL",
    )

    triage_parser = subparsers.add_parser("triage", help="Repo-native discovery triage")
    triage_sub = triage_parser.add_subparsers(dest="triage_action", required=True)

    triage_files = triage_sub.add_parser("files", help="Rank repository files 1–5")
    triage_files.add_argument("--repo", type=Path, required=True, help="Target repository root")
    triage_files.add_argument("--slug", default="", help="Target slug for output naming")
    triage_files.add_argument("--min-score", type=int, default=4, help="Minimum score to include")
    triage_files.add_argument(
        "--output",
        type=Path,
        default=Path("data/security_results/triage/files.json"),
    )

    triage_patches = triage_sub.add_parser("patches", help="Mine security patch shapes from git")
    triage_patches.add_argument("--repo", type=Path, required=True)
    triage_patches.add_argument("--slug", default="")
    triage_patches.add_argument("--max-commits", type=int, default=200)
    triage_patches.add_argument(
        "--output",
        type=Path,
        default=Path("data/security_results/triage/patch_shapes.jsonl"),
    )
    triage_patches.add_argument(
        "--ranked-file",
        action="append",
        default=[],
        dest="ranked_files",
        help="Ranked file path for analogue search (repeatable)",
    )

    triage_wormhole = triage_sub.add_parser(
        "wormhole-map",
        help="Map live Wormhole EVM/Solana program IDs (Block B)",
    )
    triage_wormhole.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Optional cloned wormhole repo for discovery scan",
    )
    triage_wormhole.add_argument(
        "--output",
        type=Path,
        default=Path("data/security_results/triage/wormhole_program_map.json"),
    )
    triage_wormhole.add_argument(
        "--recon-output",
        type=Path,
        default=Path("sources/wormhole/recon.json"),
        help="Write recon JSON with program map + invariants",
    )

    novel_parser = subparsers.add_parser(
        "novel",
        help="Novel candidate scoring and human gate (Block C)",
    )
    novel_sub = novel_parser.add_subparsers(dest="novel_action", required=True)
    novel_score = novel_sub.add_parser("score", help="Score novel findings; write human gate report")
    novel_score.add_argument(
        "--input",
        action="append",
        type=Path,
        required=True,
        dest="inputs",
        help="Findings JSON path (repeatable)",
    )
    novel_score.add_argument(
        "--output",
        type=Path,
        default=Path("data/security_results/novel/human_gate.json"),
    )

    impact_parser = subparsers.add_parser(
        "impact",
        help="Post-PoC impact sizing — oracle arbitrage, TVS maximization",
    )
    impact_sub = impact_parser.add_subparsers(dest="impact_action", required=True)

    impact_oracle = impact_sub.add_parser("oracle", help="Compare oracle vs DEX spot on fork")
    impact_oracle.add_argument("--oracle", required=True, help="Oracle contract address")
    impact_oracle.add_argument("--getter", required=True, help="Price getter signature")
    impact_oracle.add_argument("--pair", required=True, help="Uniswap V2 pair for spot price")
    impact_oracle.add_argument("--rpc-url", default=None)
    impact_oracle.add_argument("--threshold-pct", type=float, default=2.0)
    impact_oracle.add_argument("--token0-decimals", type=int, default=18)
    impact_oracle.add_argument("--token1-decimals", type=int, default=6)

    impact_tvs = impact_sub.add_parser("tvs", help="Rank sibling pools for TVS maximization")
    impact_tvs.add_argument("--base-pool", required=True)
    impact_tvs.add_argument(
        "--siblings",
        type=Path,
        default=Path("src/night_shift_security/config/wormhole_siblings.json"),
    )
    impact_tvs.add_argument("--holder", default=None, help="balanceOf holder for metric")
    impact_tvs.add_argument("--rpc-url", default=None)

    invariants_parser = subparsers.add_parser(
        "invariants",
        help="Semantic invariant tests from recon JSON",
    )
    invariants_sub = invariants_parser.add_subparsers(dest="invariants_action", required=True)
    inv_test = invariants_sub.add_parser("test", help="Run invariant / PBT checks")
    inv_test.add_argument(
        "--from-recon",
        type=Path,
        required=True,
        help="Recon JSON path (e.g. sources/kamino/recon.json)",
    )
    inv_test.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/security_results/invariants"),
    )
    inv_test.add_argument(
        "--no-hypothesis",
        action="store_true",
        help="Skip Hypothesis engine (deterministic only)",
    )
    inv_test.add_argument("--max-examples", type=int, default=50)

    operator_parser = subparsers.add_parser(
        "operator",
        help="Operator layer — execution tools, checkpoint, sandbox",
    )
    operator_sub = operator_parser.add_subparsers(dest="operator_action", required=True)

    op_forge = operator_sub.add_parser("forge-test", help="Run forge test via operator tool")
    op_forge.add_argument("--match-test", required=True)
    op_forge.add_argument("--fork-block", type=int, default=None)
    op_forge.add_argument("--fork-url", default=None)

    op_cast = operator_sub.add_parser("cast-call", help="Run cast call on fork RPC")
    op_cast.add_argument("--to", required=True)
    op_cast.add_argument("--sig", required=True, dest="signature")
    op_cast.add_argument("--arg", action="append", default=[], dest="args_list")
    op_cast.add_argument("--rpc-url", default=None)
    op_cast.add_argument("--from-addr", default=None)

    op_anvil = operator_sub.add_parser("anvil", help="Start/stop local Anvil fork")
    op_anvil.add_argument("anvil_action", choices=["start", "stop"])
    op_anvil.add_argument("--fork-block", type=int, default=None)
    op_anvil.add_argument("--fork-url", default=None)
    op_anvil.add_argument("--docker", action="store_true", help="Use Docker sandbox")

    op_sandbox = operator_sub.add_parser("sandbox", help="Docker Anvil sandbox lifecycle")
    op_sandbox.add_argument("sandbox_action", choices=["start", "stop", "status"])
    op_sandbox.add_argument("--fork-block", type=int, default=None)
    op_sandbox.add_argument("--fork-url", default=None)

    op_slither = operator_sub.add_parser("slither", help="Slither scan on triage-ranked files")
    op_slither.add_argument("--repo", type=Path, required=True)
    op_slither.add_argument("--triage-json", type=Path, default=None)
    op_slither.add_argument("--min-score", type=int, default=4)
    op_slither.add_argument("--file", action="append", default=[], dest="files")

    op_checkpoint = operator_sub.add_parser("checkpoint", help="Read/write/clear operator checkpoint")
    op_checkpoint.add_argument(
        "action",
        choices=["read", "write", "clear"],
        help="read | write | clear",
    )
    op_checkpoint.add_argument(
        "--path",
        type=Path,
        default=Path("data/security_results/operator/checkpoint.json"),
        help="Checkpoint JSON path",
    )
    op_checkpoint.add_argument("--target-slug", default="", help="Target slug (write)")
    op_checkpoint.add_argument("--hypothesis", default="", help="Active hypothesis (write)")
    op_checkpoint.add_argument(
        "--reason",
        default="manual",
        choices=["rollover", "manual", "pre_shutdown"],
        help="Context reason (write)",
    )
    op_checkpoint.add_argument(
        "--next",
        action="append",
        default=[],
        dest="next_commands",
        help="Next command to run (repeatable)",
    )

    coordinator_parser = subparsers.add_parser(
        "coordinator",
        help="Deterministic mission coordinator (Layer 6 orchestration)",
    )
    coordinator_parser.add_argument(
        "action",
        choices=["init", "status", "plan", "cycle"],
        help="init | status | plan | cycle",
    )
    coordinator_parser.add_argument(
        "--state",
        type=Path,
        default=default_state_path(),
        help="Path to coordinator_state.json",
    )
    coordinator_parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/security_results/knowledge/findings_store.jsonl"),
        help="Path to findings_store.jsonl",
    )
    coordinator_parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Max missions for plan (default: 3)",
    )
    coordinator_parser.add_argument(
        "--campaign",
        default=None,
        help="Filter status by campaign_id (reserved)",
    )

    native_parser = subparsers.add_parser(
        "native",
        help="v5 NativeHarness status — preconditions for live on-chain bug discovery",
    )
    native_sub = native_parser.add_subparsers(dest="native_action", required=True)

    native_status = native_sub.add_parser("status", help="Show current native-harness manifest")
    native_status.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/security_results/loop/native_harness_status.json"),
    )

    native_upsert = native_sub.add_parser(
        "mark",
        help="Upsert a target's harness status (missing|mapped|harness_built|ready|paused)",
    )
    native_upsert.add_argument("--slug", required=True)
    native_upsert.add_argument("--name", default="")
    native_upsert.add_argument("--platform", default="immunefi", choices=["immunefi", "cantina"])
    native_upsert.add_argument("--chain", default="ethereum")
    native_upsert.add_argument("--contract-address", default="")
    native_upsert.add_argument("--source-commit", default="")
    native_upsert.add_argument(
        "--status",
        required=True,
        choices=["missing", "mapped", "harness_built", "ready", "paused"],
    )
    native_upsert.add_argument("--notes", default="")
    native_upsert.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/security_results/loop/native_harness_status.json"),
    )

    args = parser.parse_args()

    try:
        if args.command == "serve":
            sys.exit(_cmd_serve(args.host, args.port, args.dataset))
        if args.command == "export":
            sys.exit(_cmd_export(args.input, args.output_dir))
        if args.command == "disclose":
            sys.exit(_cmd_disclose(args.input, args.finding_id, args.status, args.report))
        if args.command == "bounty":
            if args.bounty_action == "score":
                sys.exit(
                    _cmd_bounty_score(
                        args.input,
                        args.output_dir,
                        args.min_score,
                        args.min_evidence_grade,
                        args.append,
                    )
                )
            if args.bounty_action == "loop":
                sys.exit(
                    _cmd_bounty_loop(
                        args.iterations,
                        args.trials,
                        not args.no_stop_on_submit,
                        args.refresh_scan,
                        args.min_bounty,
                        args.min_grade,
                        args.state,
                        args.scan,
                        args.config,
                        args.proposals,
                        args.target,
                    )
                )
            sys.exit(
                _cmd_bounty_export(args.input, args.output_dir, args.min_severity, args.immunefi)
            )
        if args.command == "semantic":
            if args.semantic_action == "map":
                sys.exit(_cmd_semantic_map(args.slug, args.repo, args.out, args.kind, args.store))
            if args.semantic_action == "candidates":
                sys.exit(
                    _cmd_semantic_candidates(
                        args.slug,
                        args.semantic_dir,
                        args.kind,
                        args.output,
                        args.store,
                    )
                )
        if args.command == "tools":
            if args.tools_action == "opengrep":
                sys.exit(
                    _cmd_tools_opengrep(
                        args.slug,
                        args.repo,
                        args.rules,
                        args.out,
                        args.semantic_dir,
                        args.store,
                        args.tool,
                    )
                )
            if args.tools_action == "offchain":
                sys.exit(_cmd_tools_offchain(args.tool_name, args.scope, args.out, args.target))
        if args.command == "poc":
            if args.poc_action == "generate":
                sys.exit(
                    _cmd_poc_generate(
                        args.candidate_id,
                        args.store,
                        args.foundry_root,
                        args.solana_root,
                    )
                )
            if args.poc_action == "verify":
                sys.exit(_cmd_poc_verify(args.candidate_id, args.store, args.artifact, args.output_dir))
        if args.command == "traces":
            if args.traces_action == "summarize":
                sys.exit(
                    _cmd_traces_summarize(
                        args.slug,
                        args.traces_dir,
                        args.signatures,
                        args.hints,
                    )
                )
        if args.command == "scan":
            sys.exit(
                _cmd_scan(
                    args.config,
                    args.ecosystem,
                    args.min_bounty,
                    args.limit,
                    args.list_only,
                    args.platform,
                )
            )
        if args.command == "investigate":
            eco = None if args.ecosystem == "all" else args.ecosystem
            sys.exit(
                _cmd_investigate(
                    args.config,
                    args.scan,
                    args.top,
                    args.min_grade,
                    eco,
                    args.proposals,
                    args.dry_run,
                    args.exclude,
                )
            )
        if args.command == "submission":
            sys.exit(_cmd_submission(args.input, args.output_dir, args.min_evidence_grade))
        if args.command == "platform":
            skip_net = getattr(args, "skip_network", False)
            sys.exit(
                _cmd_platform(
                    args.platform_action,
                    args.output_dir,
                    skip_net,
                    max_pages=getattr(args, "max_pages", 2),
                    page_size=getattr(args, "page_size", 100),
                    scope=getattr(args, "scope", "target-plus-pattern"),
                    min_quality=getattr(args, "min_quality", 3),
                    input_path=getattr(args, "input", None),
                    patterns_output=getattr(args, "patterns_output", None),
                    auditvault_repo=getattr(args, "repo", None),
                    auditvault_input=getattr(args, "input", None),
                    auditvault_patterns_output=getattr(args, "patterns_output", None),
                    auditvault_ids_output=getattr(args, "ids_output", None),
                )
            )
        if args.command == "immunefi":
            sys.exit(
                _cmd_immunefi(
                    args.input,
                    args.output_dir,
                    args.min_evidence_grade,
                    args.min_severity,
                )
            )
        if args.command == "monitor":
            sys.exit(_cmd_monitor(args.input, args.webhook, args.alert_file))
        if args.command == "dedupe":
            sys.exit(_cmd_dedupe(args.input, args.output_dir, args.re_export))
        if args.command == "knowledge":
            sys.exit(
                _cmd_knowledge(
                    args.store,
                    args.hypothesis_id,
                    args.stats,
                    args.campaign,
                    args.bounty_ready,
                    args.min_score,
                )
            )
        if args.command == "eval":
            result = run_llm_quality_eval(output_dir=args.output_dir)
            print(json.dumps(result, indent=2))
            sys.exit(0)
        if args.command == "hipif":
            sys.exit(
                _cmd_hipif(
                    args.action,
                    task=args.task,
                    context_path=args.context,
                    text=args.text,
                    subgoal=args.subgoal,
                    hipif_action=args.hipif_action,
                    observation=args.observation,
                    outcome=args.outcome,
                    metrics_json=args.metrics_json,
                )
            )
        if args.command == "improve":
            sys.exit(_cmd_improve(args.loop_state, args.store))
        if args.command == "triage":
            if args.triage_action == "wormhole-map":
                sys.exit(
                    _cmd_triage_wormhole_map(
                        args.repo,
                        args.output,
                        args.recon_output,
                    )
                )
            if args.triage_action == "files":
                slug = args.slug or args.repo.name
                out = args.output
                if args.slug and str(out).endswith("files.json"):
                    out = args.output.parent / f"{slug}_files.json"
                sys.exit(_cmd_triage_files(args.repo, slug, args.min_score, out))
            slug = args.slug or args.repo.name
            out = args.output
            if args.slug and str(out).endswith("patch_shapes.jsonl"):
                out = args.output.parent / f"{slug}_patch_shapes.jsonl"
            sys.exit(
                _cmd_triage_patches(
                    args.repo,
                    slug,
                    args.max_commits,
                    out,
                    args.ranked_files,
                )
            )
        if args.command == "invariants":
            sys.exit(
                _cmd_invariants_test(
                    args.from_recon,
                    args.output_dir,
                    not args.no_hypothesis,
                    args.max_examples,
                )
            )
        if args.command == "novel":
            sys.exit(_cmd_novel_score(args.inputs, args.output))
        if args.command == "impact":
            if args.impact_action == "oracle":
                sys.exit(
                    _cmd_impact_oracle(
                        args.oracle,
                        args.getter,
                        args.pair,
                        args.rpc_url,
                        args.threshold_pct,
                        args.token0_decimals,
                        args.token1_decimals,
                    )
                )
            sys.exit(
                _cmd_impact_tvs(
                    args.base_pool,
                    args.siblings,
                    args.holder,
                    args.rpc_url,
                )
            )
        if args.command == "operator":
            if args.operator_action == "forge-test":
                sys.exit(
                    _cmd_operator_forge_test(args.match_test, args.fork_block, args.fork_url)
                )
            if args.operator_action == "cast-call":
                sys.exit(
                    _cmd_operator_cast_call(
                        args.to,
                        args.signature,
                        args.args_list,
                        args.rpc_url,
                        args.from_addr,
                    )
                )
            if args.operator_action == "anvil":
                sys.exit(
                    _cmd_operator_anvil(
                        args.anvil_action,
                        args.fork_block,
                        args.fork_url,
                        args.docker,
                    )
                )
            if args.operator_action == "sandbox":
                sys.exit(
                    _cmd_operator_sandbox(
                        args.sandbox_action,
                        args.fork_block,
                        args.fork_url,
                    )
                )
            if args.operator_action == "slither":
                sys.exit(
                    _cmd_operator_slither(
                        args.repo,
                        args.triage_json,
                        args.min_score,
                        args.files,
                    )
                )
            sys.exit(
                _cmd_operator_checkpoint(
                    args.action,
                    args.path,
                    args.target_slug,
                    args.hypothesis,
                    args.reason,
                    args.next_commands,
                )
            )
        if args.command == "coordinator":
            sys.exit(
                _cmd_coordinator(
                    args.action,
                    args.config,
                    args.state,
                    args.store,
                    args.top,
                    args.proposals,
                    args.campaign,
                )
            )
        if args.command == "native":
            if args.native_action == "status":
                sys.exit(_cmd_native_status(args.manifest))
            if args.native_action == "mark":
                sys.exit(
                    _cmd_native_mark(
                        args.manifest,
                        args.slug,
                        args.name,
                        args.platform,
                        args.chain,
                        args.contract_address,
                        args.source_commit,
                        args.status,
                        args.notes,
                    )
                )
        sys.exit(_cmd_run(args.config, args.proposals))
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
