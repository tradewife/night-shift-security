"""Lightweight Solidity semantic extraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from night_shift_security.semantic.selectors import evm_selector

_FUNCTION_RE = re.compile(
    r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*([^;{]*)",
    re.MULTILINE,
)
_CONTRACT_RE = re.compile(r"\b(?:contract|interface|library)\s+([A-Za-z_][A-Za-z0-9_]*)")
_EVENT_RE = re.compile(r"\bevent\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_MODIFIER_RE = re.compile(r"\bmodifier\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_VISIBILITY = {"external", "public", "internal", "private"}
_TYPE_CLEAN = re.compile(r"\b(?:memory|calldata|storage|payable|indexed)\b")


def _iter_solidity_files(repo: Path) -> list[Path]:
    if not repo.exists():
        return []
    skip_parts = {"test", "tests", "forge-test", "node_modules", "build", "out", "cache"}
    return sorted(
        p
        for p in repo.rglob("*.sol")
        if p.is_file() and not (set(p.relative_to(repo).parts[:-1]) & skip_parts)
    )


def _param_types(params: str) -> list[str]:
    types: list[str] = []
    for raw in [p.strip() for p in params.split(",") if p.strip()]:
        raw = _TYPE_CLEAN.sub("", raw)
        parts = [p for p in raw.split() if p]
        if parts:
            types.append(parts[0])
    return types


def _visibility_and_modifiers(tail: str) -> tuple[str, list[str]]:
    tokens = [t for t in re.split(r"\s+", tail.strip()) if t]
    visibility = ""
    modifiers: list[str] = []
    stop_tokens = {"returns", "virtual", "override"}
    for token in tokens:
        head = token.split("(", 1)[0]
        if head in _VISIBILITY:
            visibility = head
        elif head not in stop_tokens and head not in {"view", "pure", "payable"}:
            modifiers.append(head)
    return visibility, modifiers


def _line_no(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def parse_solidity_repo(repo: Path, *, slug: str) -> dict[str, Any]:
    files_payload: list[dict[str, Any]] = []
    entrypoints: list[dict[str, Any]] = []
    authority_signals: list[dict[str, Any]] = []
    value_flows: list[dict[str, Any]] = []
    oracle_reads: list[dict[str, Any]] = []
    bridge_flows: list[dict[str, Any]] = []

    for path in _iter_solidity_files(repo):
        text = path.read_text(errors="ignore")
        rel = str(path.relative_to(repo))
        contracts = _CONTRACT_RE.findall(text)
        events = _EVENT_RE.findall(text)
        modifiers_defined = _MODIFIER_RE.findall(text)
        lower = text.lower()
        file_signals = {
            "delegatecall": ".delegatecall" in lower,
            "low_level_call": ".call" in lower,
            "token_transfer": any(s in lower for s in (".transfer(", ".transferfrom(", ".safeTransfer".lower())),
            "oracle": any(s in lower for s in ("oracle", "pricefeed", "chainlink", "pyth")),
            "bridge": any(s in lower for s in ("bridge", "message", "emitter", "guardian", "vaa")),
            "upgrade": any(s in lower for s in ("upgrade", "implementation", "proxy", "delegatecall")),
        }
        files_payload.append(
            {
                "path": rel,
                "language": "solidity",
                "contracts": contracts,
                "events": events,
                "modifiers": modifiers_defined,
                "signals": file_signals,
            }
        )

        for match in _FUNCTION_RE.finditer(text):
            name, params, tail = match.groups()
            visibility, modifiers = _visibility_and_modifiers(tail)
            if visibility not in {"external", "public"}:
                continue
            signature = f"{name}({','.join(_param_types(params))})"
            selector = evm_selector(signature)
            entry = {
                "kind": "solidity_function",
                "name": name,
                "signature": signature,
                "selector_or_discriminator": selector["value"],
                "selector_algorithm": selector["algorithm"],
                "file": rel,
                "line": _line_no(text, match.start()),
                "visibility": visibility,
                "modifiers": modifiers,
                "source_ref": {"repo": str(repo), "file": rel, "symbol": name},
                "signals": file_signals,
            }
            entrypoints.append(entry)
            mod_l = " ".join(modifiers).lower()
            if any(k in mod_l or k in name.lower() for k in ("owner", "admin", "guardian", "paus", "upgrade")):
                authority_signals.append(entry)
            if file_signals["token_transfer"] or any(k in name.lower() for k in ("withdraw", "mint", "burn", "release", "deposit")):
                value_flows.append(entry)
            if file_signals["oracle"]:
                oracle_reads.append(entry)
            if file_signals["bridge"]:
                bridge_flows.append(entry)

    return {
        "files": files_payload,
        "entrypoints": entrypoints,
        "authority_signals": authority_signals,
        "value_flows": value_flows,
        "oracle_reads": oracle_reads,
        "bridge_flows": bridge_flows,
        "parser": "solidity_regex_v1",
        "slug": slug,
    }
