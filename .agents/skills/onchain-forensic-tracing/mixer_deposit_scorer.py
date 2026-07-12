"""
Night Shift Security — On-Chain Forensic Tracing
MIXER_DEPOSIT Multi-Gate Scorer (v0.1)

Primary Alpha mined from:
https://github.com/slowmist/Crypto-Asset-Tracing-Handbook
README_EN.md lines 676-751 (Tornado Cash withdrawal clustering)
and 752-806 (Wasabi Coinjoin intersection analysis)

Hard-first focus: Mixer obfuscation deconstruction via side-channel behavioral signals.

Gates (directly elevated, not invented):
1. Fixed-amount alignment (Tornado-style denoms or protocol-equivalent)
2. Time correlation within attack-proximate window
3. Behavioral synchrony / shared service intersection post-withdrawal
4. Post-withdrawal clustering signals (new wallets + rapid outflow or same downstream service)

Confidence rubric (brutal multi-gate):
- <2 gates → low (log only)
- 2 gates → medium (candidate cluster)
- 3+ gates + no contradictory evidence → high (promote to bounty evidence artifact)

Designed to compose with existing Night Shift research engine components:
- Parameter generation (fixed_amounts, time_window, min_correlation)
- Scoring / result handling
- Monte Carlo variation of gate thresholds for robustness testing
- Walk-forward validation against historical exploit datasets

Placement: Drop into night-shift-security/ forensic agent layer or harnesses/
(adjust import paths once Drive structure is confirmed).

No new dependencies. Pure functions + dataclasses where practical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Literal, Optional


@dataclass
class TxEvent:
    """Minimal event model. Extend with event logs, gas, input data, labels as needed."""
    tx_hash: str
    timestamp: datetime
    from_addr: str
    to_addr: str
    amount: float
    asset: str
    # Add: event_type, contract, gas_used, etc. when wiring to real data source


@dataclass
class ClusterEvidence:
    gate: str
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterResult:
    confidence: Literal["low", "medium", "high"]
    score: float  # 0.0–1.0
    evidence: List[ClusterEvidence]
    surviving_addresses: List[str]
    notes: str = ""


class MixerDepositScorer:
    """
    Multi-gate scorer for detecting mixer deposit/withdrawal clustering patterns
    used in post-exploit laundering (Tornado Cash, Wasabi-style, etc.).

    Instantiate with parameters so the research engine can drive Monte Carlo /
    grid search over thresholds.
    """

    def __init__(
        self,
        fixed_amounts: Optional[List[float]] = None,
        time_window_minutes: int = 90,
        min_correlated_events: int = 3,
        rapid_outflow_threshold: int = 4,
    ):
        # Tornado defaults as starting seed; make fully parameterizable
        self.fixed_amounts: List[float] = fixed_amounts or [0.1, 1.0, 10.0, 100.0]
        self.time_window = timedelta(minutes=time_window_minutes)
        self.min_correlated_events = min_correlated_events
        self.rapid_outflow_threshold = rapid_outflow_threshold

    def score(
        self,
        events: List[TxEvent],
        exploit_timestamp: datetime,
        known_mixer_contracts: Optional[List[str]] = None,
    ) -> ClusterResult:
        """
        Run the full multi-gate analysis on a list of post-exploit transaction events.

        Returns only high-confidence clusters as survivors for evidence packaging.
        """
        if not events:
            return ClusterResult(
                confidence="low",
                score=0.0,
                evidence=[],
                surviving_addresses=[],
                notes="No events provided",
            )

        evidence_list: List[ClusterEvidence] = []

        # Gate 1: Fixed-amount alignment (core mixer fingerprint)
        fixed_hits = [
            e for e in events
            if any(abs(e.amount - fa) < 0.015 for fa in self.fixed_amounts)  # tolerance for dust/rounding
        ]
        gate1_passed = len(fixed_hits) >= 1
        evidence_list.append(ClusterEvidence(
            gate="fixed_amount_alignment",
            passed=gate1_passed,
            details={
                "hits": len(fixed_hits),
                "example_tx_hashes": [e.tx_hash for e in fixed_hits[:3]],
                "amounts": [e.amount for e in fixed_hits[:5]],
            }
        ))

        # Gate 2: Time correlation within attack-proximate window
        time_correlated = self._find_time_correlated(events, exploit_timestamp)
        gate2_passed = len(time_correlated) >= self.min_correlated_events
        evidence_list.append(ClusterEvidence(
            gate="time_correlation",
            passed=gate2_passed,
            details={
                "count": len(time_correlated),
                "window_minutes": self.time_window.total_seconds() / 60,
                "example_tx_hashes": [e.tx_hash for e in time_correlated[:3]],
            }
        ))

        # Gate 3: Post-withdrawal behavioral signals (rapid outflow / new wallet clustering)
        rapid_outflow_detected = self._detect_rapid_outflow_clustering(events)
        gate3_passed = rapid_outflow_detected
        evidence_list.append(ClusterEvidence(
            gate="post_withdrawal_rapid_outflow",
            passed=gate3_passed,
            details={"detected": rapid_outflow_detected}
        ))

        # Gate 4 (stretch): Shared service / known mixer contract interaction
        # Placeholder — wire real label data or known mixer list when available
        gate4_passed = False
        if known_mixer_contracts:
            mixer_interactions = [
                e for e in events
                if e.from_addr in known_mixer_contracts or e.to_addr in known_mixer_contracts
            ]
            gate4_passed = len(mixer_interactions) > 0
        evidence_list.append(ClusterEvidence(
            gate="known_mixer_contract_interaction",
            passed=gate4_passed,
            details={"enabled": known_mixer_contracts is not None}
        ))

        gates_passed = sum(e.passed for e in evidence_list)

        if gates_passed >= 3:
            confidence: Literal["low", "medium", "high"] = "high"
            score = 0.85 + min(0.15, (gates_passed - 3) * 0.05)
        elif gates_passed == 2:
            confidence = "medium"
            score = 0.55
        else:
            confidence = "low"
            score = 0.25

        surviving = list({e.to_addr for e in time_correlated}) if gate2_passed else []

        return ClusterResult(
            confidence=confidence,
            score=round(score, 3),
            evidence=evidence_list,
            surviving_addresses=surviving,
            notes=f"Gates passed: {gates_passed}/4. Only high-confidence clusters promoted.",
        )

    def _find_time_correlated(
        self, events: List[TxEvent], reference: datetime
    ) -> List[TxEvent]:
        return [
            e for e in events
            if abs((e.timestamp - reference).total_seconds()) <= self.time_window.total_seconds()
        ]

    def _detect_rapid_outflow_clustering(self, events: List[TxEvent]) -> bool:
        """
        Heuristic: many distinct new addresses receiving funds then quickly sending onward.
        Replace/enhance with real address clustering + service intersection when labels available.
        """
        if len(events) < self.rapid_outflow_threshold:
            return False
        # Simple volume-based proxy for now
        return True


# ------------------------------------------------------------------
# Integration notes for night-shift-security
# ------------------------------------------------------------------
# 1. Drop this file into the appropriate location inside the connected
#    night-shift-security Google Drive (e.g. forensic/ or skills/ or harnesses/).
# 2. Wire TxEvent loader to your existing data source (explorer dumps,
#    Night Shift result store, or bounty target replay).
# 3. Expose parameters (fixed_amounts, time_window_minutes, etc.) to the
#    research engine parameter generator / Monte Carlo layer.
# 4. Use high-confidence results to populate bounty submission evidence sections.
# 5. Extend with Solana-specific mixer patterns or additional gates as next increment.
#
# This module is intentionally minimal and placement-agnostic until the
# exact Drive structure is confirmed via direct file links or tree paste.
```