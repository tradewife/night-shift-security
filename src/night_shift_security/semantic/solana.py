"""Lightweight Solana/Anchor semantic extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from night_shift_security.semantic.selectors import anchor_discriminator

_RUST_FN_RE = re.compile(r"pub\s+fn\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_ACCOUNTS_STRUCT_RE = re.compile(r"#\[derive\(Accounts\)\]\s*pub\s+struct\s+([A-Za-z_][A-Za-z0-9_]*)")


def _line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _iter_files(repo: Path, suffix: str) -> list[Path]:
    if not repo.exists():
        return []
    skip_parts = {"test", "tests", "node_modules", "build", "out"}
    return sorted(
        p
        for p in repo.rglob(f"*{suffix}")
        if p.is_file() and (suffix == ".json" or not (set(p.relative_to(repo).parts[:-1]) & skip_parts))
    )


def _parse_idl(path: Path, repo: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    instructions = payload.get("instructions")
    if not isinstance(instructions, list):
        return None
    rel = str(path.relative_to(repo))
    entrypoints: list[dict[str, Any]] = []
    for ix in instructions:
        if not isinstance(ix, dict):
            continue
        name = str(ix.get("name") or "").strip()
        if not name:
            continue
        accounts = ix.get("accounts") if isinstance(ix.get("accounts"), list) else []
        discriminator = ix.get("discriminator")
        if isinstance(discriminator, list):
            discriminator_hex = "0x" + bytes(int(x) & 0xFF for x in discriminator).hex()
        else:
            discriminator_hex = anchor_discriminator(name)
        entrypoints.append(
            {
                "kind": "solana_instruction",
                "name": name,
                "selector_or_discriminator": discriminator_hex,
                "file": rel,
                "line": 1,
                "accounts": accounts,
                "signers": [a.get("name") for a in accounts if isinstance(a, dict) and a.get("signer")],
                "writable": [a.get("name") for a in accounts if isinstance(a, dict) and a.get("writable")],
                "source_ref": {"repo": str(repo), "file": rel, "symbol": name},
            }
        )
    return {"file": rel, "entrypoints": entrypoints}


def parse_solana_repo(repo: Path, *, slug: str) -> dict[str, Any]:
    files_payload: list[dict[str, Any]] = []
    entrypoints: list[dict[str, Any]] = []
    authority_signals: list[dict[str, Any]] = []
    value_flows: list[dict[str, Any]] = []
    oracle_reads: list[dict[str, Any]] = []

    for path in _iter_files(repo, ".json"):
        parsed = _parse_idl(path, repo)
        if not parsed:
            continue
        files_payload.append({"path": parsed["file"], "language": "anchor_idl"})
        for entry in parsed["entrypoints"]:
            entrypoints.append(entry)
            lower = entry["name"].lower()
            if any(k in lower for k in ("admin", "owner", "authority", "pause", "upgrade")):
                authority_signals.append(entry)
            if any(k in lower for k in ("borrow", "deposit", "withdraw", "liquidat", "mint", "burn")):
                value_flows.append(entry)
            if "oracle" in lower or "price" in lower or "refresh" in lower:
                oracle_reads.append(entry)

    for path in _iter_files(repo, ".rs"):
        text = path.read_text(errors="ignore")
        rel = str(path.relative_to(repo))
        account_structs = _ACCOUNTS_STRUCT_RE.findall(text)
        files_payload.append(
            {
                "path": rel,
                "language": "rust",
                "anchor_accounts": account_structs,
                "signals": {
                    "cpi": "invoke" in text or "CpiContext" in text,
                    "token": "token::" in text or "TokenAccount" in text,
                    "oracle": "oracle" in text.lower() or "price" in text.lower(),
                },
            }
        )
        for match in _RUST_FN_RE.finditer(text):
            name = match.group(1)
            lower = name.lower()
            entry = {
                "kind": "solana_instruction",
                "name": name,
                "selector_or_discriminator": anchor_discriminator(name),
                "file": rel,
                "line": _line_no(text, match.start()),
                "accounts": account_structs,
                "source_ref": {"repo": str(repo), "file": rel, "symbol": name},
            }
            entrypoints.append(entry)
            if any(k in lower for k in ("admin", "owner", "authority", "pause", "upgrade")):
                authority_signals.append(entry)
            if any(k in lower for k in ("borrow", "deposit", "withdraw", "liquidat", "mint", "burn")):
                value_flows.append(entry)
            if "oracle" in lower or "price" in lower or "refresh" in lower:
                oracle_reads.append(entry)

    return {
        "files": files_payload,
        "entrypoints": entrypoints,
        "authority_signals": authority_signals,
        "value_flows": value_flows,
        "oracle_reads": oracle_reads,
        "bridge_flows": [],
        "parser": "solana_anchor_regex_v1",
        "slug": slug,
    }
