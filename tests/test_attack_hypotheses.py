"""Tests for Hypothesis Generation Layer."""

import json
import random

import pytest

from night_shift_security.core.evaluation import evaluate_attack_vector
from night_shift_security.core.evolution import darwinian_evolution
from night_shift_security.core.hypothesis import (
    generate_llm_expanded_attack_vectors,
    generate_sampled_attack_vectors,
    resolve_sample_count,
)
from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.domain.attack_hypotheses import (
    AttackHypothesis,
    LLMExpansionOrchestrator,
    MAPPING_VERSION,
    MockLLMProvider,
    attack_vector_to_hypothesis,
    get_generator,
    hypothesis_to_attack_vector,
    list_generators,
    validate_hypothesis,
    validate_parameters,
)
from night_shift_security.domain.attack_hypotheses.llm_provider import (
    LiteLLMProvider,
    create_llm_provider,
    extract_json_payload,
)
from night_shift_security.domain.attack_hypotheses.governance import GovernanceCaptureGenerator
from night_shift_security.domain.attack_hypotheses.mapping import (
    MAPPING_REGISTRY,
    hypothesis_to_template_params,
    template_to_hypothesis_params,
)
from night_shift_security.domain.attack_hypotheses.parameter_spaces import (
    ALL_PARAMETER_SPACES,
    GOVERNANCE_CAPTURE_SPACE,
    TREASURY_DRAIN_SPACE,
)

import night_shift_security.domain.attack_hypotheses  # noqa: F401
import night_shift_security.domain.attack_templates.governance_capture  # noqa: F401
import night_shift_security.domain.attack_templates.treasury_drain  # noqa: F401
import night_shift_security.domain.attack_templates.flash_loan_oracle  # noqa: F401
import night_shift_security.domain.attack_templates.reentrancy  # noqa: F401
import night_shift_security.domain.attack_templates.composability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.upgradeability_risk  # noqa: F401
import night_shift_security.domain.attack_templates.access_control_escalation  # noqa: F401

ALL_TEMPLATES = {
    "governance_capture",
    "treasury_drain",
    "flash_loan_oracle",
    "reentrancy",
    "composability_risk",
    "upgradeability_risk",
    "access_control_escalation",
}


def test_generators_registered():
    assert set(list_generators()) == ALL_TEMPLATES


def test_all_parameter_spaces_have_mappings():
    assert set(ALL_PARAMETER_SPACES) == set(MAPPING_REGISTRY)
    assert len(MAPPING_REGISTRY) == 7


def test_mapping_version_stamped_on_hypotheses():
    generator = get_generator("governance_capture")
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    assert hypothesis.metadata["mapping_version"] == MAPPING_VERSION


def test_governance_sample_100_hypotheses():
    generator = get_generator("governance_capture")
    assert generator is not None
    hypotheses = generator.sample(100)
    assert len(hypotheses) == 100
    for hypothesis in hypotheses:
        ok, reason = validate_hypothesis(hypothesis)
        assert ok, reason
        assert hypothesis.template == "governance_capture"
        assert hypothesis.metadata["generation_method"] == "sample"
        assert hypothesis.metadata["trusted"] is True
        assert hypothesis.metadata["mapping_version"] == MAPPING_VERSION


def test_treasury_parameter_space_validation():
    generator = get_generator("treasury_drain")
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    ok, reason = validate_parameters(TREASURY_DRAIN_SPACE, hypothesis.parameters)
    assert ok, reason


def test_mutate_and_compose_provenance():
    generator = get_generator("governance_capture")
    assert generator is not None
    seed = generator.sample(1)[0]
    mutated = generator.mutate(seed)
    composed = generator.compose(seed, mutated)

    assert mutated.hypothesis_id != seed.hypothesis_id
    assert composed.hypothesis_id not in {seed.hypothesis_id, mutated.hypothesis_id}
    assert mutated.metadata["generation_method"] == "mutate"
    assert composed.metadata["generation_method"] == "compose"
    assert seed.hypothesis_id in mutated.metadata["parent_ids"]
    assert set(composed.metadata["parent_ids"]) == {seed.hypothesis_id, mutated.hypothesis_id}
    assert seed.hypothesis_id in mutated.metadata["lineage"]
    assert seed.hypothesis_id in composed.metadata["lineage"]


def test_hypothesis_round_trip_serialization():
    generator = get_generator("treasury_drain")
    assert generator is not None
    original = generator.sample(1)[0]
    payload = json.dumps(original.to_dict())
    restored = AttackHypothesis.from_dict(json.loads(payload))
    assert restored == original


def test_hypothesis_to_attack_vector_pipeline_compat():
    generator = get_generator("governance_capture")
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    vector = hypothesis_to_attack_vector(hypothesis)
    assert vector.template_id == "governance_capture"
    assert "voting_power_pct" in vector.parameters
    assert vector.metadata["hypothesis_id"] == hypothesis.hypothesis_id
    assert vector.metadata["mapping_version"] == MAPPING_VERSION


def test_all_templates_forward_mapping():
    for template_id in ALL_TEMPLATES:
        generator = get_generator(template_id)
        assert generator is not None
        hypothesis = generator.sample(1)[0]
        template_params = hypothesis_to_template_params(template_id, hypothesis.parameters)
        assert template_params
        vector = hypothesis_to_attack_vector(hypothesis)
        assert vector.parameters == template_params


def test_all_templates_reverse_mapping():
    for template_id in ALL_TEMPLATES:
        generator = get_generator(template_id)
        assert generator is not None
        original = generator.sample(1)[0]
        vector = hypothesis_to_attack_vector(original)
        restored = attack_vector_to_hypothesis(vector)
        ok, _ = validate_hypothesis(restored)
        assert ok
        assert set(restored.parameters) == set(ALL_PARAMETER_SPACES[template_id])


def test_sampled_vectors_evaluate_in_pipeline():
    catalog = get_exploit_catalog()
    gov_states = [e.state for e in catalog if e.template_id == "governance_capture"]

    vectors = generate_sampled_attack_vectors("governance_capture", n=10)
    assert len(vectors) == 10
    results = [evaluate_attack_vector(v, gov_states) for v in vectors]
    assert len(results) == 10


def test_evolution_lineage_tracking_across_generations():
    """Offspring must carry parent_ids and ancestry through multi-gen evolution."""
    catalog = get_exploit_catalog()
    states = [e.state for e in catalog if e.template_id == "governance_capture"]

    generator = GovernanceCaptureGenerator()
    generator._rng = random.Random(42)
    seed = generator.sample(1)[0]
    seed_id = seed.hypothesis_id
    seed_vector = hypothesis_to_attack_vector(seed)
    population = [evaluate_attack_vector(seed_vector, states)]

    random.seed(42)
    evolved = darwinian_evolution(
        population,
        states,
        config={"generations": 3, "population": 2, "offspring_per_parent": 2},
    )
    assert evolved

    evolved_meta = [
        c.vector.metadata
        for c in evolved
        if c.vector.metadata.get("generation_method") in ("mutate", "compose")
    ]
    assert evolved_meta, "expected evolved offspring with hypothesis metadata"

    for meta in evolved_meta:
        assert meta.get("parent_ids"), "evolved vector missing parent_ids"
        lineage = meta.get("lineage", [])
        assert seed_id in lineage or seed_id in meta["parent_ids"]


def test_evolution_uses_hypothesis_generators():
    catalog = get_exploit_catalog()
    states = [e.state for e in catalog if e.template_id == "governance_capture"]
    vectors = generate_sampled_attack_vectors("governance_capture", n=5)
    population = [evaluate_attack_vector(v, states) for v in vectors]
    evolved = darwinian_evolution(
        population,
        states,
        config={"generations": 1, "population": 3, "offspring_per_parent": 2},
    )
    assert len(evolved) > 0


def test_llm_expansion_disabled_uses_deterministic_stub():
    generator = get_generator("governance_capture")
    assert generator is not None
    seed = generator.sample(1)[0]
    orchestrator = LLMExpansionOrchestrator(enabled=False)
    proposals = orchestrator.propose_variants(seed, n=2)
    assert len(proposals) == 2
    for proposal in proposals:
        assert proposal.metadata["trusted"] is False
        assert proposal.metadata["generation_method"] == "llm_proposal"
        assert proposal.metadata["llm_expansion"]["fallback"] == "parametric"
        assert proposal.metadata["llm_expansion"]["note"] == "parametric_fallback"
        ok, _ = validate_hypothesis(proposal)
        assert ok


def test_llm_expansion_pipeline_handoff_validates_proposals():
    vectors = generate_sampled_attack_vectors("governance_capture", n=2)
    expanded = generate_llm_expanded_attack_vectors(
        "governance_capture",
        vectors,
        variants_per_seed=2,
        enabled=False,
    )
    assert len(expanded) == 4
    for vector in expanded:
        assert vector.metadata.get("trusted") is False
        assert vector.metadata.get("mapping_version") == MAPPING_VERSION


def test_attack_vector_round_trip_to_hypothesis():
    generator = get_generator("treasury_drain")
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    vector = hypothesis_to_attack_vector(hypothesis)
    restored = attack_vector_to_hypothesis(vector)
    ok, _ = validate_hypothesis(restored)
    assert ok
    assert restored.template == "treasury_drain"
    assert restored.hypothesis_id == hypothesis.hypothesis_id
    assert set(restored.parameters) == set(TREASURY_DRAIN_SPACE.keys())


def test_mapping_registry_audit_fields():
    for template_id, spec in MAPPING_REGISTRY.items():
        assert spec["hypothesis_fields"]
        assert spec["template_fields"]
        assert spec["rules"]
        assert template_id in ALL_PARAMETER_SPACES


@pytest.mark.parametrize("template_id", sorted(ALL_TEMPLATES))
def test_each_generator_samples_valid_hypothesis(template_id):
    generator = get_generator(template_id)
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    ok, reason = validate_hypothesis(hypothesis)
    assert ok, reason
    assert hypothesis.metadata["mapping_version"] == MAPPING_VERSION


def test_resolve_sample_count_fraction_of_grid():
    assert resolve_sample_count(24, samples_per_template=20, sample_fraction_of_grid=0.5) == 12
    assert resolve_sample_count(24, samples_per_template=20, sample_fraction_of_grid=None) == 20


def _governance_llm_variant_json() -> str:
    return """[
      {
        "quorum_threshold": 0.12,
        "participation_rate": 0.45,
        "whale_concentration": 0.55,
        "proposal_timing_window_blocks": 1200,
        "flash_loan_boost": 0.15
      },
      {
        "quorum_threshold": 0.18,
        "participation_rate": 0.62,
        "whale_concentration": 0.71,
        "proposal_timing_window_blocks": 2400,
        "flash_loan_boost": 0.08
      }
    ]"""


def test_create_llm_provider_mock():
    provider = create_llm_provider({"provider": "mock", "model": "unit-test"})
    assert provider is not None
    assert provider.provider_name == "mock"


def test_create_llm_provider_litellm_without_credentials_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    missing = tmp_path / "missing-auth.json"
    monkeypatch.setattr(
        "night_shift_security.domain.attack_hypotheses.llm_provider._GROK_AUTH_PATH",
        missing,
    )
    monkeypatch.setattr(
        "night_shift_security.domain.attack_hypotheses.llm_provider._HERMES_AUTH_PATH",
        missing,
    )
    provider = create_llm_provider({"provider": "litellm", "model": "gpt-4o-mini"})
    assert provider is None


def test_litellm_provider_reports_import_error_when_uninstalled():
    provider = LiteLLMProvider("gpt-4o-mini", api_key="test-key")
    result = provider.complete([{"role": "user", "content": "hi"}])
    if result.success:
        pytest.skip("litellm is installed in this environment")
    assert result.error is not None
    assert "litellm" in result.error.lower()


def test_extract_json_payload_from_fenced_block():
    payload = extract_json_payload(f"```json\n{_governance_llm_variant_json()}\n```")
    assert isinstance(payload, list)
    assert len(payload) == 2


def test_llm_expansion_enabled_with_mock_provider():
    generator = get_generator("governance_capture")
    assert generator is not None
    seed = generator.sample(1)[0]
    provider = MockLLMProvider(responses=[_governance_llm_variant_json()])
    orchestrator = LLMExpansionOrchestrator(
        enabled=True,
        fallback="parametric",
        provider=provider,
        provider_config={"provider": "mock", "model": "test-model"},
    )
    proposals = orchestrator.propose_variants(seed, n=2)
    assert len(proposals) == 2
    for proposal in proposals:
        assert proposal.metadata["trusted"] is False
        assert proposal.metadata["generation_method"] == "llm_proposal"
        assert proposal.metadata["llm_expansion"]["note"] == "llm_proposal"
        assert proposal.metadata["llm_expansion"]["call"]["provider"] == "mock"
        ok, _ = validate_hypothesis(proposal)
        assert ok


def test_llm_expansion_falls_back_when_provider_fails():
    generator = get_generator("governance_capture")
    assert generator is not None
    seed = generator.sample(1)[0]
    provider = MockLLMProvider(fail=True, error="rate limited")
    orchestrator = LLMExpansionOrchestrator(
        enabled=True,
        fallback="parametric",
        provider=provider,
    )
    proposals = orchestrator.propose_variants(seed, n=2)
    assert len(proposals) == 2
    for proposal in proposals:
        assert proposal.metadata["llm_expansion"]["note"].startswith("parametric_fallback")
        ok, _ = validate_hypothesis(proposal)
        assert ok


def test_llm_expansion_rejects_invalid_llm_output_then_falls_back():
    generator = get_generator("governance_capture")
    assert generator is not None
    seed = generator.sample(1)[0]
    invalid_json = '[{"quorum_threshold": 99.0, "participation_rate": 0.5}]'
    provider = MockLLMProvider(responses=[invalid_json])
    orchestrator = LLMExpansionOrchestrator(
        enabled=True,
        fallback="parametric",
        provider=provider,
    )
    proposals = orchestrator.propose_variants(seed, n=2)
    assert len(proposals) == 2
    assert all(
        p.metadata["llm_expansion"]["note"].startswith("parametric_fallback")
        for p in proposals
    )


def test_llm_expansion_pipeline_handoff_with_mock_provider():
    vectors = generate_sampled_attack_vectors("governance_capture", n=2)
    provider = MockLLMProvider(
        responses=[_governance_llm_variant_json(), _governance_llm_variant_json()],
    )
    expanded = generate_llm_expanded_attack_vectors(
        "governance_capture",
        vectors,
        variants_per_seed=2,
        enabled=True,
        fallback="parametric",
        provider=provider,
    )
    assert len(expanded) == 4
    for vector in expanded:
        assert vector.metadata.get("trusted") is False
        assert vector.metadata.get("mapping_version") == MAPPING_VERSION
        ok, _ = validate_hypothesis(attack_vector_to_hypothesis(vector))
        assert ok


def test_template_round_trip_mapping_consistency():
    generator = get_generator("flash_loan_oracle")
    assert generator is not None
    hypothesis = generator.sample(1)[0]
    forward = hypothesis_to_template_params("flash_loan_oracle", hypothesis.parameters)
    reverse = template_to_hypothesis_params("flash_loan_oracle", forward)
    ok, _ = validate_parameters(ALL_PARAMETER_SPACES["flash_loan_oracle"], reverse)
    assert ok