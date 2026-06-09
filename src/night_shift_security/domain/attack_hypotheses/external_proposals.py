"""Load Hermes delegate_task hypothesis proposals — untrusted, gated by validate_hypothesis()."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from night_shift_security.domain.attack_hypotheses.base import (
    AttackHypothesis,
    _base_metadata,
    _new_hypothesis_id,
    get_generator,
    validate_hypothesis,
)

logger = logging.getLogger(__name__)


@dataclass
class ExternalProposalsDocument:
    """Hermes-written proposals sidecar for pipeline ingestion."""

    run_id: str
    campaign_id: str | None = None
    proposals: list[dict[str, Any]] = field(default_factory=list)
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "campaign_id": self.campaign_id,
            "proposals": self.proposals,
        }


def load_external_proposals(path: Path) -> ExternalProposalsDocument:
    """Parse and validate the top-level JSON envelope."""
    if not path.is_file():
        raise FileNotFoundError(f"External proposals file not found: {path}")

    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid external proposals JSON at {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("External proposals root must be a JSON object")

    run_id = str(payload.get("run_id") or path.stem)
    campaign_id = payload.get("campaign_id")
    if campaign_id is not None:
        campaign_id = str(campaign_id)

    raw_proposals = payload.get("proposals", [])
    if not isinstance(raw_proposals, list):
        raise ValueError("External proposals 'proposals' must be a JSON array")

    proposals: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_proposals):
        if not isinstance(item, dict):
            raise ValueError(f"Proposal at index {idx} must be a JSON object")
        proposals.append(dict(item))

    return ExternalProposalsDocument(
        run_id=run_id,
        campaign_id=campaign_id,
        proposals=proposals,
        source_path=str(path),
    )


def _hypothesis_from_external_proposal(
    proposal: dict[str, Any],
    *,
    seed: AttackHypothesis | None,
    source_path: str | None,
) -> AttackHypothesis | None:
    template = str(proposal.get("template", "")).strip()
    parameters = proposal.get("parameters")
    if not template or not isinstance(parameters, dict):
        logger.debug("Skipping external proposal with missing template/parameters")
        return None

    if get_generator(template) is None:
        logger.debug("Skipping external proposal for unknown template %s", template)
        return None

    seed_id = str(proposal.get("seed_id") or (seed.hypothesis_id if seed else ""))
    lineage = proposal.get("lineage")
    if isinstance(lineage, list):
        lineage_ids = [str(x) for x in lineage]
    elif seed is not None:
        lineage_ids = list(seed.metadata.get("lineage", []))
        if seed.hypothesis_id not in lineage_ids:
            lineage_ids.append(seed.hypothesis_id)
    else:
        lineage_ids = [seed_id] if seed_id else []

    parent_ids = [seed_id] if seed_id else []
    delegate_note = proposal.get("delegate_note")
    metadata = _base_metadata(
        generation_method="hermes_delegate",
        template=template,
        parent_ids=parent_ids,
        lineage=lineage_ids,
        trusted=False,
    )
    metadata["llm_expansion"] = {
        "enabled": True,
        "provider": "external",
        "source_path": source_path,
        "seed_id": seed_id,
        "note": "hermes_delegate",
    }
    if isinstance(delegate_note, str) and delegate_note.strip():
        metadata["delegate_note"] = delegate_note.strip()

    hypothesis = AttackHypothesis(
        hypothesis_id=_new_hypothesis_id(),
        template=template,
        parameters=dict(parameters),
        metadata=metadata,
    )
    valid, reason = validate_hypothesis(hypothesis)
    if not valid:
        logger.debug("External proposal rejected by validate_hypothesis: %s", reason)
        return None
    return hypothesis


def external_proposals_for_seed(
    document: ExternalProposalsDocument,
    seed: AttackHypothesis,
    *,
    limit: int,
) -> list[AttackHypothesis]:
    """Return validated proposals matching the seed template (and seed_id when set)."""
    matched: list[AttackHypothesis] = []
    seed_id = seed.hypothesis_id

    for proposal in document.proposals:
        if str(proposal.get("template", "")).strip() != seed.template:
            continue
        proposal_seed = proposal.get("seed_id")
        if proposal_seed is not None and str(proposal_seed) != seed_id:
            continue

        hypothesis = _hypothesis_from_external_proposal(
            proposal,
            seed=seed,
            source_path=document.source_path,
        )
        if hypothesis is not None:
            matched.append(hypothesis)
        if len(matched) >= limit:
            break

    return matched


def external_proposals_for_template(
    document: ExternalProposalsDocument,
    template_id: str,
    *,
    limit: int,
) -> list[AttackHypothesis]:
    """Return validated template-level proposals (no seed binding)."""
    matched: list[AttackHypothesis] = []
    for proposal in document.proposals:
        if str(proposal.get("template", "")).strip() != template_id:
            continue
        if proposal.get("seed_id") is not None:
            continue

        hypothesis = _hypothesis_from_external_proposal(
            proposal,
            seed=None,
            source_path=document.source_path,
        )
        if hypothesis is not None:
            matched.append(hypothesis)
        if len(matched) >= limit:
            break

    return matched