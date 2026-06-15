"""Authority graph projection helpers."""

from __future__ import annotations

from typing import Any


def authority_graph(semantic_map: dict[str, Any]) -> list[dict[str, Any]]:
    return list((semantic_map.get("graphs") or {}).get("authority") or [])
