"""Finding → catalogue exploit resolution (shared by export modules)."""

from __future__ import annotations

from night_shift_security.data.exploit_catalog import get_exploit_catalog
from night_shift_security.data.schemas import ExploitRecord, Finding


def resolve_exploit_id(finding: Finding) -> str:
    """Prefer strict reproduction anchors over fuzzy rediscovery matches."""
    if finding.solana_reproduced or finding.solana_confirmed:
        evidence_id = finding.solana_evidence.get("exploit_id", "")
        if evidence_id:
            return str(evidence_id)
    if finding.fork_reproduced:
        fork_id = finding.fork_evidence.get("exploit_id", "")
        if fork_id:
            return str(fork_id)
    if finding.rediscovered_exploit_id:
        return finding.rediscovered_exploit_id
    evidence_id = finding.solana_evidence.get("exploit_id", "")
    if evidence_id:
        return str(evidence_id)
    if finding.fork_evidence.get("exploit_id"):
        return str(finding.fork_evidence["exploit_id"])
    return ""


def resolve_catalog_record(
    finding: Finding,
    catalog: list[ExploitRecord] | None = None,
) -> ExploitRecord | None:
    exploit_id = resolve_exploit_id(finding)
    if not exploit_id:
        return None
    catalog = catalog or get_exploit_catalog()
    for record in catalog:
        if record.exploit_id == exploit_id:
            return record
    return None