"""Bridge graph projection helpers."""

from __future__ import annotations

from typing import Any


def bridge_graph(semantic_map: dict[str, Any]) -> list[dict[str, Any]]:
    return list((semantic_map.get("graphs") or {}).get("bridges") or [])
