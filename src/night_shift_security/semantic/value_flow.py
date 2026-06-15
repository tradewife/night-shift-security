"""Value-flow graph projection helpers."""

from __future__ import annotations

from typing import Any


def value_flows(semantic_map: dict[str, Any]) -> list[dict[str, Any]]:
    return list((semantic_map.get("graphs") or {}).get("value_flows") or [])
