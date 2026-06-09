"""Tests for Hermes external proposals ingestion."""

import json
from pathlib import Path

import pytest

from night_shift_security.core.hypothesis import generate_llm_expanded_attack_vectors
from night_shift_security.data.schemas import AttackVector
from night_shift_security.domain.attack_hypotheses import attack_vector_to_hypothesis
from night_shift_security.domain.attack_hypotheses.external_proposals import (
    external_proposals_for_seed,
    load_external_proposals,
)
from night_shift_security.domain.attack_hypotheses.llm_expansion import LLMExpansionOrchestrator

import night_shift_security.domain.attack_hypotheses  # noqa: F401


_SEED_VECTOR = AttackVector(
    label="seed_flash",
    template_id="flash_loan_oracle",
    parameters={
        "loan_fraction_of_ceiling": 0.25,
        "price_skew_severity": 0.5,
        "oracle_dependency_score": 0.7,
    },
)


def _write_proposals(path: Path, proposals: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "run_id": "test-run",
                "campaign_id": "kamino-immunefi-2026-06",
                "proposals": proposals,
            }
        )
    )


def test_load_external_proposals_valid(tmp_path: Path):
    path = tmp_path / "proposals.json"
    _write_proposals(
        path,
        [
            {
                "template": "flash_loan_oracle",
                "parameters": {
                    "loan_fraction_of_ceiling": 0.4,
                    "price_skew_severity": 0.8,
                    "oracle_dependency_score": 0.6,
                },
            }
        ],
    )
    doc = load_external_proposals(path)
    assert doc.run_id == "test-run"
    assert doc.campaign_id == "kamino-immunefi-2026-06"
    assert len(doc.proposals) == 1


def test_load_external_proposals_rejects_invalid_root(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([]))
    with pytest.raises(ValueError, match="JSON object"):
        load_external_proposals(path)


def test_external_proposals_for_seed_filters_by_template_and_seed_id(tmp_path: Path):
    seed = attack_vector_to_hypothesis(_SEED_VECTOR, generation_method="test_seed")
    path = tmp_path / "proposals.json"
    _write_proposals(
        path,
        [
            {
                "template": "flash_loan_oracle",
                "seed_id": seed.hypothesis_id,
                "parameters": dict(_SEED_VECTOR.parameters),
            },
            {
                "template": "reentrancy",
                "seed_id": seed.hypothesis_id,
                "parameters": {
                    "recursion_intensity": 0.5,
                    "callback_exploitability": 0.6,
                },
            },
            {
                "template": "flash_loan_oracle",
                "seed_id": "other-seed",
                "parameters": dict(_SEED_VECTOR.parameters),
            },
        ],
    )
    doc = load_external_proposals(path)
    matched = external_proposals_for_seed(doc, seed, limit=5)
    assert len(matched) == 1
    assert matched[0].template == "flash_loan_oracle"
    assert matched[0].metadata["generation_method"] == "hermes_delegate"
    assert matched[0].metadata["trusted"] is False


def test_external_proposals_rejects_out_of_range_parameters(tmp_path: Path):
    seed = attack_vector_to_hypothesis(_SEED_VECTOR, generation_method="test_seed")
    path = tmp_path / "proposals.json"
    bad = dict(_SEED_VECTOR.parameters)
    bad["price_skew_severity"] = 99.0
    _write_proposals(
        path,
        [{"template": "flash_loan_oracle", "seed_id": seed.hypothesis_id, "parameters": bad}],
    )
    doc = load_external_proposals(path)
    assert external_proposals_for_seed(doc, seed, limit=5) == []


def test_orchestrator_external_provider_uses_file(tmp_path: Path):
    seed = attack_vector_to_hypothesis(_SEED_VECTOR, generation_method="test_seed")
    path = tmp_path / "proposals.json"
    _write_proposals(
        path,
        [
            {
                "template": "flash_loan_oracle",
                "seed_id": seed.hypothesis_id,
                "parameters": dict(_SEED_VECTOR.parameters),
                "delegate_note": "mango analogue probe",
            }
        ],
    )
    orchestrator = LLMExpansionOrchestrator(
        enabled=True,
        fallback="parametric",
        provider_config={
            "provider": "external",
            "proposals_path": str(path),
        },
    )
    proposals = orchestrator.propose_variants(seed, n=2)
    assert len(proposals) >= 1
    assert proposals[0].metadata["generation_method"] == "hermes_delegate"


def test_generate_llm_expanded_attack_vectors_external(tmp_path: Path):
    seed_vector = _SEED_VECTOR
    path = tmp_path / "proposals.json"
    seed_hypothesis = attack_vector_to_hypothesis(seed_vector, generation_method="test_seed")
    _write_proposals(
        path,
        [
            {
                "template": "flash_loan_oracle",
                "seed_id": seed_hypothesis.hypothesis_id,
                "parameters": dict(seed_vector.parameters),
            }
        ],
    )
    vectors = generate_llm_expanded_attack_vectors(
        "flash_loan_oracle",
        [seed_vector],
        variants_per_seed=2,
        enabled=True,
        fallback="parametric",
        provider_config={"provider": "external", "proposals_path": str(path)},
    )
    assert len(vectors) >= 1
    assert vectors[0].template_id == "flash_loan_oracle"