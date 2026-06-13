#!/usr/bin/env python3
"""Deterministic HIPIF night chain — no-agent fallback when OAuth unavailable.

Global NSS flags (--config, --proposals) MUST precede the subcommand:
  .venv/bin/python -m night_shift_security.cli.main --proposals PATH bounty loop ...
  .venv/bin/python -m night_shift_security.cli.main --config PATH coordinator cycle
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.program_registry import get_program_by_slug

REPO = Path(__file__).resolve().parents[2]
STATE_PATH = REPO / "data/security_results/loop/state.json"
HINTS_PATH = REPO / "data/security_results/loop/refinement_hints.json"
CONTEXT_PATH = REPO / "data/security_results/hipif/folded_context.json"
COORD_STATE = REPO / "data/security_results/knowledge/coordinator_state.json"
ALERT_PATH = REPO / "data/security_results/loop/submission_alert.json"
KAMINO_CFG = "src/night_shift_security/config/kamino_shoestring.json"


def _py() -> list[str]:
    return [sys.executable, "-m", "night_shift_security.cli.main"]


def run(cmd: list[str], *, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    result = subprocess.run(
        cmd,
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
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


def hipif_fold(outcome: str, metrics: dict | None = None) -> dict:
    cmd = nss_cmd("hipif", "fold", "--outcome", outcome)
    if metrics:
        cmd += ["--metrics", json.dumps(metrics)]
    run(cmd)
    return json.loads((REPO / "data/security_results/hipif/folded_context.json").read_text())


def last_run() -> dict:
    if not STATE_PATH.is_file():
        return {}
    state = json.loads(STATE_PATH.read_text())
    runs = state.get("runs") or []
    return runs[-1] if runs else {}


def load_hints() -> dict:
    if not HINTS_PATH.is_file():
        return {}
    return json.loads(HINTS_PATH.read_text())


def submit_ready() -> bool:
    if not ALERT_PATH.is_file():
        return False
    try:
        return json.loads(ALERT_PATH.read_text()).get("status") == "submit_ready"
    except (json.JSONDecodeError, OSError):
        return False


def write_proposals_for_slug(slug: str) -> bool:
    """Immunefi: parametric scan proposals. Cantina: no script — caller uses depth pin."""
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


def write_lab_notebook(ctx: dict) -> Path:
    nb_dir = REPO / "data/security_results/lab_notebook"
    nb_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = nb_dir / f"{date}-hipif-chain-run.md"
    last = last_run()
    folds = ctx.get("folded_history") or []
    lines = ["# Lab entry — HIPIF chain run\n", "## Folded history\n"]
    for rec in folds:
        if isinstance(rec, dict):
            m = rec.get("metrics") or {}
            metric_str = " ".join(f"{k}={v}" for k, v in m.items() if v is not None)
            lines.append(f"- **{rec.get('subgoal_id')}**: {rec.get('outcome_summary')} {metric_str}".rstrip())
    lines += [
        "\n## Last pipeline",
        f"- slug: {last.get('slug', '')}",
        f"- fork_reproduced: {last.get('fork_reproduced', '')}",
        f"- solana_reproduced: {last.get('solana_reproduced', '')}",
        f"- findings: {last.get('findings', '')}",
        f"- chain_status: {ctx.get('chain_status', '')}",
        f"- submit_ready: {submit_ready()}",
        "\n## Notes",
        "Deterministic runner: hermes/scripts/nss-hipif-chain-run.py",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


def run_chain(*, force_depth: bool = True) -> dict:
    env_base = os.environ.copy()
    env_base.pop("NSS_LOOP_DEPTH_SLUG", None)

    # bootstrap
    hipif_fold("context loaded, lab notebook reviewed", {"status": "ok"})

    # scan
    run(nss_cmd("scan", "--platform", "all", "--min-bounty", "250000"))
    hipif_fold("unified Immunefi+Cantina scan complete", {"artifact": "bounty_scan/latest.json"})

    # wormhole depth
    env_wh = env_base.copy()
    env_wh["NSS_LOOP_DEPTH_SLUG"] = "wormhole"
    run(["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1"], env=env_wh, check=True)
    r = last_run()
    hipif_fold(
        "wormhole triage depth complete",
        {"slug": r.get("slug"), "fork_reproduced": r.get("fork_reproduced", 0), "findings": r.get("findings", 0)},
    )
    if submit_ready():
        return hipif_fold("submit_ready at wormhole depth", {"submit_ready": True})

    # kamino depth
    env_km = env_base.copy()
    env_km["NSS_LOOP_DEPTH_SLUG"] = "kamino"
    run(["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1"], env=env_km)
    r = last_run()
    hipif_fold(
        "kamino klend depth complete",
        {"slug": r.get("slug"), "solana_reproduced": r.get("solana_reproduced", 0), "findings": r.get("findings", 0)},
    )
    if submit_ready():
        return hipif_fold("submit_ready at kamino depth", {"submit_ready": True})

    # hunt
    run(["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1"], env=env_base)
    r = last_run()
    hipif_fold(
        "rotation hunt complete",
        {"slug": r.get("slug"), "fork_reproduced": r.get("fork_reproduced", 0), "findings": r.get("findings", 0)},
    )
    if submit_ready():
        return hipif_fold("submit_ready at hunt", {"submit_ready": True})

    # rsi
    run(nss_cmd("improve"))
    hints = load_hints()
    top = hints.get("top") or {}
    hipif_fold("RSI aggregated", {"hints_slug": top.get("slug", "")})

    # refine
    if top.get("slug"):
        slug = str(top["slug"])
        wrote = write_proposals_for_slug(slug)
        proposals = REPO / "data/security_results/hermes_proposals/latest.json"
        if wrote and proposals.is_file():
            run(nss_cmd("bounty", "loop", "--iterations", "1", proposals=str(proposals)))
            refine_mode = "proposals"
        else:
            env_ref = env_base.copy()
            env_ref["NSS_LOOP_DEPTH_SLUG"] = slug
            run(["hermes/scripts/nss-bounty-loop.sh", "--iterations", "1"], env=env_ref)
            refine_mode = "depth_pin"
        r = last_run()
        hipif_fold(
            "refinement pass",
            {
                "hint_slug": slug,
                "template": top.get("template_id"),
                "refine_target": r.get("slug"),
                "mode": refine_mode,
            },
        )
    else:
        hipif_fold("refinement skipped", {"reason": "no hints"})

    # coordinator
    if top.get("slug") == "kamino" and COORD_STATE.is_file():
        run(nss_cmd("coordinator", "plan", "--top", "1", config=KAMINO_CFG))
        proposals = REPO / "data/security_results/hermes_proposals/latest.json"
        prop = str(proposals) if proposals.is_file() else None
        run(nss_cmd("coordinator", "cycle", config=KAMINO_CFG, proposals=prop))
        hipif_fold("kamino coordinator cycle", {"slug": "kamino"})
    else:
        hipif_fold("coordinator skipped", {"reason": "no kamino mission", "hints_slug": top.get("slug", "")})

    ctx = json.loads(CONTEXT_PATH.read_text())
    nb = write_lab_notebook(ctx)
    hipif_fold("lab notebook written", {"path": str(nb.relative_to(REPO))})

    ctx = hipif_fold("gate checked", {"submit_ready": submit_ready()})
    return ctx


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic HIPIF night chain")
    parser.add_argument("--init", action="store_true", help="hipif init before chain")
    parser.add_argument("--task", default=None, help="Task string for hipif init")
    args = parser.parse_args()

    os.chdir(REPO)
    if args.init:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        task = args.task or f"Night chain SPEC v3.1.0 ({month})"
        run(nss_cmd("hipif", "init", "--task", task))

    try:
        ctx = run_chain()
        print("\n=== HIPIF CHAIN COMPLETE ===", flush=True)
        print(
            json.dumps(
                {
                    "chain_status": ctx.get("chain_status"),
                    "folds": len(ctx.get("folded_history", [])),
                    "submit_ready": submit_ready(),
                },
                indent=2,
            )
        )
        return 0 if not submit_ready() else 0
    except RuntimeError as exc:
        print(f"HIPIF chain failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())