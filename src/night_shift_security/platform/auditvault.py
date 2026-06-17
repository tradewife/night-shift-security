"""Auditware AuditVault corpus loader.

Reads the local clone of https://github.com/Auditware/AuditVault (Obsidian-style
markdown) and emits a normalized Findings-like JSON document plus a deterministic
patterns JSONL, mirroring the public surface of :mod:`solodit`.

AuditVault is treated strictly as advisory metadata. It must NEVER satisfy any
live-reproduction, deployment-viability, fork-validity, or submission gate in
:mod:`night_shift_security.validation.submission_gates`. See SPEC.md §2.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_REPO_PATH = Path("sources/auditvault/repo")
DEFAULT_OUTPUT_DIR = Path("data/security_results/platform")
DEFAULT_FINDINGS_PATH = DEFAULT_OUTPUT_DIR / "auditvault_findings.json"
DEFAULT_PATTERNS_PATH = Path("data/security_results/knowledge/auditvault_patterns.jsonl")
DEFAULT_KNOWLEDGE_PATH = Path("data/security_results/knowledge/auditvault_ids.jsonl")

SCHEMA_VERSION = "1.0"

# Subdirectories within AuditVault that yield findings worth indexing.
_FINDINGS_SUBDIRS = ("findings",)
_CLASSIFICATIONS_BUG_SUBDIR = Path("classifications/bug")
_CLASSIFICATIONS_IMPACT_SUBDIR = Path("classifications/impact")
_CLASSIFICATIONS_SECTOR_SUBDIR = Path("classifications/sector")

# Obsidian frontmatter delimiter.
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]")

# Bug classification → NSS template mapping (advisory).
BUG_TO_TEMPLATE: dict[str, str] = {
    "reentrancy": "reentrancy",
    "cross-chain replay": "access_control_escalation",
    "cross chain replay": "access_control_escalation",
    "signature replay": "access_control_escalation",
    "access control": "access_control_escalation",
    "improper access control": "access_control_escalation",
    "logic error": "composability_risk",
    "business logic": "composability_risk",
    "oracle": "flash_loan_oracle",
    "price oracle": "flash_loan_oracle",
    "price manipulation": "flash_loan_oracle",
    "flash loan": "flash_loan_oracle",
    "governance": "governance_capture",
    "governance attack": "governance_capture",
    "treasury": "treasury_drain",
    "upgradeability": "upgradeability_risk",
    "proxy upgrade": "upgradeability_risk",
}

# Impact keywords → severity score (0-5). AuditVault categories encode this.
_IMPACT_SEVERITY: dict[str, int] = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "moderate": 3,
    "low": 2,
    "informational": 1,
    "info": 1,
}

# Atlas-tag axis mapping for structural filter penalty (`auditvault_axes`).
ATLAS_AXES: tuple[str, ...] = (
    "bridge",
    "oracle",
    "lending",
    "amm",
    "staking",
    "governance",
    "perpetuals",
    "messaging",
    "mev",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity_score(impact: str | None, hooks_impact: str | None = None) -> float:
    """Map AuditVault Impact/Class severity to NSS-grade float (0-5)."""
    blob = " ".join([impact or "", hooks_impact or ""]).strip().lower()
    best = 0
    for token, score in _IMPACT_SEVERITY.items():
        if token in blob:
            best = max(best, score)
    return float(best)


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse simple YAML-ish Obsidian frontmatter; defensive by design."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw_meta, body = match.group(1), match.group(2)
    meta: dict[str, Any] = {}
    for line in raw_meta.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1]
            meta[key] = [
                v.strip().strip('"').strip("'") for v in inner.split(",") if v.strip()
            ]
        elif value.startswith('"') and value.endswith('"'):
            meta[key] = value[1:-1]
        else:
            meta[key] = value
    return meta, body


def _atlas_axes(tags: list[str], body: str, sector: str | None) -> list[str]:
    haystack = " ".join([*tags, body[:2000], sector or ""]).lower()
    axes: list[str] = []
    for axis in ATLAS_AXES:
        if axis in haystack:
            axes.append(axis)
    return sorted(set(axes))


def _template_hints(impact: str | None, tags: list[str], body: str, bug_class: str | None) -> list[str]:
    haystack = " ".join([
        bug_class or "",
        impact or "",
        " ".join(tags),
        body[:2000],
    ]).lower()
    hints = [tmpl for token, tmpl in BUG_TO_TEMPLATE.items() if token in haystack]
    return sorted(set(hints))


def _protocols_in_text(text: str) -> list[str]:
    """Extract protocol slugs from Obsidian wikilinks `[[Protocol/...]]`."""
    slugs: set[str] = set()
    for match in _WIKILINK_RE.findall(text):
        head = match.split("/")[0].strip()
        if head:
            slugs.add(head)
    return sorted(slugs)


def _protocol_path(repo_root: Path) -> Path:
    return repo_root / "protocols"


def _read_protocol_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Build `{slug: {name, url?, ...}}` from `protocols/<Name>/<Name>.md`."""
    index: dict[str, dict[str, Any]] = {}
    proto_root = _protocol_path(repo_root)
    if not proto_root.is_dir():
        return index
    for entry in sorted(proto_root.iterdir()):
        if not entry.is_dir():
            continue
        slug = entry.name.strip()
        readme = entry / f"{entry.name}.md"
        if not readme.is_file():
            # Some repos use lowercase or variant; fall back to any *.md.
            cand = next(iter(sorted(entry.glob("*.md"))), None)
            if cand is None:
                continue
            readme = cand
        try:
            meta, _ = _split_frontmatter(readme.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if not isinstance(meta, dict):
            meta = {}
        name = str(meta.get("name") or slug)
        index[slug.lower()] = {
            "slug": slug,
            "name": name,
            "url": meta.get("url") or meta.get("link"),
            "sector": meta.get("sector") or meta.get("category"),
        }
    return index


def _iter_finding_paths(repo_root: Path) -> list[Path]:
    """Yield absolute paths that look like findings documents."""
    out: list[Path] = []
    for subdir in _FINDINGS_SUBDIRS:
        root = repo_root / subdir
        if not root.is_dir():
            continue
        for path in root.rglob("*.md"):
            out.append(path)
    return sorted(out)


def _normalize_finding(
    raw_path: Path,
    meta: dict[str, Any],
    body: str,
    *,
    protocol_index: dict[str, dict[str, Any]],
    repo_root: Path,
    synced_at: str,
) -> dict[str, Any]:
    rel = raw_path.relative_to(repo_root).as_posix()
    file_id = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]
    tags = [str(t) for t in (meta.get("tags") or [])]
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    impact = str(meta.get("impact") or meta.get("class") or "")
    bug_class = str(meta.get("bug") or meta.get("finding_type") or "")
    sector = str(meta.get("sector") or "")
    protocols_meta = meta.get("protocols")
    if isinstance(protocols_meta, str):
        protocols = [p.strip() for p in protocols_meta.split(",") if p.strip()]
    elif isinstance(protocols_meta, list):
        protocols = [str(p).strip() for p in protocols_meta if str(p).strip()]
    else:
        protocols = []
    wiki_protocols = _protocols_in_text(body)
    for wp in wiki_protocols:
        if wp not in protocols:
            protocols.append(wp)
    auditors = meta.get("auditors") or meta.get("auditor")
    if isinstance(auditors, str):
        auditors_clean = [a.strip() for a in auditors.split(",") if a.strip()]
    elif isinstance(auditors, list):
        auditors_clean = [str(a).strip() for a in auditors if str(a).strip()]
    else:
        auditors_clean = []
    severity = _severity_score(meta.get("impact"), meta.get("class"))
    template_hints = _template_hints(impact, tags, body, bug_class or meta.get("bug"))
    axes = _atlas_axes(tags, body, sector)
    primary_protocol = protocols[0] if protocols else ""
    primary_info = protocol_index.get(primary_protocol.lower(), {})
    return {
        "source": "auditvault",
        "synced_at": synced_at,
        "auditvault_id": file_id,
        "rel_path": rel,
        "title": str(meta.get("title") or raw_path.stem),
        "bug_class": bug_class,
        "impact": impact,
        "severity_score": severity,
        "tags": tags,
        "protocols": protocols,
        "primary_protocol_slug": primary_protocol.lower(),
        "primary_protocol_name": primary_info.get("name") or primary_protocol,
        "primary_protocol_url": primary_info.get("url"),
        "sector": sector,
        "auditors": auditors_clean,
        "report": meta.get("report") or meta.get("report_link"),
        "source_link": meta.get("source") or meta.get("link"),
        "report_date": meta.get("date") or meta.get("report_date"),
        "atlas_axes": axes,
        "template_hints": template_hints,
        "protocol_categories": [sector] if sector else [],
        "summary": body.strip()[:1200],
    }


class AuditVaultError(RuntimeError):
    """Raised when the local AuditVault repo is malformed."""


def sync_auditvault_findings(
    repo_root: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Read the local AuditVault markdown repo, normalize, and write a JSON document.

    Defensive: returns ``status: skipped_no_repo`` when the clone is missing and
    ``status: parsed_with_warnings`` when individual files fail to parse.
    """
    repo = repo_root or DEFAULT_REPO_PATH
    out = output_dir or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    synced_at = _utc_now()

    if not repo.is_dir():
        payload = {
            "schema_version": SCHEMA_VERSION,
            "source": "auditware_auditvault",
            "status": "skipped_no_repo",
            "synced_at": synced_at,
            "repo_path": str(repo),
            "finding_count": 0,
            "protocol_count": 0,
            "warnings": [f"auditvault repo missing at {repo}"],
            "findings": [],
        }
        path = out / "auditvault_findings.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return {
            "status": "skipped_no_repo",
            "path": str(path),
            "finding_count": 0,
            "protocol_count": 0,
        }

    protocol_index = _read_protocol_index(repo)
    raw_paths = _iter_finding_paths(repo)

    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw in raw_paths:
        try:
            text = raw.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"read_error:{raw}:{exc}")
            continue
        try:
            meta, body = _split_frontmatter(text)
            finding = _normalize_finding(
                raw,
                meta,
                body,
                protocol_index=protocol_index,
                repo_root=repo,
                synced_at=synced_at,
            )
        except AuditVaultError as exc:
            warnings.append(f"parse_error:{raw}:{exc}")
            continue
        findings.append(finding)

    findings.sort(
        key=lambda r: (-float(r.get("severity_score") or 0), str(r.get("title") or "")),
    )

    status = "ok" if not warnings else "parsed_with_warnings"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": "auditware_auditvault",
        "status": status,
        "synced_at": synced_at,
        "repo_path": str(repo),
        "finding_count": len(findings),
        "protocol_count": len(protocol_index),
        "warning_count": len(warnings),
        "warnings": warnings[:50],
        "findings": findings,
    }
    path = out / "auditvault_findings.json"
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "status": status,
        "path": str(path),
        "finding_count": len(findings),
        "protocol_count": len(protocol_index),
        "warning_count": len(warnings),
    }


def build_auditvault_patterns(findings_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Distill normalized AuditVault findings into compact pattern records."""
    patterns: list[dict[str, Any]] = []
    for row in findings_payload.get("findings") or []:
        if not isinstance(row, dict):
            continue
        patterns.append(
            {
                "pattern_id": f"auditvault:{row.get('auditvault_id')}",
                "source": "auditvault",
                "title": row.get("title", ""),
                "impact": row.get("impact", ""),
                "severity_score": float(row.get("severity_score") or 0),
                "protocol_slug": row.get("primary_protocol_slug", ""),
                "protocol_name": row.get("primary_protocol_name", ""),
                "protocol_url": row.get("primary_protocol_url"),
                "auditors": list(row.get("auditors") or []),
                "report_date": row.get("report_date"),
                "tags": list(row.get("tags") or []),
                "atlas_axes": list(row.get("atlas_axes") or []),
                "template_hints": list(row.get("template_hints") or []),
                "source_link": row.get("source_link"),
                "report_link": row.get("report"),
                "rel_path": row.get("rel_path"),
                "sector": row.get("sector", ""),
            }
        )
    patterns.sort(
        key=lambda r: (-r["severity_score"], -len(r["template_hints"]), str(r["title"])),
    )
    return patterns


def write_auditvault_patterns(
    input_path: Path = DEFAULT_FINDINGS_PATH,
    output_path: Path = DEFAULT_PATTERNS_PATH,
) -> dict[str, Any]:
    payload = (
        json.loads(input_path.read_text())
        if input_path.is_file()
        else {"findings": [], "status": "skipped_no_repo"}
    )
    patterns = build_auditvault_patterns(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as fh:
        for pattern in patterns:
            fh.write(json.dumps(pattern, sort_keys=True) + "\n")
    return {
        "status": payload.get("status", "ok"),
        "path": str(output_path),
        "pattern_count": len(patterns),
    }


def load_auditvault_patterns(path: Path = DEFAULT_PATTERNS_PATH) -> list[dict[str, Any]]:
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


def write_auditvault_ids(
    findings_payload: dict[str, Any],
    output_path: Path = DEFAULT_KNOWLEDGE_PATH,
) -> dict[str, Any]:
    """Emit a flat observable-id JSONL so RSI / auditors can pick slugs.

    This carries only advisory slug → auditvault_refs metadata; it NEVER
    satisfies any submission gate.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for finding in findings_payload.get("findings") or []:
        slug = str(finding.get("primary_protocol_slug") or "").strip()
        if not slug:
            continue
        rows.append(
            {
                "slug": slug,
                "auditvault_id": finding.get("auditvault_id"),
                "severity_score": float(finding.get("severity_score") or 0),
                "template_hints": list(finding.get("template_hints") or []),
                "atlas_axes": list(finding.get("atlas_axes") or []),
                "report_date": finding.get("report_date"),
                "title": finding.get("title", ""),
            }
        )
    with output_path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return {"status": "ok", "path": str(output_path), "row_count": len(rows)}


def auditvault_summary(findings_path: Path = DEFAULT_FINDINGS_PATH) -> dict[str, Any]:
    """Return non-evidence summary metrics for HIPIF scan dashboards."""
    if not findings_path.is_file():
        return {
            "status": "skipped_no_repo",
            "finding_count": 0,
            "protocol_count": 0,
            "slugs": [],
        }
    payload = json.loads(findings_path.read_text())
    findings = payload.get("findings") or []
    slugs: dict[str, dict[str, Any]] = {}
    sector_counts: dict[str, int] = {}
    axis_counts: dict[str, int] = {}
    impact_counts: dict[str, int] = {}
    for finding in findings:
        slug = str(finding.get("primary_protocol_slug") or "").strip()
        if slug:
            entry = slugs.setdefault(
                slug,
                {
                    "slug": slug,
                    "name": finding.get("primary_protocol_name") or slug,
                    "finding_count": 0,
                    "severity_max": 0.0,
                },
            )
            entry["finding_count"] += 1
            entry["severity_max"] = max(
                entry["severity_max"], float(finding.get("severity_score") or 0)
            )
        sector = str(finding.get("sector") or "").strip() or "unknown"
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        for axis in finding.get("atlas_axes") or []:
            axis_counts[axis] = axis_counts.get(axis, 0) + 1
        impact = str(finding.get("impact") or "").strip() or "unknown"
        impact_counts[impact] = impact_counts.get(impact, 0) + 1
    return {
        "status": payload.get("status", "ok"),
        "schema_version": payload.get("schema_version", SCHEMA_VERSION),
        "synced_at": payload.get("synced_at"),
        "finding_count": len(findings),
        "protocol_count": len(slugs),
        "warning_count": int(payload.get("warning_count") or 0),
        "sector_counts": dict(sorted(sector_counts.items(), key=lambda kv: -kv[1])),
        "axis_counts": dict(sorted(axis_counts.items(), key=lambda kv: -kv[1])),
        "impact_counts": dict(sorted(impact_counts.items(), key=lambda kv: -kv[1])),
        "slugs": sorted(slugs.values(), key=lambda s: (-s["severity_max"], -s["finding_count"], s["slug"])),
    }
