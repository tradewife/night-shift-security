"""Concrete v4 candidate schema and seed construction."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConcreteCandidate:
    candidate_id: str
    target_slug: str
    campaign_id: str
    chain: str
    source_ref: dict[str, Any]
    entrypoint: dict[str, Any]
    actors: list[dict[str, Any]]
    state_bindings: dict[str, Any]
    sequence: list[dict[str, Any]]
    invariant: dict[str, Any]
    impact_oracle: dict[str, Any]
    provenance: dict[str, Any] = field(default_factory=dict)
    candidate_schema_version: int = 4
    target_pinned: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConcreteCandidate":
        return cls(
            candidate_id=str(data.get("candidate_id") or ""),
            target_slug=str(data.get("target_slug") or ""),
            campaign_id=str(data.get("campaign_id") or ""),
            chain=str(data.get("chain") or ""),
            source_ref=dict(data.get("source_ref") or {}),
            entrypoint=dict(data.get("entrypoint") or {}),
            actors=list(data.get("actors") or []),
            state_bindings=dict(data.get("state_bindings") or {}),
            sequence=list(data.get("sequence") or []),
            invariant=dict(data.get("invariant") or {}),
            impact_oracle=dict(data.get("impact_oracle") or {}),
            provenance=dict(data.get("provenance") or {}),
            candidate_schema_version=int(data.get("candidate_schema_version") or 4),
            target_pinned=bool(data.get("target_pinned", True)),
        )


def _candidate_id(slug: str, entry: dict[str, Any], invariant_id: str) -> str:
    key = "|".join(
        [
            slug,
            str(entry.get("kind") or ""),
            str(entry.get("file") or ""),
            str(entry.get("name") or ""),
            invariant_id,
        ]
    )
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _chain_for(entry: dict[str, Any]) -> str:
    kind = str(entry.get("kind") or "")
    if kind.startswith("solana"):
        return "solana"
    if kind.startswith("solidity"):
        return "ethereum"
    return "unknown"


def _invariant_for(entry: dict[str, Any], *, kind: str | None = None) -> dict[str, str]:
    name = str(entry.get("name") or "").lower()
    signals = entry.get("signals") if isinstance(entry.get("signals"), dict) else {}
    if kind == "bridge" or signals.get("bridge") or any(k in name for k in ("bridge", "message", "vaa", "emitter")):
        return {
            "id": "bridge_accounting",
            "predicate": "released_or_minted_assets_require_authorized_source_lock_or_burn",
            "expected_violation": "value_moves_without_valid_message_or_source_accounting",
        }
    if kind == "oracle" or signals.get("oracle") or any(k in name for k in ("oracle", "price", "refresh")):
        return {
            "id": "oracle_freshness",
            "predicate": "borrow_or_liquidation_uses_fresh_bounded_oracle_state",
            "expected_violation": "stale_or_unbounded_price_changes_protocol_value",
        }
    if any(k in name for k in ("admin", "owner", "authority", "pause", "upgrade")):
        return {
            "id": "authorized_role_transition",
            "predicate": "critical_role_or_upgrade_changes_require_authorized_actor",
            "expected_violation": "unauthorized_actor_changes_critical_state",
        }
    return {
        "id": "value_conservation",
        "predicate": "post_protocol_assets_plus_attacker_assets_do_not_exceed_authorized_prestate",
        "expected_violation": "attacker_balance_increases_without_authorized_protocol_debit",
    }


def candidate_from_entrypoint(
    entry: dict[str, Any],
    *,
    target_slug: str,
    campaign_id: str,
    kind: str | None = None,
    provenance_source: str = "semantic_recon",
) -> ConcreteCandidate:
    invariant = _invariant_for(entry, kind=kind)
    cid = _candidate_id(target_slug, entry, invariant["id"])
    selector = str(entry.get("selector_or_discriminator") or "")
    return ConcreteCandidate(
        candidate_id=cid,
        target_slug=target_slug,
        campaign_id=campaign_id,
        chain=_chain_for(entry),
        source_ref=dict(entry.get("source_ref") or {}),
        entrypoint={
            "kind": entry.get("kind"),
            "name": entry.get("name"),
            "selector_or_discriminator": selector,
            "file": entry.get("file"),
            "line": entry.get("line"),
        },
        actors=[{"role": "attacker", "constraints": ["not_authorized", "funded"]}],
        state_bindings={
            "contracts": {},
            "accounts": {},
            "storage_slots": {},
            "token_accounts": {},
        },
        sequence=[{"call": entry.get("name"), "params": {}, "sender": "attacker"}],
        invariant=invariant,
        impact_oracle={
            "metric": "TOKEN_DELTA",
            "threshold": "non_fee_positive_delta_or_bounded_tvs",
            "measured": False,
        },
        provenance={
            "source": provenance_source,
            "trusted": False,
            "evidence": [entry.get("file")] if entry.get("file") else [],
        },
    )


def build_candidate_seeds(
    semantic_map: dict[str, Any],
    *,
    target_slug: str,
    campaign_id: str = "",
    kind: str | None = None,
) -> list[ConcreteCandidate]:
    campaign = campaign_id or f"semantic-{target_slug}"
    entries = list(semantic_map.get("entrypoints") or [])
    if kind:
        kind_l = kind.lower()
        entries = [
            e
            for e in entries
            if kind_l in json.dumps(e.get("signals", {})).lower()
            or kind_l in str(e.get("name") or "").lower()
            or kind_l in str(e.get("file") or "").lower()
        ]
    candidates: list[ConcreteCandidate] = []
    seen: set[str] = set()
    for entry in entries:
        candidate = candidate_from_entrypoint(
            entry,
            target_slug=target_slug,
            campaign_id=campaign,
            kind=kind,
        )
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        candidates.append(candidate)
    return candidates


def write_candidates_jsonl(candidates: list[ConcreteCandidate], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for candidate in candidates:
            fh.write(json.dumps(candidate.to_dict(), sort_keys=True) + "\n")
    return path
