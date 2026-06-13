"""Per-file triage scorer (1–5) for bounty target repositories."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_CODE_EXTENSIONS = frozenset(
    {
        ".rs",
        ".sol",
        ".vy",
        ".cairo",
        ".move",
        ".go",
        ".ts",
        ".js",
        ".py",
    }
)

_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "target",
        "dist",
        "build",
        "out",
        "lib",
        "vendor",
        ".venv",
        "__pycache__",
    }
)

# Higher tier first — score = max matched tier.
_TIER_PATTERNS: list[tuple[int, tuple[str, ...]]] = [
    (
        5,
        (
            r"bridge",
            r"wormhole",
            r"cross.?chain",
            r"portal",
            r"messaging",
            r"lockbox",
        ),
    ),
    (
        4,
        (
            r"oracle",
            r"price",
            r"borrow",
            r"lend",
            r"liquidat",
            r"collateral",
            r"reserve",
            r"vault",
            r"cpi",
            r"flash",
        ),
    ),
    (
        3,
        (
            r"auth",
            r"access",
            r"permission",
            r"role",
            r"owner",
            r"admin",
            r"guard",
            r"only_",
            r"signer",
        ),
    ),
    (
        2,
        (
            r"math",
            r"fee",
            r"treasury",
            r"withdraw",
            r"deposit",
            r"swap",
            r"amm",
            r"upgrade",
            r"proxy",
        ),
    ),
]


@dataclass(frozen=True)
class RankedFile:
    path: str
    score: int
    signals: tuple[str, ...]
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "signals": list(self.signals)}


def _score_path(rel_path: str) -> tuple[int, tuple[str, ...]]:
    lowered = rel_path.lower().replace("\\", "/")
    signals: list[str] = []
    best = 1
    for tier, patterns in _TIER_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, lowered):
                signals.append(f"tier{tier}:{pattern}")
                best = max(best, tier)
    return best, tuple(signals)


def iter_code_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    root = repo_root.resolve()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _CODE_EXTENSIONS:
            continue
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        files.append(path)
    return sorted(files)


def rank_files(repo_root: Path) -> list[RankedFile]:
    """Score every code file in repo_root on a 1–5 bug-likelihood scale."""
    ranked: list[RankedFile] = []
    root = repo_root.resolve()
    for path in iter_code_files(root):
        rel = str(path.relative_to(root))
        score, signals = _score_path(rel)
        ranked.append(
            RankedFile(
                path=rel,
                score=score,
                signals=signals,
                size_bytes=path.stat().st_size,
            )
        )
    ranked.sort(key=lambda r: (-r.score, r.path))
    return ranked


def filter_by_min_score(ranked: list[RankedFile], min_score: int) -> list[RankedFile]:
    return [r for r in ranked if r.score >= min_score]


def write_rank_report(
    repo_root: Path,
    output_path: Path,
    *,
    slug: str = "",
    min_score: int = 1,
) -> dict[str, Any]:
    ranked = rank_files(repo_root)
    filtered = filter_by_min_score(ranked, min_score)
    payload = {
        "slug": slug or repo_root.name,
        "repo": str(repo_root.resolve()),
        "min_score": min_score,
        "file_count": len(ranked),
        "above_min": len(filtered),
        "files": [r.to_dict() for r in filtered],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload