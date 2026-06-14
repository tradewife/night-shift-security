#!/usr/bin/env python3
"""Deterministic HIPIF night chain — bounty-depth profile for long-running hunts.

Set NSS_HIPIF_BOUNTY_DEPTH=1 (default here) to boost fork/validator top_n, samples,
and darwinian depth in build_loop_config.

Env tunables:
  NSS_HIPIF_TRIALS_WORMHOLE (default 12)
  NSS_HIPIF_TRIALS_KAMINO (default 5)
  NSS_HIPIF_HUNT_TARGETS (default 4)
  NSS_HIPIF_HUNT_TRIALS (default 3)
  NSS_HIPIF_HUNT_SLUGS (default fork-ready: kamino,wormhole,morpho,euler,ethena,jito)
  NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS (default 4)
  NSS_HIPIF_CANTINA_SLATES (default reserve-protocol,coinbase,morpho,euler)
  NSS_HIPIF_CANTINA_TRIALS (default 3)
  NSS_HIPIF_REFINE_TOP (default 3)
  NSS_HIPIF_COORD_CYCLES (default 2)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.program_registry import get_program_by_slug
from night_shift_security.orchestration.bounty_loop import (
    klend_live_preflight,
    pick_fork_ready_hunt_slugs,
)

REPO = Path(__file__).resolve().parents[2]
STATE_PATH = REPO / "data/security_results/loop/state.json"
SCAN_PATH = REPO / "data/security_results/bounty_scan/latest.json"
HINTS_PATH = REPO / "data/security_results/loop/refinement_hints.json"
CONTEXT_PATH = REPO / "data/security_results/hipif/folded_context.json"
COORD_STATE = REPO / "data/security_results/knowledge/coordinator_state.json"
ALERT_PATH = REPO / "data/security_results/loop/submission_alert.json"
KAMINO_CFG = "src/night_shift_security/config/kamino_shoestring.json"
WORMHOLE_SHOESTRING_CFG = "src/night_shift_security/config/wormhole_shoestring.json"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(int(raw), 1)
    except ValueError:
        return default


def _py() -> list[str]:
    return [sys.executable, "-m", "night_shift_security.cli.main"]


def run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    t0 = time.monotonic()
    result = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    elapsed = time.monotonic() - t0
    print(f"... elapsed {elapsed:.0f}s", flush=True)
    if result.stdout:
        tail = result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout
        print(tail, flush=True)
    if result.stderr:
        print(result.stderr[-2000:], file=sys.stderr, flush=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def nss_cmd(*parts: str, config: str | None = None, proposals: str | None = None) -> list[str]:
    cmd = _py()
    if config:
        cmd += ["--config", config]
    if proposals:
        cmd += ["--proposals", proposals]
    cmd += list(parts)
    return cmd


def hipif_fold(outcome: str, metrics: dict | None = None, *, subgoal: str | None = None) -> dict:
    cmd = nss_cmd("hipif", "fold", "--outcome", outcome)
    if subgoal:
        cmd += ["--subgoal", subgoal]
    if metrics:
        cmd += ["--metrics", json.dumps(metrics)]
    run(cmd)
    return json.loads(CONTEXT_PATH.read_text())


def last_run() -> dict:
    if not STATE_PATH.is_file():
        return {}
    state = json.loads(STATE_PATH.read_text())
    runs = state.get("runs") or []
    return runs[-1] if runs else {}


def loop_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    return json.loads(STATE_PATH.read_text())


def submit_ready() -> bool:
    if not ALERT_PATH.is_file():
        return False
    try:
        return json.loads(ALERT_PATH.read_text()).get("status") == "submit_ready"
    except (json.JSONDecodeError, OSError):
        return False


def depth_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    env["NSS_HIPIF_BOUNTY_DEPTH"] = "1"
    env.setdefault("NSS_KLEND_FIXTURE", "0")
    return env


def bounty_depth(
    slug: str,
    *,
    trials: int,
    label: str,
    extra_env: dict[str, str] | None = None,
    fold_subgoal: str | None = None,
) -> dict:
    env = depth_env()
    env["NSS_LOOP_DEPTH_SLUG"] = slug
    if extra_env:
        env.update(extra_env)
    run(
        ["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1", "--trials", str(trials)],
        env=env,
    )
    r = last_run()
    metrics = {
        "slug": r.get("slug"),
        "trials": trials,
        "fork_reproduced": r.get("fork_reproduced", 0),
        "solana_reproduced": r.get("solana_reproduced", 0),
        "findings": r.get("findings", 0),
        "label": label,
    }
    if fold_subgoal is None:
        return metrics
    return hipif_fold(f"{label} depth ({slug}) {trials} trials", metrics, subgoal=fold_subgoal)


def wormhole_core_bridge_refinement(*, trials: int) -> dict:
    """Pin Wormhole core/token_bridge via triage proposals + shoestring config."""
    script = REPO / "hermes/scripts/nss-write-wormhole-triage-proposals.py"
    proposals = REPO / "data/security_results/hermes_proposals/latest.json"
    wrote = False
    if script.is_file():
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout[-2000:], flush=True)
        if result.returncode != 0 and result.stderr:
            print(result.stderr[-2000:], file=sys.stderr, flush=True)
        wrote = proposals.is_file()
    env = depth_env()
    env["NSS_LOOP_DEPTH_SLUG"] = "wormhole"
    if wrote:
        run(
            nss_cmd(
                "bounty",
                "loop",
                "--iterations",
                "1",
                "--trials",
                str(trials),
                config=WORMHOLE_SHOESTRING_CFG,
                proposals=str(proposals),
            ),
            env=env,
        )
        mode = "triage_proposals"
    else:
        run(
            nss_cmd(
                "bounty",
                "loop",
                "--iterations",
                "1",
                "--trials",
                str(trials),
                config=WORMHOLE_SHOESTRING_CFG,
            ),
            env=env,
        )
        mode = "shoestring_depth_pin"
    r = last_run()
    metrics = {
        "trials": trials,
        "mode": mode,
        "proposals": wrote,
        "slug": r.get("slug"),
        "fork_reproduced": r.get("fork_reproduced", 0),
        "findings": r.get("findings", 0),
        "targets": "wormhole-core-ethereum,wormhole-token-bridge-ethereum",
    }
    return hipif_fold("wormhole core/token_bridge refinement", metrics, subgoal="depth_wormhole_bridge")


def hunt_rotation(*, targets: int, trials: int) -> dict:
    env = depth_env()
    env.pop("NSS_LOOP_DEPTH_SLUG", None)
    state = loop_state()
    hunt_env = os.environ.get("NSS_HIPIF_HUNT_SLUGS", "").strip()
    picked = pick_fork_ready_hunt_slugs(
        max_targets=targets,
        exclude_slugs=list(state.get("saturated_slugs") or []),
        env_override=hunt_env or None,
        ignore_saturation=True,
    )

    metrics: dict = {
        "targets_requested": targets,
        "trials_each": trials,
        "slugs": picked,
        "fork_ready_only": True,
        "ignore_saturation": True,
    }
    for slug in picked:
        if submit_ready():
            break
        env_h = depth_env()
        env_h["NSS_LOOP_DEPTH_SLUG"] = slug
        if slug == "ethena":
            write_proposals_for_slug(slug)
            proposals = REPO / "data/security_results/hermes_proposals/latest.json"
            if proposals.is_file():
                run(
                    nss_cmd(
                        "bounty",
                        "loop",
                        "--iterations",
                        "1",
                        "--trials",
                        str(trials),
                        proposals=str(proposals),
                    ),
                    env=env_h,
                )
                metrics[f"{slug}_mode"] = "proposals"
            else:
                run(
                    ["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1", "--trials", str(trials)],
                    env=env_h,
                )
                metrics[f"{slug}_mode"] = "depth_pin"
        else:
            run(
                ["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1", "--trials", str(trials)],
                env=env_h,
            )
            metrics[f"{slug}_mode"] = "depth_pin"
        r = last_run()
        metrics[f"{slug}_fork"] = r.get("fork_reproduced", 0)
        metrics[f"{slug}_findings"] = r.get("findings", 0)

    if not picked:
        run(
            ["hermes/scripts/nss-bounty-loop.sh", "--iterations", str(targets), "--trials", str(trials)],
            env=env,
        )
        r = last_run()
        metrics["fallback_slug"] = r.get("slug")

    r = last_run()
    metrics.update(
        {
            "last_slug": r.get("slug"),
            "fork_reproduced": r.get("fork_reproduced", 0),
            "findings": r.get("findings", 0),
        }
    )
    return hipif_fold("multi-target hunt rotation", metrics, subgoal="hunt_rotation")


def write_proposals_for_slug(slug: str) -> bool:
    program = get_program_by_slug(slug) or get_program_by_slug(slug, platform="cantina")
    if program is None or program.platform != "immunefi":
        return False
    script = REPO / "hermes/scripts/nss-write-scan-proposals.py"
    if not script.is_file():
        return False
    result = subprocess.run(
        [sys.executable, str(script), "--slug", slug],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr, flush=True)
        return False
    if result.stdout:
        print(result.stdout[-2000:], flush=True)
    return (REPO / "data/security_results/hermes_proposals/latest.json").is_file()


def refinement_passes(top_n: int, *, trials: int = 2) -> dict:
    state = loop_state()
    queue = list(state.get("refinement_queue") or [])
    if not queue and HINTS_PATH.is_file():
        hints = json.loads(HINTS_PATH.read_text())
        top = hints.get("top")
        if top:
            queue = [top]

    passes: list[dict] = []
    for entry in queue[:top_n]:
        slug = str(entry.get("slug") or "")
        if not slug:
            continue
        wrote = write_proposals_for_slug(slug)
        proposals = REPO / "data/security_results/hermes_proposals/latest.json"
        env = depth_env()
        if wrote and proposals.is_file():
            run(
                nss_cmd("bounty", "loop", "--iterations", "1", "--trials", str(trials), proposals=str(proposals)),
                env=env,
            )
            mode = "proposals"
        else:
            env["NSS_LOOP_DEPTH_SLUG"] = slug
            run(
                ["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1", "--trials", str(trials)],
                env=env,
            )
            mode = "depth_pin"
        r = last_run()
        passes.append(
            {
                "slug": slug,
                "template": entry.get("template_id"),
                "mode": mode,
                "target": r.get("slug"),
                "fork_reproduced": r.get("fork_reproduced", 0),
            }
        )
        if submit_ready():
            break

    return hipif_fold(
        f"refinement {len(passes)} passes",
        {"passes": passes, "count": len(passes)},
        subgoal="refine_conditional",
    )


def coordinator_depth(cycles: int) -> dict:
    if not COORD_STATE.is_file():
        return hipif_fold(
            "coordinator skipped",
            {"reason": "no coordinator state"},
            subgoal="coordinator_conditional",
        )
    done = 0
    for i in range(cycles):
        if submit_ready():
            break
        run(nss_cmd("coordinator", "plan", "--top", "1", config=KAMINO_CFG))
        proposals = REPO / "data/security_results/hermes_proposals/latest.json"
        prop = str(proposals) if proposals.is_file() else None
        run(nss_cmd("coordinator", "cycle", config=KAMINO_CFG, proposals=prop))
        done += 1
    return hipif_fold("coordinator depth", {"cycles": done}, subgoal="coordinator_conditional")


def write_lab_notebook(ctx: dict, *, elapsed_s: float) -> Path:
    nb_dir = REPO / "data/security_results/lab_notebook"
    nb_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = nb_dir / f"{date}-hipif-bounty-depth-run.md"
    last = last_run()
    folds = ctx.get("folded_history") or []
    lines = [
        "# Lab entry — HIPIF bounty-depth chain\n",
        f"- wall_time_s: {elapsed_s:.0f}",
        f"- bounty_depth: NSS_HIPIF_BOUNTY_DEPTH=1",
        f"- klend_live: NSS_KLEND_FIXTURE=0",
        "\n## Folded history\n",
    ]
    for rec in folds:
        if isinstance(rec, dict):
            m = rec.get("metrics") or {}
            metric_str = " ".join(f"{k}={v}" for k, v in m.items() if v is not None and k != "passes")
            lines.append(f"- **{rec.get('subgoal_id')}**: {rec.get('outcome_summary')} {metric_str}".rstrip())
    lines += [
        "\n## Last pipeline",
        f"- slug: {last.get('slug', '')}",
        f"- fork_reproduced: {last.get('fork_reproduced', '')}",
        f"- solana_reproduced: {last.get('solana_reproduced', '')}",
        f"- findings: {last.get('findings', '')}",
        f"- submit_ready: {submit_ready()}",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def run_chain() -> dict:
    t0 = time.monotonic()
    trials_wh = _env_int("NSS_HIPIF_TRIALS_WORMHOLE", 12)
    trials_km = _env_int("NSS_HIPIF_TRIALS_KAMINO", 5)
    bridge_trials = _env_int("NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS", 4)
    hunt_targets = _env_int("NSS_HIPIF_HUNT_TARGETS", 4)
    hunt_trials = _env_int("NSS_HIPIF_HUNT_TRIALS", 3)
    cantina_slates = [
        s.strip()
        for s in os.environ.get(
            "NSS_HIPIF_CANTINA_SLATES", "reserve-protocol,coinbase,morpho,euler"
        ).split(",")
        if s.strip()
    ]
    cantina_trials = _env_int("NSS_HIPIF_CANTINA_TRIALS", 3)
    refine_top = _env_int("NSS_HIPIF_REFINE_TOP", 3)
    coord_cycles = _env_int("NSS_HIPIF_COORD_CYCLES", 2)

    hipif_fold("context loaded — bounty depth profile", {"depth": "bounty"}, subgoal="bootstrap")

    run(nss_cmd("scan", "--platform", "all", "--min-bounty", "250000"), env=depth_env())
    hipif_fold("scan complete", {"artifact": "bounty_scan/latest.json"}, subgoal="scan_all")

    bounty_depth("wormhole", trials=trials_wh, label="wormhole", fold_subgoal="depth_wormhole")
    if submit_ready():
        return hipif_fold("submit_ready wormhole", {"submit_ready": True}, subgoal="gate")

    wormhole_core_bridge_refinement(trials=bridge_trials)
    if submit_ready():
        return hipif_fold("submit_ready wormhole bridge", {"submit_ready": True}, subgoal="gate")

    preflight = klend_live_preflight()
    hipif_fold("kamino live preflight", preflight, subgoal="kamino_preflight")
    bounty_depth(
        "kamino",
        trials=trials_km,
        label="kamino",
        extra_env={"KLEND_PROBE": os.environ.get("KLEND_PROBE", "oracle_staleness_borrow")},
        fold_subgoal="depth_kamino",
    )
    if submit_ready():
        return hipif_fold("submit_ready kamino", {"submit_ready": True}, subgoal="gate")

    cantina_results: list[dict] = []
    for slug in cantina_slates:
        if submit_ready():
            break
        m = bounty_depth(slug, trials=cantina_trials, label=f"cantina-{slug}", fold_subgoal=None)
        cantina_results.append(m)
    if cantina_results:
        hipif_fold(
            f"cantina slates ({len(cantina_results)} programs)",
            {"slates": cantina_results, "count": len(cantina_results)},
            subgoal="cantina_slates",
        )

    hunt_rotation(targets=hunt_targets, trials=hunt_trials)
    if submit_ready():
        return hipif_fold("submit_ready hunt", {"submit_ready": True}, subgoal="gate")

    run(nss_cmd("improve"), env=depth_env())
    hipif_fold(
        "RSI aggregated",
        {"refinement_queue": len(loop_state().get("refinement_queue") or [])},
        subgoal="rsi_fold",
    )

    refinement_passes(refine_top, trials=2)
    if submit_ready():
        return hipif_fold("submit_ready refine", {"submit_ready": True}, subgoal="gate")

    coordinator_depth(coord_cycles)

    elapsed = time.monotonic() - t0
    ctx = json.loads(CONTEXT_PATH.read_text())
    nb = write_lab_notebook(ctx, elapsed_s=elapsed)
    hipif_fold(
        "lab notebook",
        {"path": str(nb.relative_to(REPO)), "elapsed_s": int(elapsed)},
        subgoal="journal_fold",
    )

    return hipif_fold(
        "gate",
        {"submit_ready": submit_ready(), "elapsed_s": int(elapsed)},
        subgoal="gate",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HIPIF bounty-depth night chain")
    parser.add_argument("--init", action="store_true", help="hipif init before chain")
    parser.add_argument("--task", default=None, help="Task string for hipif init")
    args = parser.parse_args()

    os.chdir(REPO)
    if args.init:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        task = args.task or f"Bounty-depth chain SPEC v3.1.0 ({month})"
        run(nss_cmd("hipif", "init", "--task", task))

    try:
        ctx = run_chain()
        print("\n=== HIPIF BOUNTY-DEPTH CHAIN COMPLETE ===", flush=True)
        print(
            json.dumps(
                {
                    "chain_status": ctx.get("chain_status"),
                    "folds": len(ctx.get("folded_history", [])),
                    "submit_ready": submit_ready(),
                    "elapsed_s": (ctx.get("folded_history") or [{}])[-1].get("metrics", {}).get("elapsed_s"),
                },
                indent=2,
            )
        )
        return 0
    except RuntimeError as exc:
        print(f"HIPIF chain failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())