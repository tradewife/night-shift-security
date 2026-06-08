"""LLM-assisted hypothesis expansion — proposal-only, never trusted for validation."""

from __future__ import annotations

import logging
from typing import Any

from night_shift_security.domain.attack_hypotheses.base import (
    AttackHypothesis,
    BaseHypothesisGenerator,
    _base_metadata,
    _new_hypothesis_id,
    get_generator,
    get_parameter_space,
    validate_hypothesis,
)
from night_shift_security.domain.attack_hypotheses.llm_provider import (
    LLMProvider,
    create_llm_provider,
    extract_json_payload,
    log_llm_outcome,
)

logger = logging.getLogger(__name__)


def _parameter_space_prompt(space: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for name, spec in space.items():
        field_type = spec["type"]
        if field_type in ("float", "int"):
            low, high = spec["range"]
            lines.append(f'  "{name}": {field_type} in [{low}, {high}]')
        elif field_type == "bool":
            lines.append(f'  "{name}": bool')
        elif field_type == "choice":
            lines.append(f'  "{name}": one of {spec["choices"]}')
    return "\n".join(lines)


def _build_expansion_prompt(seed: AttackHypothesis, n: int) -> list[dict[str, str]]:
    space = get_parameter_space(seed.template)
    system = (
        "You propose attack hypothesis parameter variants for security research. "
        "Output is untrusted and will be validated deterministically. "
        "Respond with JSON only: an array of exactly "
        f"{n} objects, each containing all required parameter keys with valid values."
    )
    user = (
        f"Template: {seed.template}\n"
        f"Seed parameters: {seed.parameters}\n"
        f"Parameter space:\n{_parameter_space_prompt(space)}\n"
        f"Propose {n} diverse variants as a JSON array of parameter objects."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _hypothesis_from_llm_params(
    seed: AttackHypothesis,
    parameters: dict[str, Any],
) -> AttackHypothesis:
    parent_ids = [seed.hypothesis_id]
    lineage = list(seed.metadata.get("lineage", []))
    if seed.hypothesis_id not in lineage:
        lineage.append(seed.hypothesis_id)
    return AttackHypothesis(
        hypothesis_id=_new_hypothesis_id(),
        template=seed.template,
        parameters=parameters,
        metadata=_base_metadata(
            generation_method="llm_proposal",
            template=seed.template,
            parent_ids=parent_ids,
            lineage=lineage,
            trusted=False,
        ),
    )


def _annotate_llm_metadata(
    hypothesis: AttackHypothesis,
    *,
    enabled: bool,
    fallback: str,
    seed_id: str,
    note: str,
    llm_call: dict[str, Any] | None = None,
) -> None:
    hypothesis.metadata["trusted"] = False
    hypothesis.metadata["generation_method"] = "llm_proposal"
    expansion_meta: dict[str, Any] = {
        "enabled": enabled,
        "fallback": fallback,
        "seed_id": seed_id,
        "note": note,
    }
    if llm_call:
        expansion_meta["call"] = llm_call
    hypothesis.metadata["llm_expansion"] = expansion_meta


def _parse_llm_variants(content: str, n: int) -> list[dict[str, Any]]:
    payload = extract_json_payload(content)
    if isinstance(payload, dict) and "variants" in payload:
        payload = payload["variants"]
    if not isinstance(payload, list):
        raise ValueError("LLM response must be a JSON array of parameter objects")
    variants: list[dict[str, Any]] = []
    for item in payload[:n]:
        if not isinstance(item, dict):
            raise ValueError("Each LLM variant must be a JSON object")
        variants.append(dict(item))
    return variants


class LLMExpansionOrchestrator:
    """
    Thin orchestrator for LLM-proposed hypothesis variants.

    Strict contract:
    - Output is untrusted proposal only (metadata.trusted = False).
    - Never participates in validation, scoring, or gate decisions.
    - All proposals must still pass deterministic ParameterSpace validation.
    """

    def __init__(
        self,
        enabled: bool = False,
        fallback: str = "parametric",
        provider: LLMProvider | None = None,
        provider_config: dict[str, Any] | None = None,
    ) -> None:
        self.enabled = enabled
        self.fallback = fallback
        self._provider = provider
        self._provider_config = dict(provider_config or {})
        self._temperature = float(self._provider_config.get("temperature", 0.7))
        self._max_tokens = int(self._provider_config.get("max_tokens", 1024))
        self._timeout_seconds = float(self._provider_config.get("timeout_seconds", 30.0))

    def _get_provider(self) -> LLMProvider | None:
        if self._provider is not None:
            return self._provider
        if not self.enabled:
            return None
        return create_llm_provider(self._provider_config)

    def _parametric_variants(
        self,
        seed: AttackHypothesis,
        generator: BaseHypothesisGenerator,
        n: int,
        *,
        note: str,
    ) -> list[AttackHypothesis]:
        proposals: list[AttackHypothesis] = []
        current = seed
        for _ in range(n):
            variant = generator.mutate(current)
            _annotate_llm_metadata(
                variant,
                enabled=self.enabled,
                fallback=self.fallback,
                seed_id=seed.hypothesis_id,
                note=note,
            )
            valid, reason = validate_hypothesis(variant)
            if valid:
                proposals.append(variant)
            else:
                logger.debug("Parametric fallback variant rejected: %s", reason)
            current = variant
        return proposals

    def _llm_variants(
        self,
        seed: AttackHypothesis,
        n: int,
        provider: LLMProvider,
    ) -> tuple[list[AttackHypothesis], dict[str, Any] | None]:
        messages = _build_expansion_prompt(seed, n)
        result = provider.complete(
            messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout_seconds=self._timeout_seconds,
        )
        log_llm_outcome(result, context=f"expand:{seed.template}:{seed.hypothesis_id[:8]}")

        call_meta = {
            "provider": result.provider,
            "model": result.model,
            "success": result.success,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "estimated_cost_usd": result.estimated_cost_usd,
            "error": result.error,
        }

        if not result.success:
            return [], call_meta

        try:
            raw_variants = _parse_llm_variants(result.content, n)
        except (ValueError, TypeError) as exc:
            logger.warning("Failed to parse LLM variants: %s", exc)
            call_meta["parse_error"] = str(exc)
            return [], call_meta

        proposals: list[AttackHypothesis] = []
        for parameters in raw_variants:
            hypothesis = _hypothesis_from_llm_params(seed, parameters)
            _annotate_llm_metadata(
                hypothesis,
                enabled=True,
                fallback=self.fallback,
                seed_id=seed.hypothesis_id,
                note="llm_proposal",
                llm_call=call_meta,
            )
            valid, reason = validate_hypothesis(hypothesis)
            if valid:
                proposals.append(hypothesis)
            else:
                logger.debug("LLM proposal rejected by validate_hypothesis: %s", reason)

        call_meta["accepted_count"] = len(proposals)
        call_meta["proposed_count"] = len(raw_variants)
        return proposals, call_meta

    def propose_variants(
        self,
        seed: AttackHypothesis,
        n: int = 3,
    ) -> list[AttackHypothesis]:
        """
        Propose variants from a seed hypothesis.

        When enabled with a configured provider, attempts real LLM calls.
        Falls back to parametric mutation on failure or to fill remaining slots.
        """
        generator = get_generator(seed.template)
        if generator is None:
            return []

        if not self.enabled:
            return self._parametric_variants(
                seed,
                generator,
                n,
                note="parametric_fallback",
            )

        provider = self._get_provider()
        if provider is None:
            logger.info(
                "LLM expansion enabled but no provider available; using parametric fallback"
            )
            return self._parametric_variants(
                seed,
                generator,
                n,
                note="parametric_fallback_no_provider",
            )

        llm_proposals, _ = self._llm_variants(seed, n, provider)
        if len(llm_proposals) >= n:
            return llm_proposals[:n]

        remaining = n - len(llm_proposals)
        if remaining > 0 and self.fallback == "parametric":
            logger.info(
                "LLM produced %d/%d valid variants for %s; filling %d via parametric fallback",
                len(llm_proposals),
                n,
                seed.hypothesis_id[:8],
                remaining,
            )
            fallback_seed = llm_proposals[-1] if llm_proposals else seed
            llm_proposals.extend(
                self._parametric_variants(
                    fallback_seed,
                    generator,
                    remaining,
                    note="parametric_fallback_after_llm",
                )
            )
        return llm_proposals

    def expand_batch(
        self,
        seeds: list[AttackHypothesis],
        variants_per_seed: int = 2,
    ) -> list[AttackHypothesis]:
        expanded: list[AttackHypothesis] = []
        for seed in seeds:
            expanded.extend(self.propose_variants(seed, n=variants_per_seed))
        return expanded