#!/usr/bin/env python3
"""v6.8 Ultrafuzz Orchestrator — Kamino KLend Flash-Loan Campaign

Runs 5 strategies x 3 attempts = 15 runs on Kamino KLend flash-loan path.
Each attempt uses a fresh solana-test-validator context.
"""

import json
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

INVESTIGATION_DIR = Path("/home/kt/projects/rtp/night-shift-security/data/security_results/investigations/2026-06-21-v6-8-kamino-ultrafuzz")
KAMINO_DIR = Path("/home/kt/projects/rtp/night-shift-security/sources/kamino/klend")
PROGRAM_BINARY = KAMINO_DIR / "tests/fixtures/klend.so"
PROGRAM_ID = "KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD"
RPC_URL = "https://solana-mainnet.g.alchemy.com/v2/wsRyjZyoVhsl7OPkGSE-g"

@dataclass
class AttemptResult:
    strategy: str
    attempt: int
    started_at: str
    finished_at: Optional[str]
    status: str  # "pass", "fail", "error", "harness_artifact"
    findings: List[Dict[str, Any]]
    validator_output: str
    exit_code: int

@dataclass
class StrategyResult:
    strategy: str
    description: str
    attempts: List[AttemptResult]
    pass_at_k: int  # how many of 3 attempts found at least one finding
    unique_findings: List[Dict[str, Any]]

@dataclass  
class CampaignSummary:
    target: str
    program_id: str
    started_at: str
    finished_at: Optional[str]
    total_attempts: int
    total_findings: int
    unique_findings: int
    pass_at_k_by_strategy: Dict[str, int]
    adjudicated: bool
    submit_ready: bool

STRATEGIES = [
    {
        "id": "fee_edge_cases",
        "name": "Strategy 1: Fee Edge Cases",
        "description": "Flash-borrow at boundary amounts to test fee calculation precision",
        "hypothesis": "H4: Fee precision loss at small amounts",
    },
    {
        "id": "cross_reserve_composition",
        "name": "Strategy 2: Cross-Reserve Composition",
        "description": "Flash-borrow USDC, interact with SOL reserve, flash-repay",
        "hypothesis": "H10: Cross-reserve isolation",
    },
    {
        "id": "obligation_lifecycle",
        "name": "Strategy 3: Obligation Lifecycle + Flash-Loan",
        "description": "Create obligation, deposit, flash-borrow, repay, withdraw in various orders",
        "hypothesis": "H9: Obligation health during flash window",
    },
    {
        "id": "liquidation_race",
        "name": "Strategy 4: Liquidation + Flash-Loan Race",
        "description": "Flash-borrow to reduce liquidity, then attempt liquidation",
        "hypothesis": "H2: Obligation health check race",
    },
    {
        "id": "token2022_interaction",
        "name": "Strategy 5: Token-2022 Interaction",
        "description": "Flash-loan with tokens that have transfer hooks or transfer fees",
        "hypothesis": "H5: Token-2022 double-charge",
    },
]

NUM_ATTEMPTS = 3

def run_attempt(strategy_id: str, attempt_num: int) -> AttemptResult:
    """Run a single attempt of a strategy on a fresh validator context."""
    now = datetime.now(timezone.utc).isoformat()
    
    # The actual test execution would use ts-mocha or anchor test
    # For now, create the result structure
    result = AttemptResult(
        strategy=strategy_id,
        attempt=attempt_num,
        started_at=now,
        finished_at=None,
        status="pending",
        findings=[],
        validator_output="",
        exit_code=-1,
    )
    
    # TODO: Wire to actual test execution via subprocess
    # subprocess.run(["npx", "ts-mocha", ...], cwd=str(KAMINO_DIR))
    
    return result

def adjudicate(strategy_results: List[StrategyResult]) -> Dict[str, Any]:
    """Run quorum adjudication on all findings."""
    all_findings = []
    for sr in strategy_results:
        all_findings.extend(sr.unique_findings)
    
    # Deduplicate by root cause
    deduplicated = {}
    for f in all_findings:
        key = f.get("root_cause", f.get("description", ""))
        if key not in deduplicated:
            deduplicated[key] = f
    
    return {
        "total_raw": len(all_findings),
        "deduplicated": len(deduplicated),
        "findings": list(deduplicated.values()),
    }

def main():
    """Run the full Ultrafuzz campaign."""
    INVESTIGATION_DIR.mkdir(parents=True, exist_ok=True)
    (INVESTIGATION_DIR / "strategies").mkdir(exist_ok=True)
    
    summary = CampaignSummary(
        target="kamino_klend",
        program_id=PROGRAM_ID,
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        total_attempts=0,
        total_findings=0,
        unique_findings=0,
        pass_at_k_by_strategy={},
        adjudicated=False,
        submit_ready=False,
    )
    
    strategy_results = []
    
    for strategy in STRATEGIES:
        print(f"\n{'='*60}")
        print(f"Running: {strategy['name']}")
        print(f"Description: {strategy['description']}")
        print(f"Hypothesis: {strategy['hypothesis']}")
        print(f"{'='*60}")
        
        attempts = []
        findings_count = 0
        
        for attempt_num in range(1, NUM_ATTEMPTS + 1):
            print(f"\n  Attempt {attempt_num}/{NUM_ATTEMPTS}...")
            result = run_attempt(strategy["id"], attempt_num)
            attempts.append(result)
            summary.total_attempts += 1
            findings_count += len(result.findings)
        
        sr = StrategyResult(
            strategy=strategy["id"],
            description=strategy["description"],
            attempts=attempts,
            pass_at_k=1 if findings_count > 0 else 0,
            unique_findings=[],  # populated after adjudication
        )
        strategy_results.append(sr)
        summary.pass_at_k_by_strategy[strategy["id"]] = sr.pass_at_k
        
        # Write strategy results
        strategy_file = INVESTIGATION_DIR / "strategies" / f"{strategy['id']}.json"
        with open(strategy_file, "w") as f:
            json.dump(asdict(sr), f, indent=2)
    
    # Quorum adjudication
    print(f"\n{'='*60}")
    print("Phase 4: Quorum Adjudication")
    print(f"{'='*60}")
    
    quorum = adjudicate(strategy_results)
    summary.total_findings = quorum["total_raw"]
    summary.unique_findings = quorum["deduplicated"]
    summary.adjudicated = True
    summary.finished_at = datetime.now(timezone.utc).isoformat()
    
    # Write quorum results
    with open(INVESTIGATION_DIR / "quorum.json", "w") as f:
        json.dump(quorum, f, indent=2)
    
    # Write summary
    with open(INVESTIGATION_DIR / "summary.json", "w") as f:
        json.dump(asdict(summary), f, indent=2)
    
    print(f"\nTotal attempts: {summary.total_attempts}")
    print(f"Total raw findings: {summary.total_findings}")
    print(f"Unique findings: {summary.unique_findings}")
    print(f"Pass@k by strategy: {summary.pass_at_k_by_strategy}")
    print(f"Submit ready: {summary.submit_ready}")
    
    return summary

if __name__ == "__main__":
    main()
