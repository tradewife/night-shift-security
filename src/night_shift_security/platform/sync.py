"""Sync live Immunefi + Cantina listings into platform intelligence JSON."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.bounty_program import BountyProgram, program_summary
from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS
from night_shift_security.data.immunefi_registry import IMMUNEFI_PROGRAMS, immunefi_to_bounty

CANTINA_API = (
    "https://api.cantina.xyz/api/v0/opportunities?type=bounty&status=live&limit=100"
)
IMMUNEFI_LISTING = "https://immunefi.com/bug-bounty/"

_DEFAULT_OUTPUT = Path("data/security_results/platform")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, *, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "night-shift-security/3.3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _slug_to_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def sync_immunefi_listing(*, html: str | None = None) -> dict[str, Any]:
    """Parse Immunefi bug-bounty listing page for live program slugs."""
    raw = html if html is not None else _http_get(IMMUNEFI_LISTING)
    slugs = sorted(
        {
            m.group(1)
            for m in re.finditer(r"bug-bounty/([a-z0-9][a-z0-9-]+)", raw, re.I)
            if m.group(1) not in ("information", "scope", "resources")
        }
    )
    programs = [
        {
            "slug": slug,
            "name": _slug_to_name(slug),
            "platform": "immunefi",
            "url": f"https://immunefi.com/bug-bounty/{slug}/information/",
            "live": True,
        }
        for slug in slugs
    ]
    return {
        "schema_version": "1.0",
        "source": "immunefi_listing",
        "synced_at": _utc_now(),
        "program_count": len(programs),
        "programs": programs,
    }


def sync_cantina_api(*, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fetch Cantina live bounty opportunities."""
    if payload is None:
        data = json.loads(_http_get(CANTINA_API))
    else:
        data = payload
    items = data.get("items") or []
    programs: list[dict[str, Any]] = []
    for item in items:
        company = item.get("company") or {}
        fee_raw = item.get("submissionFee")
        deposit_usd = 0.0
        if fee_raw is not None:
            try:
                deposit_usd = float(str(fee_raw))
            except ValueError:
                deposit_usd = 0.0
        pot_raw = item.get("totalRewardPot") or "0"
        try:
            max_bounty = int(float(str(pot_raw)))
        except ValueError:
            max_bounty = 0
        programs.append(
            {
                "slug": str(company.get("handle") or item.get("name", "")).lower().replace(" ", "-"),
                "name": item.get("name") or company.get("name") or "",
                "platform": "cantina",
                "cantina_id": item.get("id", ""),
                "url": item.get("url", ""),
                "max_bounty_usd": max_bounty,
                "deposit_usd": deposit_usd,
                "deposit_required": deposit_usd > 0,
                "currency": item.get("currencyCode", "USDC"),
                "status": item.get("status", "live"),
                "live": item.get("status") == "live",
            }
        )
    programs.sort(key=lambda p: p.get("max_bounty_usd", 0), reverse=True)
    return {
        "schema_version": "1.0",
        "source": "cantina_api",
        "synced_at": _utc_now(),
        "program_count": len(programs),
        "payouts_available_usd": data.get("payoutsAvailable"),
        "programs": programs,
    }


def _curated_programs() -> list[BountyProgram]:
    immunefi = [immunefi_to_bounty(p) for p in IMMUNEFI_PROGRAMS if p.live]
    return immunefi + list(CANTINA_PROGRAMS)


def build_scope_registry(
    immunefi_sync: dict[str, Any],
    cantina_sync: dict[str, Any],
) -> dict[str, Any]:
    """Merge synced listings with curated NSS metadata."""
    curated = {p.slug: p for p in _curated_programs()}
    entries: dict[str, dict[str, Any]] = {}

    for row in immunefi_sync.get("programs") or []:
        slug = row["slug"]
        prog = curated.get(slug)
        entries[slug] = {
            "slug": slug,
            "name": prog.name if prog else row.get("name", slug),
            "platform": "immunefi",
            "url": row.get("url", ""),
            "max_bounty_usd": prog.max_bounty_usd if prog else None,
            "templates": list(prog.templates) if prog else [],
            "catalog_analogue": prog.catalog_analogue if prog else "",
            "kyc_required": prog.kyc_required if prog else False,
            "poc_required": prog.poc_required if prog else True,
            "deposit_usd": prog.deposit_usd if prog else 0,
            "deposit_required": prog.deposit_required if prog else False,
            "primacy_of_impact": prog.primacy_of_impact if prog else False,
            "triaged": prog.triaged if prog else False,
            "curated": prog is not None,
            "scope_version": prog.scope_version if prog else None,
        }

    for row in cantina_sync.get("programs") or []:
        slug = row.get("slug") or ""
        if not slug:
            continue
        prog = curated.get(slug)
        deposit = row.get("deposit_usd", 0) or 0
        entries[slug] = {
            "slug": slug,
            "name": prog.name if prog else row.get("name", slug),
            "platform": "cantina",
            "cantina_id": row.get("cantina_id") or (prog.cantina_id if prog else ""),
            "url": row.get("url", ""),
            "max_bounty_usd": row.get("max_bounty_usd") or (prog.max_bounty_usd if prog else 0),
            "templates": list(prog.templates) if prog else [],
            "catalog_analogue": prog.catalog_analogue if prog else "",
            "kyc_required": prog.kyc_required if prog else False,
            "poc_required": prog.poc_required if prog else True,
            "deposit_usd": deposit,
            "deposit_required": bool(row.get("deposit_required") or deposit > 0),
            "primacy_of_impact": prog.primacy_of_impact if prog else False,
            "triaged": prog.triaged if prog else False,
            "curated": prog is not None,
            "scope_version": prog.scope_version if prog else None,
        }

    return {
        "schema_version": "1.0",
        "generated_at": _utc_now(),
        "entry_count": len(entries),
        "curated_count": sum(1 for e in entries.values() if e.get("curated")),
        "entries": entries,
    }


def sync_platforms(
    output_dir: Path | None = None,
    *,
    immunefi_html: str | None = None,
    cantina_payload: dict[str, Any] | None = None,
    skip_network: bool = False,
) -> dict[str, Any]:
    """Write immunefi_programs.json, cantina_programs.json, scope_registry.json."""
    out = output_dir or _DEFAULT_OUTPUT
    out.mkdir(parents=True, exist_ok=True)

    if skip_network:
        immunefi_path = out / "immunefi_programs.json"
        cantina_path = out / "cantina_programs.json"
        immunefi_sync = json.loads(immunefi_path.read_text()) if immunefi_path.is_file() else {
            "programs": [],
            "program_count": 0,
        }
        cantina_sync = json.loads(cantina_path.read_text()) if cantina_path.is_file() else {
            "programs": [],
            "program_count": 0,
        }
    else:
        immunefi_sync = sync_immunefi_listing(html=immunefi_html)
        cantina_sync = sync_cantina_api(payload=cantina_payload)

    immunefi_path = out / "immunefi_programs.json"
    cantina_path = out / "cantina_programs.json"
    scope_path = out / "scope_registry.json"

    immunefi_path.write_text(json.dumps(immunefi_sync, indent=2) + "\n")
    cantina_path.write_text(json.dumps(cantina_sync, indent=2) + "\n")
    scope = build_scope_registry(immunefi_sync, cantina_sync)
    scope_path.write_text(json.dumps(scope, indent=2) + "\n")

    return {
        "output_dir": str(out),
        "immunefi_programs": str(immunefi_path),
        "cantina_programs": str(cantina_path),
        "scope_registry": str(scope_path),
        "immunefi_count": immunefi_sync.get("program_count", 0),
        "cantina_count": cantina_sync.get("program_count", 0),
        "scope_entries": scope.get("entry_count", 0),
    }


def platform_diff(
    output_dir: Path | None = None,
    *,
    immunefi_sync: dict[str, Any] | None = None,
    cantina_sync: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare curated NSS registries against synced live listings."""
    out = output_dir or _DEFAULT_OUTPUT
    if immunefi_sync is None:
        path = out / "immunefi_programs.json"
        immunefi_sync = json.loads(path.read_text()) if path.is_file() else {"programs": []}
    if cantina_sync is None:
        path = out / "cantina_programs.json"
        cantina_sync = json.loads(path.read_text()) if path.is_file() else {"programs": []}

    curated_immunefi = {p.slug for p in IMMUNEFI_PROGRAMS if p.live}
    curated_cantina = {p.slug for p in CANTINA_PROGRAMS if p.live}
    live_immunefi = {p["slug"] for p in immunefi_sync.get("programs") or []}
    live_cantina = {p["slug"] for p in cantina_sync.get("programs") or []}

    return {
        "generated_at": _utc_now(),
        "immunefi": {
            "live_count": len(live_immunefi),
            "curated_count": len(curated_immunefi),
            "coverage_pct": round(100 * len(curated_immunefi & live_immunefi) / max(len(live_immunefi), 1), 2),
            "missing_from_curated": sorted(live_immunefi - curated_immunefi)[:50],
            "stale_curated": sorted(curated_immunefi - live_immunefi),
            "curated_programs": [program_summary(immunefi_to_bounty(p)) for p in IMMUNEFI_PROGRAMS if p.live],
        },
        "cantina": {
            "live_count": len(live_cantina),
            "curated_count": len(curated_cantina),
            "coverage_pct": round(100 * len(curated_cantina & live_cantina) / max(len(live_cantina), 1), 2),
            "missing_from_curated": sorted(live_cantina - curated_cantina)[:50],
            "stale_curated": sorted(curated_cantina - live_cantina),
            "curated_programs": [program_summary(p) for p in CANTINA_PROGRAMS if p.live],
        },
    }