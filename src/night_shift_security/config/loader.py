"""Configuration loader."""

import json
from pathlib import Path

from night_shift_security.core.gates import SecurityGate

_DEFAULT_CONFIG = Path(__file__).parent / "default.json"


def load_config(config_path: Path | None = None) -> dict:
    path = config_path or _DEFAULT_CONFIG
    with open(path) as f:
        return json.load(f)


def gates_from_config(config: dict) -> SecurityGate:
    g = config.get("gates", {})
    return SecurityGate(
        MIN_REPRODUCIBILITY=g.get("min_reproducibility", 0.80),
        MIN_SEVERITY_SCORE=g.get("min_severity_score", 0.50),
        MIN_ECONOMIC_IMPACT_USD=g.get("min_economic_impact_usd", 100_000),
        MIN_INVARIANT_VIOLATIONS=g.get("min_invariant_violations", 1),
        MIN_REALISM_SCORE=g.get("min_realism_score", 0.40),
        MIN_GENERALITY=g.get("min_generality", 0.30),
        MAX_CAPITAL_REQUIRED_USD=g.get("max_capital_required_usd", 50_000_000),
    )