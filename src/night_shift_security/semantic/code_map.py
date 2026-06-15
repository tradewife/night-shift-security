"""Repository-level semantic map and artifact writer."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.semantic.candidates import build_candidate_seeds, write_candidates_jsonl
from night_shift_security.semantic.solana import parse_solana_repo
from night_shift_security.semantic.solidity import parse_solidity_repo

PARSER_VERSION = "semantic_recon_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_commit(repo: Path) -> str:
    if not (repo / ".git").exists():
        return ""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _merge_unique(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for entry in entries:
        key = json.dumps(
            {
                "kind": entry.get("kind"),
                "file": entry.get("file"),
                "name": entry.get("name"),
                "line": entry.get("line"),
            },
            sort_keys=True,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def build_semantic_map(slug: str, repo: Path) -> dict[str, Any]:
    solidity = parse_solidity_repo(repo, slug=slug)
    solana = parse_solana_repo(repo, slug=slug)
    files = list(solidity.get("files") or []) + list(solana.get("files") or [])
    entrypoints = _merge_unique(list(solidity.get("entrypoints") or []) + list(solana.get("entrypoints") or []))
    authority = _merge_unique(list(solidity.get("authority_signals") or []) + list(solana.get("authority_signals") or []))
    value = _merge_unique(list(solidity.get("value_flows") or []) + list(solana.get("value_flows") or []))
    oracle = _merge_unique(list(solidity.get("oracle_reads") or []) + list(solana.get("oracle_reads") or []))
    bridge = _merge_unique(list(solidity.get("bridge_flows") or []) + list(solana.get("bridge_flows") or []))

    return {
        "schema_version": 1,
        "parser_version": PARSER_VERSION,
        "generated_at": _utc_now(),
        "slug": slug,
        "repo": str(repo),
        "source_commit": source_commit(repo),
        "files": files,
        "entrypoints": entrypoints,
        "graphs": {
            "authority": authority,
            "value_flows": value,
            "oracles": oracle,
            "bridges": bridge,
        },
        "summary": {
            "files": len(files),
            "entrypoints": len(entrypoints),
            "authority_signals": len(authority),
            "value_flows": len(value),
            "oracle_reads": len(oracle),
            "bridge_flows": len(bridge),
        },
    }


def write_semantic_artifacts(
    slug: str,
    repo: Path,
    out_dir: Path | None = None,
    *,
    kind: str | None = None,
    store_path: Path | None = None,
) -> dict[str, Any]:
    out = out_dir or Path("data/security_results/semantic") / slug
    out.mkdir(parents=True, exist_ok=True)
    semantic_map = build_semantic_map(slug, repo)
    candidates = build_candidate_seeds(semantic_map, target_slug=slug, kind=kind)

    paths = {
        "code_map": out / "code_map.json",
        "entrypoints": out / "entrypoints.json",
        "authority_graph": out / "authority_graph.json",
        "value_flows": out / "value_flows.json",
        "oracle_graph": out / "oracle_graph.json",
        "bridge_graph": out / "bridge_graph.json",
        "candidate_seeds": out / "candidate_seeds.jsonl",
    }
    paths["code_map"].write_text(json.dumps(semantic_map, indent=2, sort_keys=True) + "\n")
    paths["entrypoints"].write_text(json.dumps(semantic_map["entrypoints"], indent=2, sort_keys=True) + "\n")
    paths["authority_graph"].write_text(json.dumps(semantic_map["graphs"]["authority"], indent=2, sort_keys=True) + "\n")
    paths["value_flows"].write_text(json.dumps(semantic_map["graphs"]["value_flows"], indent=2, sort_keys=True) + "\n")
    paths["oracle_graph"].write_text(json.dumps(semantic_map["graphs"]["oracles"], indent=2, sort_keys=True) + "\n")
    paths["bridge_graph"].write_text(json.dumps(semantic_map["graphs"]["bridges"], indent=2, sort_keys=True) + "\n")
    write_candidates_jsonl(candidates, paths["candidate_seeds"])
    store_result = None
    if store_path is not None:
        from night_shift_security.knowledge.concrete_candidates import upsert_candidates

        store_result = upsert_candidates(
            candidates,
            store_path,
            replace_target_slug=slug,
            replace_provenance_source="semantic_recon",
        )

    return {
        "slug": slug,
        "repo": str(repo),
        "summary": semantic_map["summary"],
        "source_commit": semantic_map["source_commit"],
        "paths": {name: str(path) for name, path in paths.items()},
        "candidate_count": len(candidates),
        "candidate_store": store_result,
    }
