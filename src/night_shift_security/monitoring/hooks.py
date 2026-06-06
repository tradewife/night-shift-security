"""Monitoring hooks — emit alerts when high-severity findings are detected."""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from night_shift_security.data.schemas import Finding, Severity

WEBHOOK_ENV_VAR = "NIGHT_SHIFT_WEBHOOK_URL"

_SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def filter_alertable(
    findings: list[Finding],
    min_severity: str = "high",
) -> list[Finding]:
    """Return findings at or above min_severity."""
    threshold = _SEVERITY_RANK.get(Severity(min_severity), 2)
    return [f for f in findings if _SEVERITY_RANK.get(f.severity, 0) >= threshold]


def build_alert_payload(findings: list[Finding], run_meta: dict) -> dict:
    """Build monitoring event payload."""
    alertable = filter_alertable(findings, run_meta.get("min_severity", "high"))
    return {
        "schema_version": "1.0",
        "source": "night-shift-security",
        "event_type": "security_findings_alert",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "run_at": run_meta.get("run_at"),
        "alert_count": len(alertable),
        "total_findings": len(findings),
        "alerts": [
            {
                "finding_id": f.finding_id,
                "template_id": f.template_id,
                "severity": f.severity.value,
                "severity_score": round(f.severity_score, 4),
                "economic_impact_usd": round(f.economic_impact_usd, 2),
                "disclosure_status": f.disclosure_status,
                "rediscovered_exploit_id": f.rediscovered_exploit_id or None,
            }
            for f in alertable
        ],
    }


def resolve_webhook_url(config: dict) -> str:
    """
    Webhook URL resolution order:

    1. config webhook_url (non-empty)
    2. NIGHT_SHIFT_WEBHOOK_URL env var
    3. empty → file-only mode
    """
    return (config.get("webhook_url") or os.environ.get(WEBHOOK_ENV_VAR, "")).strip()


def emit_monitoring_event(
    findings: list[Finding],
    run_meta: dict,
    config: dict,
) -> dict:
    """
    Emit monitoring alerts to configured sinks.

    Default (local/CI): alerts.jsonl only.
    Optional webhook via config or NIGHT_SHIFT_WEBHOOK_URL — never required.
    """
    if not config.get("enabled", True):
        return {"emitted": 0, "sinks": []}

    payload = build_alert_payload(findings, {**run_meta, **config})
    alertable = payload["alerts"]
    if not alertable:
        return {"emitted": 0, "sinks": []}

    sinks: list[str] = []

    webhook = resolve_webhook_url(config)
    if webhook:
        if _post_webhook(webhook, payload):
            sinks.append("webhook")

    alert_file = config.get("alert_file", "data/security_results/alerts.jsonl")
    if alert_file:
        _append_alert_file(Path(alert_file), payload)
        sinks.append("alert_file")

    return {"emitted": len(alertable), "sinks": sinks, "payload": payload}


def _post_webhook(url: str, payload: dict) -> bool:
    body = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _append_alert_file(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(payload, default=str) + "\n")