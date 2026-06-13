"""Git history security-patch shape miner."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SECURITY_GREP = r"fix|security|audit|patch|vuln|exploit|reentrancy|overflow|auth"
_MAX_COMMITS_DEFAULT = 200

_DIFF_SHAPES: list[tuple[str, re.Pattern[str]]] = [
    ("added_view_modifier", re.compile(r"^\+.*\bview\b", re.MULTILINE)),
    ("added_pure_modifier", re.compile(r"^\+.*\bpure\b", re.MULTILINE)),
    ("added_auth_guard", re.compile(r"^\+.*(onlyOwner|onlyRole|require_auth|has_one|Signer)", re.MULTILINE)),
    ("added_bounds_check", re.compile(r"^\+.*(require!|assert!|checked_add|SafeMath|saturating)", re.MULTILINE)),
    ("added_fee_validation", re.compile(r"^\+.*(fee_recipient|treasury|validate.*fee)", re.MULTILINE | re.IGNORECASE)),
    ("removed_unsafe_cast", re.compile(r"^\-.*as\s+uint", re.MULTILINE)),
]


@dataclass(frozen=True)
class PatchShape:
    commit: str
    subject: str
    shapes: tuple[str, ...]
    files_touched: int

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "shapes": list(self.shapes)}


def _run_git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git failed: {' '.join(args)}")
    return proc.stdout


def list_security_commits(repo: Path, *, max_commits: int = _MAX_COMMITS_DEFAULT) -> list[tuple[str, str]]:
    """Return (hash, subject) for commits matching security-related log grep."""
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"Not a git repository: {repo}")
    log = _run_git(
        repo,
        "log",
        f"--max-count={max_commits}",
        f"--extended-regexp",
        f"--grep={_SECURITY_GREP}",
        "-i",
        "--pretty=format:%H %s",
    )
    commits: list[tuple[str, str]] = []
    for line in log.splitlines():
        line = line.strip()
        if not line:
            continue
        hash_part, _, subject = line.partition(" ")
        commits.append((hash_part, subject))
    return commits


def extract_patch_shapes(diff_text: str) -> list[str]:
    found: list[str] = []
    for name, pattern in _DIFF_SHAPES:
        if pattern.search(diff_text):
            found.append(name)
    return found


def mine_patch_shapes(
    repo: Path,
    *,
    max_commits: int = _MAX_COMMITS_DEFAULT,
) -> list[PatchShape]:
    shapes: list[PatchShape] = []
    for commit, subject in list_security_commits(repo, max_commits=max_commits):
        diff = _run_git(repo, "show", commit, "--pretty=format:", "--unified=0")
        detected = extract_patch_shapes(diff)
        if not detected:
            continue
        files = {line[2:].split("\t")[0] for line in diff.splitlines() if line.startswith("+++ b/")}
        shapes.append(
            PatchShape(
                commit=commit[:12],
                subject=subject,
                shapes=tuple(detected),
                files_touched=len(files),
            )
        )
    return shapes


def find_unpatched_analogues(
    repo: Path,
    shapes: list[PatchShape],
    ranked_paths: list[str],
) -> list[dict[str, Any]]:
    """
    Heuristic: if a patch added auth guards in path X, flag similar paths without 'auth' in name.
    """
    hints: list[dict[str, Any]] = []
    auth_patches = [s for s in shapes if "added_auth_guard" in s.shapes]
    if not auth_patches:
        return hints

    for path in ranked_paths:
        lowered = path.lower()
        if any(token in lowered for token in ("auth", "access", "guard", "permission")):
            continue
        if any(token in lowered for token in ("withdraw", "borrow", "liquidat", "admin")):
            hints.append(
                {
                    "path": path,
                    "reason": "auth_patch_elsewhere_similar_surface",
                    "reference_commits": [p.commit for p in auth_patches[:3]],
                }
            )
    return hints


def write_patch_report(
    repo: Path,
    output_path: Path,
    *,
    slug: str = "",
    max_commits: int = _MAX_COMMITS_DEFAULT,
    ranked_paths: list[str] | None = None,
) -> dict[str, Any]:
    shapes = mine_patch_shapes(repo, max_commits=max_commits)
    analogues = find_unpatched_analogues(repo, shapes, ranked_paths or [])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as fh:
        for shape in shapes:
            fh.write(json.dumps(shape.to_dict()) + "\n")
    summary = {
        "slug": slug or repo.name,
        "repo": str(repo.resolve()),
        "patch_shapes": len(shapes),
        "output": str(output_path),
        "unpatched_analogues": analogues,
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary