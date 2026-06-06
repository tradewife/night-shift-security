"""API query parsing — pagination, filtering, auth."""

import os
from urllib.parse import parse_qs


def parse_query_params(query_string: str) -> dict:
    """Parse URL query string into normalized API params."""
    raw = parse_qs(query_string, keep_blank_values=False)
    return {
        "page": _int_param(raw, "page", default=1, minimum=1),
        "limit": _int_param(raw, "limit", default=50, minimum=1, maximum=200),
        "severity": _str_param(raw, "severity"),
        "template": _str_param(raw, "template"),
        "template_id": _str_param(raw, "template_id") or _str_param(raw, "template"),
        "min_severity_score": _float_param(raw, "min_severity_score"),
        "disclosure_status": _str_param(raw, "disclosure_status"),
        "api_key": _str_param(raw, "api_key"),
    }


def _int_param(raw: dict, key: str, default: int, minimum: int = 0, maximum: int | None = None) -> int:
    values = raw.get(key, [])
    if not values:
        return default
    try:
        value = int(values[0])
    except ValueError:
        return default
    value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    return value


def _float_param(raw: dict, key: str) -> float | None:
    values = raw.get(key, [])
    if not values:
        return None
    try:
        return float(values[0])
    except ValueError:
        return None


def _str_param(raw: dict, key: str) -> str | None:
    values = raw.get(key, [])
    return values[0].strip().lower() if values else None


def check_api_auth(params: dict, header_key: str | None = None) -> bool:
    """
    Optional API key auth.

    If NIGHT_SHIFT_API_KEY is unset, all requests are allowed (dev mode).
    """
    required = os.environ.get("NIGHT_SHIFT_API_KEY", "")
    if not required:
        return True
    provided = params.get("api_key") or header_key or ""
    return provided == required


def filter_findings(findings: list[dict], params: dict) -> list[dict]:
    """Apply query filters to findings list."""
    result = findings

    if params.get("severity"):
        result = [f for f in result if f.get("severity") == params["severity"]]

    if params.get("template_id"):
        result = [f for f in result if f.get("template_id") == params["template_id"]]

    if params.get("disclosure_status"):
        result = [f for f in result if f.get("disclosure_status") == params["disclosure_status"]]

    min_score = params.get("min_severity_score")
    if min_score is not None:
        result = [f for f in result if f.get("severity_score", 0) >= min_score]

    return result


def paginate_findings(findings: list[dict], page: int, limit: int) -> dict:
    """Slice findings and return pagination metadata."""
    total = len(findings)
    start = (page - 1) * limit
    end = start + limit
    page_items = findings[start:end]
    total_pages = max(1, (total + limit - 1) // limit)

    return {
        "findings": page_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }