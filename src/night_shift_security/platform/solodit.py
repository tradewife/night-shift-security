"""Cyfrin Solodit findings corpus sync and deterministic pattern extraction."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from night_shift_security.data.schemas import AttackCandidateResult

SOLODIT_BASE_URL = "https://solodit.cyfrin.io/api/v1/solodit"
SOLODIT_FINDINGS_URL = f"{SOLODIT_BASE_URL}/findings"
DEFAULT_OUTPUT_DIR = Path("data/security_results/platform")
DEFAULT_FINDINGS_PATH = DEFAULT_OUTPUT_DIR / "solodit_findings.json"
DEFAULT_PATTERNS_PATH = Path("data/security_results/knowledge/solodit_patterns.jsonl")

DEFAULT_TARGET_TERMS = (
    "wormhole",
    "kamino",
    "klend",
    "uniswap",
    "reserve",
    "euler",
    "polymarket",
    "coinbase",
    "morpho",
    "pendle",
    "okx",
    "paxos",
    "ethena",
    "jito",
)
DEFAULT_PATTERN_TAGS = (
    "Oracle",
    "Access Control",
    "Bridge",
    "Reentrancy",
    "Flash Loan",
    "Price Manipulation",
    "Logic Error",
)

TAG_TEMPLATE_HINTS = {
    "access control": "access_control_escalation",
    "bridge": "access_control_escalation",
    "oracle": "flash_loan_oracle",
    "price manipulation": "flash_loan_oracle",
    "flash loan": "flash_loan_oracle",
    "reentrancy": "reentrancy",
    "logic error": "composability_risk",
    "governance": "governance_capture",
}


class SoloditError(RuntimeError):
    """Raised for hard Solodit API failures."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_key(api_key: str | None = None) -> str:
    return str(api_key or os.environ.get("CYFRIN_API_KEY") or "").strip()


def _post_json(url: str, payload: dict[str, Any], api_key: str, *, timeout: int = 60) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Cyfrin-API-Key": api_key,
            "User-Agent": "night-shift-security/4.1-solodit",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body else {}
        except (OSError, json.JSONDecodeError):
            payload = {}
        message = payload.get("message") or str(exc)
        raise SoloditError(f"solodit_http_{exc.code}: {message}") from exc


HttpPost = Callable[[dict[str, Any]], dict[str, Any]]


def _label_value(value: str) -> dict[str, str]:
    return {"value": value}


def solodit_queries(
    *,
    scope: str = "target-plus-pattern",
    min_quality: int = 3,
    impacts: list[str] | None = None,
    target_terms: tuple[str, ...] = DEFAULT_TARGET_TERMS,
    pattern_tags: tuple[str, ...] = DEFAULT_PATTERN_TAGS,
) -> list[dict[str, Any]]:
    """Build deterministic Solodit query presets."""
    impacts = impacts or ["HIGH", "MEDIUM"]
    common = {
        "impact": impacts,
        "qualityScore": min_quality,
        "sortField": "Quality",
        "sortDirection": "Desc",
    }
    queries: list[dict[str, Any]] = []
    if scope in ("target-plus-pattern", "targets-only"):
        for term in target_terms:
            queries.append(
                {
                    "query_key": f"protocol:{term}",
                    "filters": {**common, "protocol": term},
                }
            )
    if scope in ("target-plus-pattern", "broad-high-quality"):
        for tag in pattern_tags:
            queries.append(
                {
                    "query_key": f"tag:{tag.lower().replace(' ', '-')}",
                    "filters": {**common, "tags": [_label_value(tag)]},
                }
            )
    if scope == "broad-high-quality":
        queries.insert(
            0,
            {
                "query_key": "broad:quality",
                "filters": {**common, "rarityScore": min_quality, "sortField": "Rarity"},
            },
        )
    return queries


def _extract_titles(rows: list[dict[str, Any]], outer_key: str, inner_key: str) -> list[str]:
    values: list[str] = []
    for row in rows or []:
        outer = row.get(outer_key) if isinstance(row, dict) else None
        if isinstance(outer, dict):
            title = outer.get(inner_key)
            if title:
                values.append(str(title))
    return sorted(set(values))


def _normalize_finding(row: dict[str, Any], *, query_key: str, synced_at: str) -> dict[str, Any]:
    protocol = row.get("protocols_protocol") if isinstance(row.get("protocols_protocol"), dict) else {}
    categories = []
    for item in protocol.get("protocols_protocolcategoryscore") or []:
        cat = item.get("protocols_protocolcategory") if isinstance(item, dict) else None
        if isinstance(cat, dict) and cat.get("title"):
            categories.append(str(cat["title"]))
    finders = []
    for item in row.get("issues_issue_finders") or []:
        warden = item.get("wardens_warden") if isinstance(item, dict) else None
        if isinstance(warden, dict) and warden.get("handle"):
            finders.append(str(warden["handle"]))
    return {
        "source": "solodit",
        "query_key": query_key,
        "synced_at": synced_at,
        "solodit_id": str(row.get("id") or ""),
        "slug": str(row.get("slug") or ""),
        "title": str(row.get("title") or ""),
        "content": str(row.get("content") or ""),
        "summary": row.get("summary"),
        "kind": str(row.get("kind") or ""),
        "impact": str(row.get("impact") or ""),
        "quality_score": float(row.get("quality_score") or 0),
        "rarity_score": float(row.get("general_score") or 0),
        "report_date": row.get("report_date"),
        "auditfirm_id": row.get("auditfirm_id"),
        "firm_name": row.get("firm_name") or (row.get("auditfirms_auditfirm") or {}).get("name"),
        "protocol_id": row.get("protocol_id"),
        "protocol_name": row.get("protocol_name") or protocol.get("name"),
        "protocol_categories": sorted(set(categories)),
        "contest_id": row.get("contest_id"),
        "contest_link": row.get("contest_link"),
        "contest_prize_txt": row.get("contest_prize_txt"),
        "sponsor_name": row.get("sponsor_name"),
        "sponsor_link": row.get("sponsor_link"),
        "finders_count": int(row.get("finders_count") or 0),
        "finders": sorted(set(finders)),
        "tags": _extract_titles(row.get("issues_issuetagscore") or [], "tags_tag", "title"),
        "source_link": row.get("source_link"),
        "github_link": row.get("github_link"),
        "pdf_link": row.get("pdf_link"),
        "pdf_page_from": row.get("pdf_page_from"),
    }


def sync_solodit_findings(
    output_dir: Path | None = None,
    *,
    api_key: str | None = None,
    scope: str = "target-plus-pattern",
    page_size: int = 100,
    max_pages_per_query: int = 2,
    min_quality: int = 3,
    impacts: list[str] | None = None,
    http_post: HttpPost | None = None,
    sleep_seconds: float = 3.0,
) -> dict[str, Any]:
    """Fetch Solodit findings into deterministic JSON, or skip if no API key."""
    out = output_dir or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    key = _api_key(api_key)
    if not key and http_post is None:
        payload = {
            "schema_version": "1.0",
            "source": "solodit_findings_api",
            "status": "skipped_missing_key",
            "synced_at": _utc_now(),
            "findings": [],
            "queries": [],
        }
        path = out / "solodit_findings.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return {"status": "skipped_missing_key", "path": str(path), "finding_count": 0}

    queries = solodit_queries(scope=scope, min_quality=min_quality, impacts=impacts)
    post = http_post or (lambda payload: _post_json(SOLODIT_FINDINGS_URL, payload, key))
    synced_at = _utc_now()
    findings: dict[str, dict[str, Any]] = {}
    query_summaries: list[dict[str, Any]] = []

    for query in queries:
        query_key = str(query["query_key"])
        pages = 0
        total_results = 0
        query_error = ""
        for page in range(1, max_pages_per_query + 1):
            request = {"page": page, "pageSize": min(max(page_size, 1), 100), "filters": query["filters"]}
            try:
                response = post(request)
            except SoloditError as exc:
                query_error = str(exc)
                break
            metadata = response.get("metadata") or {}
            total_pages = int(metadata.get("totalPages") or 1)
            total_results = int(metadata.get("totalResults") or 0)
            rows = response.get("findings") or []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                normalized = _normalize_finding(row, query_key=query_key, synced_at=synced_at)
                dedupe_key = normalized["solodit_id"] or normalized["slug"]
                if not dedupe_key:
                    continue
                existing = findings.get(dedupe_key)
                if existing is None:
                    findings[dedupe_key] = normalized
                else:
                    keys = set(str(existing.get("query_key", "")).split(",")) | {query_key}
                    existing["query_key"] = ",".join(sorted(k for k in keys if k))
            pages += 1
            if page >= total_pages:
                break
            if sleep_seconds > 0 and http_post is None:
                time.sleep(sleep_seconds)
        if query_error:
            query_summaries.append(
                {"query_key": query_key, "status": "error", "pages": pages, "message": query_error}
            )
        else:
            query_summaries.append(
                {
                    "query_key": query_key,
                    "status": "ok",
                    "pages": pages,
                    "total_results": total_results,
                }
            )

    ordered = sorted(findings.values(), key=lambda r: (-r["quality_score"], -r["rarity_score"], r["title"]))
    payload = {
        "schema_version": "1.0",
        "source": "solodit_findings_api",
        "status": "ok",
        "synced_at": synced_at,
        "scope": scope,
        "query_count": len(queries),
        "finding_count": len(ordered),
        "queries": query_summaries,
        "findings": ordered,
    }
    path = out / "solodit_findings.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "status": "ok",
        "path": str(path),
        "finding_count": len(ordered),
        "query_count": len(queries),
    }


def _template_hints(tags: list[str], title: str) -> list[str]:
    haystack = " ".join([title, *tags]).lower()
    hints = [template for token, template in TAG_TEMPLATE_HINTS.items() if token in haystack]
    return sorted(set(hints))


def build_solodit_patterns(findings_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Distill normalized findings into compact pattern records for RSI/agents."""
    patterns: list[dict[str, Any]] = []
    for row in findings_payload.get("findings") or []:
        if not isinstance(row, dict):
            continue
        tags = [str(t) for t in row.get("tags") or []]
        pattern_id = f"solodit:{row.get('solodit_id') or row.get('slug')}"
        patterns.append(
            {
                "pattern_id": pattern_id,
                "source": "solodit",
                "title": row.get("title", ""),
                "impact": row.get("impact", ""),
                "quality_score": float(row.get("quality_score") or 0),
                "rarity_score": float(row.get("rarity_score") or 0),
                "protocol_name": row.get("protocol_name") or "",
                "firm_name": row.get("firm_name") or "",
                "report_date": row.get("report_date"),
                "tags": tags,
                "protocol_categories": list(row.get("protocol_categories") or []),
                "template_hints": _template_hints(tags, str(row.get("title") or "")),
                "source_link": row.get("source_link"),
                "github_link": row.get("github_link"),
                "pdf_link": row.get("pdf_link"),
                "query_key": row.get("query_key", ""),
            }
        )
    return sorted(
        patterns,
        key=lambda r: (-r["quality_score"], -r["rarity_score"], str(r["title"])),
    )


def write_solodit_patterns(input_path: Path, output_path: Path = DEFAULT_PATTERNS_PATH) -> dict[str, Any]:
    payload = json.loads(input_path.read_text()) if input_path.is_file() else {"findings": []}
    patterns = build_solodit_patterns(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as fh:
        for pattern in patterns:
            fh.write(json.dumps(pattern, sort_keys=True) + "\n")
    return {"status": "ok", "path": str(output_path), "pattern_count": len(patterns)}


def load_solodit_patterns(path: Path = DEFAULT_PATTERNS_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    patterns: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            patterns.append(payload)
    return patterns


def apply_solodit_enrichment(
    candidates: list[AttackCandidateResult],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stamp best-matching Solodit analogue refs into candidate metadata."""
    cfg = config or {}
    if not cfg.get("enabled", True):
        return {"enabled": False, "matched": 0, "pattern_count": 0}
    patterns = load_solodit_patterns(Path(cfg.get("patterns_path", DEFAULT_PATTERNS_PATH)))
    if not patterns:
        return {"enabled": True, "matched": 0, "pattern_count": 0}
    max_refs = int(cfg.get("max_refs_per_candidate", 3))
    matched = 0
    for candidate in candidates:
        target = candidate.vector.target_id.lower()
        template = candidate.vector.template_id
        label = candidate.vector.label.lower()
        refs: list[dict[str, Any]] = []
        for pattern in patterns:
            hints = set(pattern.get("template_hints") or [])
            protocol = str(pattern.get("protocol_name") or "").lower()
            query_key = str(pattern.get("query_key") or "").lower()
            title = str(pattern.get("title") or "").lower()
            label_match = bool(label and label in title)
            target_match = bool(target and (target in protocol or target in query_key or target in title))
            if template not in hints and not target_match and not label_match:
                continue
            refs.append(
                {
                    "pattern_id": pattern.get("pattern_id"),
                    "title": pattern.get("title"),
                    "impact": pattern.get("impact"),
                    "quality_score": pattern.get("quality_score"),
                    "rarity_score": pattern.get("rarity_score"),
                    "tags": pattern.get("tags", [])[:8],
                    "source_link": pattern.get("source_link"),
                }
            )
            if len(refs) >= max_refs:
                break
        if refs:
            meta = candidate.vector.metadata
            meta["solodit_refs"] = refs
            meta["solodit_quality_max"] = max(float(r.get("quality_score") or 0) for r in refs)
            meta["solodit_rarity_max"] = max(float(r.get("rarity_score") or 0) for r in refs)
            meta["solodit_tags"] = sorted({tag for r in refs for tag in r.get("tags", [])})
            matched += 1
    return {"enabled": True, "matched": matched, "pattern_count": len(patterns)}
