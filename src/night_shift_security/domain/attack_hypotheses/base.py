"""Core abstractions for the Hypothesis Generation Layer."""

from __future__ import annotations

import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses.mapping import (
    MAPPING_VERSION,
    hypothesis_to_template_params,
    template_to_hypothesis_params,
)
from night_shift_security.domain.attack_hypotheses.parameter_spaces import (
    ALL_PARAMETER_SPACES,
    ParameterSpace,
)

_TEMPLATE_SPACES: dict[str, ParameterSpace] = ALL_PARAMETER_SPACES


@dataclass
class AttackHypothesis:
    """Structured, versioned attack hypothesis for pipeline handoff."""

    hypothesis_id: str
    template: str
    parameters: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttackHypothesis:
        return cls(
            hypothesis_id=data["hypothesis_id"],
            template=data["template"],
            parameters=dict(data["parameters"]),
            metadata=dict(data.get("metadata", {})),
            version=data.get("version", "1.0"),
        )


class HypothesisGenerator(ABC):
    """Produces, mutates, and composes AttackHypothesis instances."""

    @property
    @abstractmethod
    def template_id(self) -> str:
        ...

    @property
    def parameter_space(self) -> ParameterSpace:
        return get_parameter_space(self.template_id)

    @abstractmethod
    def sample(self, n: int) -> list[AttackHypothesis]:
        ...

    @abstractmethod
    def mutate(self, hypothesis: AttackHypothesis) -> AttackHypothesis:
        ...

    @abstractmethod
    def compose(self, h1: AttackHypothesis, h2: AttackHypothesis) -> AttackHypothesis:
        ...


_GENERATOR_REGISTRY: dict[str, HypothesisGenerator] = {}


def register_generator(generator: HypothesisGenerator) -> None:
    _GENERATOR_REGISTRY[generator.template_id] = generator


def get_generator(template_id: str) -> HypothesisGenerator | None:
    return _GENERATOR_REGISTRY.get(template_id)


def list_generators() -> list[str]:
    return list(_GENERATOR_REGISTRY.keys())


def get_parameter_space(template_id: str) -> ParameterSpace:
    if template_id not in _TEMPLATE_SPACES:
        raise KeyError(f"No parameter space defined for template: {template_id}")
    return _TEMPLATE_SPACES[template_id]


def _sample_field(spec: dict[str, Any], rng: random.Random) -> Any:
    field_type = spec["type"]
    if field_type == "bool":
        return rng.choice(spec.get("choices", [False, True]))
    if field_type == "choice":
        return rng.choice(spec["choices"])
    if field_type == "int":
        low, high = spec["range"]
        return rng.randint(int(low), int(high))
    if field_type == "float":
        low, high = spec["range"]
        distribution = spec.get("distribution", "uniform")
        if distribution == "uniform":
            return round(rng.uniform(low, high), 4)
        midpoint = (low + high) / 2.0
        spread = (high - low) / 6.0
        value = rng.gauss(midpoint, spread)
        return round(max(low, min(high, value)), 4)
    raise ValueError(f"Unsupported parameter type: {field_type}")


def sample_parameters(
    space: ParameterSpace,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Draw one parameter set from a declarative ParameterSpace."""
    rng = rng or random.Random()
    return {name: _sample_field(spec, rng) for name, spec in space.items()}


def validate_parameters(space: ParameterSpace, parameters: dict[str, Any]) -> tuple[bool, str]:
    """Validate parameters against a ParameterSpace definition."""
    missing = [key for key in space if key not in parameters]
    if missing:
        return False, f"Missing parameters: {', '.join(missing)}"

    extra = [key for key in parameters if key not in space]
    if extra:
        return False, f"Unknown parameters: {', '.join(extra)}"

    for name, spec in space.items():
        value = parameters[name]
        field_type = spec["type"]
        if field_type == "bool":
            if not isinstance(value, bool):
                return False, f"{name} must be bool"
            continue
        if field_type == "choice":
            if value not in spec["choices"]:
                return False, f"{name}={value!r} not in choices {spec['choices']}"
            continue
        if field_type == "int":
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"{name} must be int"
            low, high = spec["range"]
            if not int(low) <= value <= int(high):
                return False, f"{name}={value} outside range [{low}, {high}]"
            continue
        if field_type == "float":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"{name} must be float"
            low, high = spec["range"]
            if not low <= float(value) <= high:
                return False, f"{name}={value} outside range [{low}, {high}]"
            continue
        return False, f"Unsupported parameter type for {name}: {field_type}"

    return True, ""


def validate_hypothesis(hypothesis: AttackHypothesis) -> tuple[bool, str]:
    """Structural validation for Stage 0 sanity checks."""
    if not hypothesis.hypothesis_id:
        return False, "hypothesis_id is required"
    if not hypothesis.template:
        return False, "template is required"
    try:
        space = get_parameter_space(hypothesis.template)
    except KeyError as exc:
        return False, str(exc)
    return validate_parameters(space, hypothesis.parameters)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_hypothesis_id() -> str:
    return str(uuid.uuid4())


def _normalize_parent_ids(parent_ids: list[str] | None) -> list[str]:
    if not parent_ids:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for parent_id in parent_ids:
        if parent_id and parent_id not in seen:
            seen.add(parent_id)
            ordered.append(parent_id)
    return ordered


def _build_lineage(parent_ids: list[str], existing_lineage: list[str] | None = None) -> list[str]:
    lineage = list(existing_lineage or [])
    seen = set(lineage)
    for parent_id in parent_ids:
        if parent_id and parent_id not in seen:
            lineage.append(parent_id)
            seen.add(parent_id)
    return lineage


def _base_metadata(
    generation_method: str,
    template: str,
    parent_ids: list[str] | None = None,
    lineage: list[str] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    normalized_parents = _normalize_parent_ids(parent_ids)
    metadata = {
        "provenance": "attack_hypotheses",
        "generation_method": generation_method,
        "parent_ids": normalized_parents,
        "lineage": _build_lineage(normalized_parents, lineage),
        "mapping_version": MAPPING_VERSION,
        "timestamp": _utc_now_iso(),
        "trusted": generation_method != "llm_proposal",
    }
    metadata.update(extra)
    return metadata


def hypothesis_to_attack_vector(
    hypothesis: AttackHypothesis,
    target_id: str = "",
    label: str = "",
) -> AttackVector:
    """Convert AttackHypothesis to pipeline AttackVector with template-compatible params."""
    template_params = hypothesis_to_template_params(hypothesis.template, hypothesis.parameters)
    vector_label = label or f"{hypothesis.template}_{hypothesis.hypothesis_id[:8]}"
    return AttackVector(
        template_id=hypothesis.template,
        parameters=template_params,
        target_id=target_id,
        label=vector_label,
        metadata={
            "hypothesis_id": hypothesis.hypothesis_id,
            "parent_ids": list(hypothesis.metadata.get("parent_ids", [])),
            "lineage": list(hypothesis.metadata.get("lineage", [])),
            "generation_method": hypothesis.metadata.get("generation_method", "unknown"),
            "mapping_version": hypothesis.metadata.get("mapping_version", MAPPING_VERSION),
            "trusted": hypothesis.metadata.get("trusted", True),
        },
    )


def attack_vector_to_hypothesis(
    vector: AttackVector,
    generation_method: str = "grid_import",
    parent_ids: list[str] | None = None,
) -> AttackHypothesis:
    """Best-effort reverse mapping from AttackVector to AttackHypothesis."""
    vector_meta = vector.metadata or {}
    hypothesis_id = vector_meta.get("hypothesis_id") or _new_hypothesis_id()
    params = template_to_hypothesis_params(vector.template_id, vector.parameters)
    resolved_parents = _normalize_parent_ids(parent_ids or vector_meta.get("parent_ids"))

    return AttackHypothesis(
        hypothesis_id=hypothesis_id,
        template=vector.template_id,
        parameters=params,
        metadata=_base_metadata(
            generation_method=generation_method,
            template=vector.template_id,
            parent_ids=resolved_parents,
            lineage=vector_meta.get("lineage"),
            source_label=vector.label,
        ),
    )


class BaseHypothesisGenerator(HypothesisGenerator):
    """Shared sampling/mutation/compose logic for declarative parameter spaces."""

    def __init__(self, template_id: str, rng: random.Random | None = None) -> None:
        self._template_id = template_id
        self._rng = rng or random.Random()

    @property
    def template_id(self) -> str:
        return self._template_id

    def _make_hypothesis(
        self,
        parameters: dict[str, Any],
        generation_method: str,
        parent_ids: list[str] | None = None,
        lineage: list[str] | None = None,
        **metadata: Any,
    ) -> AttackHypothesis:
        valid, reason = validate_parameters(self.parameter_space, parameters)
        if not valid:
            raise ValueError(f"Invalid parameters for {self.template_id}: {reason}")
        return AttackHypothesis(
            hypothesis_id=_new_hypothesis_id(),
            template=self.template_id,
            parameters=parameters,
            metadata=_base_metadata(
                generation_method=generation_method,
                template=self.template_id,
                parent_ids=parent_ids,
                lineage=lineage,
                **metadata,
            ),
        )

    def sample(self, n: int) -> list[AttackHypothesis]:
        return [
            self._make_hypothesis(
                sample_parameters(self.parameter_space, self._rng),
                generation_method="sample",
            )
            for _ in range(n)
        ]

    def mutate(self, hypothesis: AttackHypothesis) -> AttackHypothesis:
        if hypothesis.template != self.template_id:
            raise ValueError(
                f"Cannot mutate {hypothesis.template} with {self.template_id} generator"
            )
        mutated = dict(hypothesis.parameters)
        key = self._rng.choice(list(self.parameter_space.keys()))
        mutated[key] = _sample_field(self.parameter_space[key], self._rng)
        parent_ids = [hypothesis.hypothesis_id]
        lineage = _build_lineage(
            parent_ids,
            hypothesis.metadata.get("lineage"),
        )
        return self._make_hypothesis(
            mutated,
            generation_method="mutate",
            parent_ids=parent_ids,
            lineage=lineage,
        )

    def compose(self, h1: AttackHypothesis, h2: AttackHypothesis) -> AttackHypothesis:
        if h1.template != self.template_id or h2.template != self.template_id:
            raise ValueError(
                f"Compose requires matching templates; got {h1.template} and {h2.template}"
            )
        keys = list(self.parameter_space.keys())
        split = self._rng.randint(1, len(keys) - 1) if len(keys) > 1 else 1
        composed = {}
        for i, key in enumerate(keys):
            composed[key] = h1.parameters[key] if i < split else h2.parameters[key]
        parent_ids = [h1.hypothesis_id, h2.hypothesis_id]
        lineage = _build_lineage(
            parent_ids,
            list(h1.metadata.get("lineage", [])) + list(h2.metadata.get("lineage", [])),
        )
        return self._make_hypothesis(
            composed,
            generation_method="compose",
            parent_ids=parent_ids,
            lineage=lineage,
        )