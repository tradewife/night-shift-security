#!/usr/bin/env python3
"""Write scoped hermes_proposals JSON from coordinator plan (parametric refinement variants)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.domain.attack_hypotheses.base import validate_hypothesis
from night_shift_security.domain.attack_hypotheses.base import AttackHypothesis
from night_shift_security.knowledge.findings_store import load_store
from night_shift_security.orchestration.coordinator import (
    default_state_path,
    ensure_pending_missions,
    load_state,
    plan_missions,
    save_state,
)

REPO = Path(__file__).resolve().parents[2]
REFINEMENT_VARIANTS: dict[str, list[dict]] = {
    "flash_loan_oracle": [
        {
            "loan_fraction_of_ceiling": 0.9,
            "price_skew_severity": 1.6,
            "oracle_dependency_score": 0.95,
        },
        {
            "loan_fraction_of_ceiling": 0.12,
            "price_skew_severity": 0.9,
            "oracle_dependency_score": 0.8,
        },
    ],
    "composability_risk": [
        {
            "chain_depth": 0.95,
            "leverage_intensity": 0.85,
            "callback_chain_likelihood": 0.9,
        },
        {
            "chain_depth": 0.4,
            "leverage_intensity": 0.55,
            "callback_chain_likelihood": 0.65,
        },
    ],
    "reentrancy": [
        {
            "recursion_intensity": 0.95,
            "callback_exploitability": 0.9,
            "target_function_preference": "withdraw",
        },
        {
            "recursion_intensity": 0.35,
            "callback_exploitability": 0.7,
            "target_function_preference": "redeem",
        },
    ],
}


def main() -> int:
    state_path = default_state_path()
    store_path = REPO / "data/security_results/knowledge/findings_store.jsonl"
    state = load_state(state_path)
    store = load_store(store_path)
    state = ensure_pending_missions(state, store)
    save_state(state, state_path)

    missions = plan_missions(state, store, top_n=1)
    if not missions:
        print("No missions to scope proposals", file=sys.stderr)
        return 1

    mission = missions[0]
    template = mission.template_id
    seed_id = mission.seed_hypothesis_ids[0] if mission.seed_hypothesis_ids else ""
    variants = REFINEMENT_VARIANTS.get(template, [])
    if not variants:
        print(f"No built-in variants for template {template}", file=sys.stderr)
        return 1

    proposals: list[dict] = []
    for idx, parameters in enumerate(variants):
        hypothesis = AttackHypothesis(
            hypothesis_id=f"proposal-{idx}",
            template=template,
            parameters=parameters,
            metadata={},
        )
        valid, reason = validate_hypothesis(hypothesis)
        if not valid:
            print(f"Skip invalid proposal {idx}: {reason}", file=sys.stderr)
            continue
        entry: dict = {
            "template": template,
            "parameters": parameters,
            "delegate_note": f"coordinator refinement pass {mission.priority_reason}",
        }
        if seed_id:
            entry["seed_id"] = seed_id
            entry["lineage"] = [seed_id]
        proposals.append(entry)

    if not proposals:
        print("All proposals failed validate_hypothesis()", file=sys.stderr)
        return 1

    run_id = f"kamino-refinement-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    doc = {
        "run_id": run_id,
        "campaign_id": state.campaign_id,
        "mission_id": mission.mission_id,
        "template_id": template,
        "proposals": proposals,
    }
    out_dir = REPO / "data/security_results/hermes_proposals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(doc, indent=2) + "\n")
    latest = out_dir / "latest.json"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_path.name)
    print(json.dumps({"path": str(out_path), "mission": mission.to_dict(), "count": len(proposals)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())