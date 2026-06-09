"""LLM hypothesis expansion quality eval — compare provider acceptance under validate_hypothesis()."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.domain.attack_hypotheses.base import (
    AttackHypothesis,
    hypothesis_to_attack_vector,
    validate_hypothesis,
)
from night_shift_security.domain.attack_hypotheses.llm_expansion import (
    _hypothesis_from_llm_params,
    _parse_llm_variants,
)
from night_shift_security.domain.attack_hypotheses.llm_provider import MockLLMProvider



@dataclass
class ProviderEvalResult:
    provider_label: str
    proposals_total: int
    structurally_valid: int
    acceptance_rate: float
    sample_errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_SEED = AttackHypothesis(
    hypothesis_id="eval-seed-governance",
    template="governance_capture",
    parameters={
        "quorum_threshold": 0.10,
        "participation_rate": 0.30,
        "whale_concentration": 0.50,
        "proposal_timing_window_blocks": 500,
        "flash_loan_boost": 0.20,
    },
    metadata={"generation_method": "eval_seed"},
)

_VALID_JSON = json.dumps([
    {
        "quorum_threshold": 0.08,
        "participation_rate": 0.25,
        "whale_concentration": 0.60,
        "proposal_timing_window_blocks": 800,
        "flash_loan_boost": 0.20,
    }
])

_INVALID_PARAMS_JSON = json.dumps([
    {
        "quorum_threshold": 9.99,
        "participation_rate": 0.25,
        "whale_concentration": 0.60,
        "proposal_timing_window_blocks": 800,
        "flash_loan_boost": 0.20,
    }
])

_MALFORMED_JSON = "not json at all"


def _eval_provider_responses(provider_label: str, responses: list[str]) -> ProviderEvalResult:
    valid = 0
    errors: list[str] = []
    total = 0

    for raw in responses:
        try:
            variants = _parse_llm_variants(raw, n=10)
        except (ValueError, TypeError) as exc:
            if len(errors) < 5:
                errors.append(str(exc))
            continue

        for parameters in variants:
            total += 1
            hypothesis = _hypothesis_from_llm_params(_SEED, parameters)
            ok, reason = validate_hypothesis(hypothesis)
            if ok:
                valid += 1
                hypothesis_to_attack_vector(hypothesis)
            elif len(errors) < 5:
                errors.append(reason)

    rate = (valid / total) if total else 0.0
    return ProviderEvalResult(
        provider_label=provider_label,
        proposals_total=total,
        structurally_valid=valid,
        acceptance_rate=round(rate, 4),
        sample_errors=errors,
    )


def run_llm_quality_eval(*, output_dir: Path | None = None) -> dict[str, Any]:
    """
    Compare mock Grok vs Ollama-style fixtures under validate_hypothesis().

    Zero API cost via MockLLMProvider. Extend with live LiteLLM when keys exist.
    """
    grok_responses = [_VALID_JSON, _INVALID_PARAMS_JSON, _MALFORMED_JSON]
    ollama_responses = [_VALID_JSON, _VALID_JSON, _INVALID_PARAMS_JSON]

    grok_raw = [
        MockLLMProvider([r], model="grok-mock").complete([]).content for r in grok_responses
    ]
    ollama_raw = [
        MockLLMProvider([r], model="ollama-mock").complete([]).content for r in ollama_responses
    ]

    grok_result = _eval_provider_responses("grok_mock", grok_raw)
    ollama_result = _eval_provider_responses("ollama_mock", ollama_raw)

    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "validate_hypothesis",
        "providers": [grok_result.to_dict(), ollama_result.to_dict()],
        "winner": (
            grok_result.provider_label
            if grok_result.acceptance_rate >= ollama_result.acceptance_rate
            else ollama_result.provider_label
        ),
    }

    if output_dir is not None:
        out_path = output_dir / "knowledge" / "llm_quality_eval.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
        payload["output_path"] = str(out_path)

    return payload