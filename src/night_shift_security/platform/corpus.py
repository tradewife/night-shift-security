"""Union adapter for advisory security corpora.

Wraps :mod:`night_shift_security.platform.solodit` and
:mod:`night_shift_security.platform.auditvault` so the rest of the engine can
treat them as a single ``AuditCorpus``. The corpus is advisory only: it never
replaces live reproduction, fork validation, or submission gates.

Who can call what:
- ``apply_corpus_enrichment`` is the only entry-point that mutates candidate
  metadata. It adds ``solodit_refs``, ``auditvault_refs``, ``audit_corpus_score``,
  and ``atlas_axes`` stamps. None of these are read by
  :mod:`night_shift_security.validation.submission_gates`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from night_shift_security.data.schemas import AttackCandidateResult
from night_shift_security.platform.auditvault import (
    load_auditvault_patterns,
)
from night_shift_security.platform.solodit import (
    DEFAULT_PATTERNS_PATH,
    load_solodit_patterns,
)

AUDIT_CORPUS_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "solodit": {
        "enabled": True,
        "patterns_path": str(DEFAULT_PATTERNS_PATH),
        "max_refs_per_candidate": 3,
    },
    "auditvault": {
        "enabled": True,
        "patterns_lookup_path": "data/security_results/knowledge/auditvault_patterns.jsonl",
        "ids_lookup_path": "data/security_results/knowledge/auditvault_ids.jsonl",
        "max_refs_per_candidate": 3,
        "severity_min": 3,
    },
    "conviction": {
        "enabled": True,
        "bonus_per_ref": 0.02,
        "bonus_cap": 0.05,
        "min_severity_to_bonus": 3,
    },
}


def _load_solodit_block(config: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = config.get("solodit") or {}
    if not cfg.get("enabled", True):
        return []
    return load_solodit_patterns(Path(cfg.get("patterns_path", DEFAULT_PATTERNS_PATH)))


def _load_auditvault_blocks(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    cfg = config.get("auditvault") or {}
    if not cfg.get("enabled", True):
        return [], {}
    patterns = load_auditvault_patterns(Path(cfg.get("patterns_lookup_path", "data/security_results/knowledge/auditvault_patterns.jsonl")))

    ids_lookup: dict[str, list[dict[str, Any]]] = {}
    ids_path = Path(cfg.get("ids_lookup_path", "data/security_results/knowledge/auditvault_ids.jsonl"))
    if ids_path.is_file():
        for line in ids_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            slug = str(row.get("slug") or "").strip().lower()
            if not slug:
                continue
            ids_lookup.setdefault(slug, []).append(row)
    return patterns, ids_lookup


def _match_auditvault(
    target: str,
    template: str,
    label: str,
    patterns: list[dict[str, Any]],
    ids_lookup: dict[str, list[dict[str, Any]]],
    *,
    max_refs: int,
    severity_min: float,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    target_l = target.lower()
    template_l = template.lower()
    label_l = label.lower()
    # Prefer per-slug ids when the target matches.
    per_slug = ids_lookup.get(target_l, [])
    per_slug.sort(key=lambda r: (-float(r.get("severity_score") or 0), str(r.get("title") or "")))
    for row in per_slug:
        if float(row.get("severity_score") or 0) < severity_min:
            continue
        if template_l and template_l not in [str(h).lower() for h in (row.get("template_hints") or [])]:
            if template_l not in str(row.get("title") or "").lower():
                continue
        ref = {
            "pattern_id": f"auditvault:{row.get('auditvault_id')}",
            "title": row.get("title"),
            "severity_score": float(row.get("severity_score") or 0),
            "atlas_axes": list(row.get("atlas_axes") or []),
            "template_hints": list(row.get("template_hints") or []),
            "report_date": row.get("report_date"),
        }
        if ref["pattern_id"] in seen:
            continue
        seen.add(ref["pattern_id"])
        refs.append(ref)
        if len(refs) >= max_refs:
            return refs
    # Fall back to title/label scanning.
    for pattern in patterns:
        proto = str(pattern.get("protocol_slug") or "").lower()
        title = str(pattern.get("title") or "").lower()
        if len(refs) >= max_refs:
            break
        if target_l and target_l not in proto and target_l not in title:
            if not label_l or label_l not in title:
                continue
        if template_l and template_l not in [str(h).lower() for h in (pattern.get("template_hints") or [])]:
            continue
        ref = {
            "pattern_id": pattern.get("pattern_id"),
            "title": pattern.get("title"),
            "severity_score": float(pattern.get("severity_score") or 0),
            "atlas_axes": list(pattern.get("atlas_axes") or []),
            "template_hints": list(pattern.get("template_hints") or []),
            "report_date": pattern.get("report_date"),
        }
        if ref["pattern_id"] in seen:
            continue
        seen.add(ref["pattern_id"])
        refs.append(ref)
    return refs


def _audit_corpus_conviction_bonus(
    audit_refs: list[dict[str, Any]],
    *,
    solodit_refs: list[dict[str, Any]] | None = None,
    conviction_cfg: dict[str, Any] | None = None,
) -> float:
    """Advisory conviction bonus from advisory matches only.

    Returns a float in [0, bonus_cap]. Bonus never crosses
    :data:`AUDIT_CORPUS_DEFAULTS` cap (0.05) and is gated on a minimum
    severity_score so weak/noisy entries do not cheapen reporting.
    """
    if not conviction_cfg or not conviction_cfg.get("enabled", True):
        return 0.0
    bonus_per_ref = float(conviction_cfg.get("bonus_per_ref", 0.02))
    cap = float(conviction_cfg.get("bonus_cap", 0.05))
    min_severity = float(conviction_cfg.get("min_severity_to_bonus", 3))

    total = 0.0
    counted = 0
    for ref in audit_refs:
        if float(ref.get("severity_score") or 0) < min_severity:
            continue
        total += bonus_per_ref
        counted += 1
        if total >= cap:
            return cap
    # Solodit refs earn half weight to acknowledge independent origin.
    for ref in solodit_refs or []:
        if total >= cap:
            break
        if float(ref.get("quality_score") or 0) < 3:
            continue
        total += bonus_per_ref * 0.5
        counted += 1
    return min(total, cap)


def enrich_with_audit_corpus(
    candidates: list[AttackCandidateResult],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stamp advisory Solodit + AuditVault refs onto candidate metadata.

    Mirrors the surface of :func:`apply_solodit_enrichment` so the pipeline and
    self-interrogation can call one union operation without re-loading corpora.
    """
    cfg = {**AUDIT_CORPUS_DEFAULTS, **(config or {})}
    if not cfg.get("enabled", True):
        return {"enabled": False, "matched": 0, "auditvault_matched": 0, "solodit_matched": 0}

    solodit_patterns = _load_solodit_block(cfg)
    auditvault_patterns, auditvault_ids = _load_auditvault_blocks(cfg)

    solodit_cfg = dict(cfg.get("solodit") or {})
    audit_cfg = dict(cfg.get("auditvault") or {})
    conv_cfg = dict(cfg.get("conviction") or {})

    matched = 0
    audit_matched = 0
    sol_matched = 0

    for candidate in candidates:
        target = str(candidate.vector.target_id or "").lower()
        template = str(candidate.vector.template_id or "")
        label = str(candidate.vector.label or "")
        meta = candidate.vector.metadata

        # Solodit reuse — emit identical stamps as before so existing callers
        # keep working without behavioural change.
        sol_refs: list[dict[str, Any]] = []
        if solodit_patterns:
            max_refs = int(solodit_cfg.get("max_refs_per_candidate", 3))
            for pattern in solodit_patterns:
                hints = set(str(h).lower() for h in (pattern.get("template_hints") or []))
                protocol = str(pattern.get("protocol_name") or "").lower()
                query_key = str(pattern.get("query_key") or "").lower()
                title = str(pattern.get("title") or "").lower()
                label_match = bool(label and label.lower() in title)
                target_match = bool(target and (target in protocol or target in query_key or target in title))
                if template.lower() not in hints and not target_match and not label_match:
                    continue
                sol_refs.append({
                    "pattern_id": pattern.get("pattern_id"),
                    "title": pattern.get("title"),
                    "impact": pattern.get("impact"),
                    "quality_score": pattern.get("quality_score"),
                    "rarity_score": pattern.get("rarity_score"),
                    "tags": list(pattern.get("tags") or [])[:8],
                    "source_link": pattern.get("source_link"),
                })
                if len(sol_refs) >= max_refs:
                    break

        audit_refs = _match_auditvault(
            target,
            template,
            label,
            auditvault_patterns,
            auditvault_ids,
            max_refs=int(audit_cfg.get("max_refs_per_candidate", 3)),
            severity_min=float(audit_cfg.get("severity_min", 3)),
        )

        if not sol_refs and not audit_refs:
            continue

        matched += 1
        if sol_refs:
            meta["solodit_refs"] = sol_refs
            meta["solodit_quality_max"] = max(float(r.get("quality_score") or 0) for r in sol_refs)
            meta["solodit_rarity_max"] = max(float(r.get("rarity_score") or 0) for r in sol_refs)
            meta["solodit_tags"] = sorted({tag for r in sol_refs for tag in r.get("tags", [])})
            sol_matched += 1
        if audit_refs:
            meta["auditvault_refs"] = audit_refs
            meta["auditvault_severity_max"] = max(float(r.get("severity_score") or 0) for r in audit_refs)
            meta["atlas_axes"] = sorted({
                axis for r in audit_refs for axis in r.get("atlas_axes", [])
            })
            audit_matched += 1

        bonus = _audit_corpus_conviction_bonus(audit_refs, solodit_refs=sol_refs, conviction_cfg=conv_cfg)
        meta["audit_corpus_score"] = bonus
        meta["audit_corpus_ref_count"] = len(sol_refs) + len(audit_refs)

    return {
        "enabled": True,
        "matched": matched,
        "auditvault_matched": audit_matched,
        "solodit_matched": sol_matched,
        "solodit_pattern_count": len(solodit_patterns),
        "auditvault_pattern_count": len(auditvault_patterns),
    }


__all__ = [
    "AUDIT_CORPUS_DEFAULTS",
    "enrich_with_audit_corpus",
]
