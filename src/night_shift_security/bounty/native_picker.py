"""v5 native-harness picker — manifest + measured-delta precondition gate.

Background
----------
The v4.2 bounty loop returned the same 9-12 saturated programs every cycle
because ``pick_next_target`` had no notion of "is there actually a native
substrate for this slug?" or "is there any measured-delta evidence?". This
module ships audit corrections **C3** (refuse slugs whose native-harness
status is *missing* or *mapped*) and supports **C4** (measured-delta
escape from catalogue-only saturation).

The corrections flow into ``bounty_loop.pick_next_target`` and
``bounty_loop._maybe_mark_saturated``. The picker is intentionally
deterministic and stdlib-only. It never modifies the gates
(``validation/submission_gates.py`` remains authoritative) — the picker
produces better candidates and the gates stay unchanged.

Anti-patterns this module deliberately avoids
---------------------------------------------
* Silent skip: when a slug has no manifest entry, the picker escalates to
  a typed exception so the operator must see the gap — the audit
  (SYSTEM_AUDIT_2026-06-18 §D5) flagged silent-skip as the root cause of
  the self-saturating loop.
* Fallback widening in tests: helpers accept a ``manifest_path`` so
  tests can build fixtures without touching the production gate.
* Reading ``scope_registry.json`` for the precondition itself: native
  substrate is independent of platform-vs-bounty scope. The full-registry
  walk (audit C5) lives in the caller; this module exposes
  ``list_pickable_slugs`` so the loop can union the curated + live set
  without dup.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from night_shift_security.native import DEFAULT_PATH as DEFAULT_MANIFEST_PATH
from night_shift_security.native import load_manifest

# Valid native-harness lifecycle states, ordered by readiness.
NATIVE_STATE_RANK: dict[str, int] = {
    "ready": 3,
    "paused": 2,
    "harness_built": 2,  # same operational readiness as paused per handover §4.6
    "mapped": 1,
    "missing": 0,
}

# State allowed to clear the precondition gate when no ``ready`` is present.
_NATIVE_GATE_FALLBACK_STATES: frozenset[str] = frozenset({"ready", "harness_built", "paused"})

# States that must NOT be picked (per audit C3 — refusing rather than skipping).
_NATIVE_PICK_REFUSED_STATES: frozenset[str] = frozenset({"missing", "mapped"})


class PickRefused(RuntimeError):
    """Raised when ``pick_next_target`` cannot satisfy the native-harness gate."""


class NativeStatusIncomplete(PickRefused):
    """Raised when every candidate slug has status ``missing`` or ``mapped``."""


class EmptyManifest(PickRefused):
    """Raised when the native-harness manifest does not exist or is empty."""


@dataclass(frozen=True)
class NativePickerEntry:
    slug: str
    status: str
    measured_delta_count: int = 0
    source_commit: str = ""
    contract_address: str = ""

    @property
    def rank(self) -> int:
        return NATIVE_STATE_RANK.get(self.status, 0)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def native_status_of(
    slug: str,
    *,
    manifest_path: Path | str | None = None,
) -> NativePickerEntry | None:
    """Return the manifest entry for a slug, or ``None`` when absent."""
    path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
    manifest = load_manifest(path)
    harnesses = manifest.get("harnesses") or {}
    row = harnesses.get(slug)
    if not isinstance(row, dict):
        return None
    return NativePickerEntry(
        slug=slug,
        status=str(row.get("status") or "missing"),
        measured_delta_count=int(row.get("measured_delta_count") or 0),
        source_commit=str(row.get("source_commit") or ""),
        contract_address=str(row.get("contract_address") or ""),
    )


def filter_native_ready(
    slugs: Iterable[str],
    *,
    manifest_path: Path | str | None = None,
) -> list[str]:
    """Return only slugs whose native-harness status clears the picker gate.

    Status ``ready`` is preferred; ``harness_built`` and ``paused`` are
    accepted as fallback (per handover §4.6 they are operationally equivalent
    and the cron is allowed to depth-pass through them). ``missing`` and
    ``mapped`` are silently dropped here — refusal escalation happens in
    :func:`pick_native_ready_or_raise`.
    """
    out: list[str] = []
    for slug in slugs:
        entry = native_status_of(slug, manifest_path=manifest_path)
        if entry and entry.status in _NATIVE_GATE_FALLBACK_STATES:
            out.append(slug)
    return out


def pick_native_ready_or_raise(
    slugs: Iterable[str],
    *,
    manifest_path: Path | str | None = None,
) -> str:
    """Pick the highest-ranked slug or raise a typed picker exception.

    Preference order is ``ready`` → ``harness_built``/``paused`` →
    refusal (raises). Within a tier we keep the input order so the caller
    (often ranked by bounty priority) governs the tie-break.
    """
    ordered = list(slugs)
    if not ordered:
        raise EmptyManifest("no candidate slugs supplied to native picker")

    path = Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
    manifest = load_manifest(path)
    if not manifest.get("harnesses"):
        raise EmptyManifest(
            f"native-harness manifest empty or missing: {path}",
        )

    ready_first: list[str] = []
    gate_fallback: list[str] = []
    for slug in ordered:
        entry = native_status_of(slug, manifest_path=path)
        if entry is None:
            continue
        if entry.status == "ready":
            ready_first.append(slug)
        elif entry.status in _NATIVE_GATE_FALLBACK_STATES:
            gate_fallback.append(slug)

    if ready_first:
        return ready_first[0]
    if gate_fallback:
        return gate_fallback[0]

    # Surface the refused states for operator visibility.
    refused = sorted(
        {
            native_status_of(slug, manifest_path=path).status
            for slug in ordered
            if native_status_of(slug, manifest_path=path) is not None
        }
    ) or ["unknown"]
    raise NativeStatusIncomplete(
        "no candidate clears the native-harness gate "
        f"(refused states seen: {refused})",
    )


# ---------------------------------------------------------------------------
# Measured-delta detection (audit C4 escape valve)
# ---------------------------------------------------------------------------


def has_measured_delta(
    slug: str,
    *,
    knowledge_path: Path | str | None = None,
    impact_path: Path | str | None = None,
) -> bool:
    """Return ``True`` if a slug has any positive measured-delta evidence recorded.

    Two evidence surfaces are honored:

    1. ``data/security_results/knowledge/concrete_candidates.jsonl`` rows whose
       ``fork_evidence.evidence_kind == "measured_impact_oracle.v1"`` and
       whose delta is non-zero in token-unit or slot0 terms.
    2. ``data/security_results/impact/<slug>_measured_delta.json`` evidence
       files with a non-zero delta in token-unit *or* slot0 terms.

    The matcher is defensive: it never raises on malformed JSONL lines or
    schema drift. Anything unparseable returns ``False``.
    """
    kp = Path(knowledge_path) if knowledge_path is not None else Path(
        "data/security_results/knowledge/concrete_candidates.jsonl",
    )
    ip = Path(impact_path) if impact_path is not None else Path(
        f"data/security_results/impact/{slug}_measured_delta.json",
    )
    slug_l = slug.strip().lower()

    if kp.is_file():
        try:
            with kp.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    row_slug = str(
                        row.get("target_slug")
                        or row.get("slug")
                        or row.get("target_id")
                        or ""
                    ).strip().lower()
                    if row_slug and row_slug != slug_l:
                        continue
                    if _row_has_nonzero_measured_delta(row):
                        return True
        except OSError:
            pass

    if ip.is_file():
        try:
            envelope = json.loads(ip.read_text())
        except (OSError, json.JSONDecodeError):
            envelope = None
        if isinstance(envelope, dict) and _envelope_has_nonzero_measured_delta(envelope):
            return True

    return False


def _row_has_nonzero_measured_delta(row: dict[str, Any]) -> bool:
    ev = row.get("fork_evidence") or {}
    if not isinstance(ev, dict):
        return False
    if ev.get("evidence_kind") != "measured_impact_oracle.v1":
        return False
    token_delta = int(ev.get("token_delta") or 0)
    if token_delta > 0:
        return True
    delta = ev.get("delta") or row.get("on_chain_state_diff") or {}
    if not isinstance(delta, dict):
        return False
    sqrt_raw = str(delta.get("sqrt_price_x96_delta") or "0")
    try:
        if int(sqrt_raw) != 0:
            return True
    except ValueError:
        return False
    for slot in delta.get("pool_slots") or []:
        if not isinstance(slot, dict):
            continue
        try:
            if int(str(slot.get("sqrt_price_x96_delta") or "0")) != 0:
                return True
        except ValueError:
            continue
    return False


def _envelope_has_nonzero_measured_delta(envelope: dict[str, Any]) -> bool:
    delta = envelope.get("delta") or {}
    if not isinstance(delta, dict):
        return False
    for slot_pair in delta.get("pool_slots") or []:
        if not isinstance(slot_pair, dict):
            continue
        try:
            if int(str(slot_pair.get("sqrt_price_x96_delta") or "0")) != 0:
                return True
        except ValueError:
            continue
    for tok in delta.get("tokens") or []:
        if not isinstance(tok, dict):
            continue
        try:
            if int(str(tok.get("delta_raw_units") or "0")) > 0:
                return True
        except ValueError:
            continue
    try:
        if int(str(delta.get("sqrt_price_x96_delta") or "0")) != 0:
            return True
    except ValueError:
        return False
    return False


# ---------------------------------------------------------------------------
# Full live registry walk (audit C5)
# ---------------------------------------------------------------------------


# Slugs whose state shape is incompatible with default Cantina/Immunefi
# curated coverage — used as escape hatch when the scope-registry loader
# is unavailable.
SCOPE_REGISTRY_DEFAULT = Path("data/security_results/platform/scope_registry.json")

# Cap that prevents the picker from drowning downstream gates when the
# full live registry exposes thousands of entries. Audit C5 sets 64 as a
# sane upper bound.
DEFAULT_MAX_REGISTRY_SLUGS = 64


def list_pickable_slugs(
    *,
    curated: Iterable[str] | None = None,
    scope_registry_path: Path | str | None = None,
    max_slugs: int = DEFAULT_MAX_REGISTRY_SLUGS,
) -> list[str]:
    """Return the deduplicated pickable slug union (curated + scope registry).

    The function never raises on missing scope_registry: it silently
    falls back to the curated set so callers can drive both fast and slow
    loops without ad-hoc branching.
    """
    out: list[str] = []
    for slug in curated or ():
        if slug and slug not in out:
            out.append(slug)
    path = (
        Path(scope_registry_path)
        if scope_registry_path is not None
        else SCOPE_REGISTRY_DEFAULT
    )
    if path.is_file():
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            entries = payload.get("entries") or {}
            if isinstance(entries, dict):
                bucket = sorted(entries.keys())
            else:
                bucket = []
            for slug in bucket:
                if slug and slug not in out:
                    out.append(slug)
    return out[: max(max_slugs, 1)]


# ---------------------------------------------------------------------------
# Bonus scoring (audit C5) — bounty-priority * state-multiplier
# ---------------------------------------------------------------------------


def bounty_priority_score(
    slug: str,
    *,
    scope_registry_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
) -> float:
    """Return ``max_bounty_usd * bounty_multiplier`` for ranking.

    The bounty-multiplier mirrors the handover §4.2 priority intent:

    * ``ready``          -> 1.0x (preferred)
    * ``harness_built``  -> 2.0x (carry-over preferred so the legacy
      analogue path doesn't terminate the queue — bonus over ``ready``
      because it costs more to ramp a new harness).
    * ``paused``         -> 2.0x (operationally equal to ``harness_built``).
    * ``mapped``         -> 0.25x (still cheap to bound — preferred over
      fully missing).
    * ``missing``        -> 0.0x (refused — not in candidate pool).
    * no entry at all    -> 0.0x (refused — not in candidate pool).
    """
    entry = native_status_of(slug, manifest_path=manifest_path)
    if entry is None or entry.status == "missing":
        bounty_multiplier = 0.0
    elif entry.status == "ready":
        bounty_multiplier = 1.0
    elif entry.status in ("harness_built", "paused"):
        bounty_multiplier = 2.0
    elif entry.status == "mapped":
        bounty_multiplier = 0.25
    else:
        bounty_multiplier = 0.0

    bounty_usd = _scope_max_bounty(slug, scope_registry_path=scope_registry_path)
    return float(bounty_usd) * bounty_multiplier


def _scope_max_bounty(
    slug: str,
    *,
    scope_registry_path: Path | str | None,
) -> int:
    path = (
        Path(scope_registry_path)
        if scope_registry_path is not None
        else SCOPE_REGISTRY_DEFAULT
    )
    if not path.is_file():
        # Fall back to the curated Cantina registry data when the live
        # scope_registry isn't seeded — the picker must still rank
        # something reasonable.
        try:
            from night_shift_security.data.cantina_registry import CANTINA_PROGRAMS
            from night_shift_security.data.immunefi_registry import (
                IMMUNEFI_PROGRAMS,
                immunefi_to_bounty,
            )
            curated = {p.slug: p.max_bounty_usd for p in CANTINA_PROGRAMS}
            curated.update(
                {p.slug: immunefi_to_bounty(p).max_bounty_usd for p in IMMUNEFI_PROGRAMS}
            )
            return int(curated.get(slug) or 0)
        except Exception:  # noqa: BLE001 — best-effort
            return 0

    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    entries = payload.get("entries") or {}
    row = entries.get(slug)
    if not isinstance(row, dict):
        return 0
    try:
        return int(row.get("max_bounty_usd") or 0)
    except (TypeError, ValueError):
        return 0


def rank_pickable_slugs(
    slugs: Iterable[str],
    *,
    scope_registry_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
) -> list[str]:
    """Return slugs sorted by ``bounty_priority_score`` desc, stable tiebreak."""
    decorated = [
        (
            slug,
            bounty_priority_score(
                slug,
                scope_registry_path=scope_registry_path,
                manifest_path=manifest_path,
            ),
        )
        for slug in slugs
    ]
    decorated.sort(key=lambda pair: (-pair[1], pair[0]))
    return [slug for slug, _ in decorated]


# ---------------------------------------------------------------------------
# Phase 4 rotation — opt-in cold-program float (default OFF)
# ---------------------------------------------------------------------------


def phase4_rotation_enabled() -> bool:
    """Return ``True`` when ``NSS_PHASE4_ROTATION_ENABLED`` is set to a truthy value.

    The env var must be explicitly set to ``1``, ``true``, or ``yes`` (case-
    insensitive) to enable Phase 4 rotation.  Default is **off** so every
    existing test and the production cron behave identically to today.
    """
    return os.environ.get("NSS_PHASE4_ROTATION_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def rotate_target(
    state: dict[str, Any],
    slug: str,
    *,
    now: datetime | None = None,
) -> None:
    """Record when a slug was last touched so the rotation ranker correctly
    floats cold programs to the top."""
    state.setdefault("last_touched", {})[slug] = (
        now or datetime.now(timezone.utc)
    ).isoformat()


def _days_since_last_touched(
    slug: str,
    state: dict[str, Any],
    *,
    now: datetime | None = None,
) -> float:
    """Return days since ``slug`` was last touched, defaulting to a large
    number for never-touched slugs (they should float to the top)."""
    last_touched = (state.get("last_touched") or {}).get(slug)
    if not last_touched:
        return 9999.0
    try:
        touched_dt = datetime.fromisoformat(last_touched)
    except (ValueError, TypeError):
        return 9999.0
    current = now or datetime.now(timezone.utc)
    delta = current - touched_dt
    return max(delta.total_seconds() / 86400.0, 0.0)


def is_saturated_for_rotation(
    slug: str,
    state: dict[str, Any],
    *,
    now: datetime | None = None,
    window_days: int = 14,
) -> bool:
    """Return ``True`` if ``slug`` was last touched within ``window_days``.

    Saturation-for-rotation applies to ``harness_built`` candidates that were
    recently touched — these are de-prioritized during rotation so cold
    programs float above recently-warmed ones.  The function is a guard for
    callers who want strict rotation behaviour; the rotation score already
    handles cold/warm ordering via ``days_since_touched``.

    If the state has been reset between sessions, all candidates look cold
    and the guard is a no-op (``False``).
    """
    state = state or {}
    last_touched = dict(state.get("last_touched") or {}).get(slug)
    if not last_touched:
        return False
    days = _days_since_last_touched(slug, state, now=now)
    return 0.0 <= days <= float(window_days)


def pick_next_target_v6_phase4(
    scan_report: dict[str, Any],
    state: dict[str, Any],
    *,
    cooldown_hours: float = 12.0,
    rotation_window_days: int = 14,
    prefer_full_registry: bool = True,
    manifest_path: Path | str | None = None,
    scope_registry_path: Path | str | None = None,
    raise_on_empty: bool = False,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Phase 4 ranker — cold programs float, all gated by native_harness_status.

    Ranking formula::

        score = (max_bounty_usd * state_multiplier) * max(days_since_touched, 1)

    where ``state_multiplier`` mirrors the existing ``bounty_priority_score``
    weights (``ready``=1.0, ``harness_built``/``paused``=2.0, etc.).

    When the manifest has no ``ready`` harnesses, ``harness_built`` and
    ``paused`` are accepted as fallback (per handover §4.6).

    Saturation guard: ``harness_built`` candidates that were last touched
    within ``rotation_window_days`` are skipped (``is_saturated_for_rotation``)
    so cold programs float above recently-warmed harness_built candidates.
    """
    targets = scan_report.get("targets") or []
    curated_slugs = [
        t["slug"] if isinstance(t, dict) else str(t)
        for t in targets
        if (t.get("slug") if isinstance(t, dict) else t)
    ]
    ranked = rank_pickable_slugs(
        list_pickable_slugs(
            curated=curated_slugs,
            scope_registry_path=scope_registry_path,
        ),
        scope_registry_path=scope_registry_path,
        manifest_path=manifest_path,
    )
    candidates = filter_native_ready(ranked, manifest_path=manifest_path)

    # Saturation guard: skip harness_built candidates that were recently touched.
    candidates = [
        s for s in candidates
        if not is_saturated_for_rotation(
            s, state, now=now, window_days=rotation_window_days
        )
    ]

    if not candidates and raise_on_empty:
        raise NativeStatusIncomplete(
            "Phase 4 rotation: no candidates clear the native-harness gate"
        )
    if not candidates:
        return None

    def _rotation_score(slug: str) -> float:
        entry = native_status_of(slug, manifest_path=manifest_path)
        if entry is None or entry.status == "missing":
            multiplier = 0.0
        elif entry.status == "ready":
            multiplier = 1.0
        elif entry.status in ("harness_built", "paused"):
            multiplier = 2.0
        elif entry.status == "mapped":
            multiplier = 0.25
        else:
            multiplier = 0.0
        bounty_usd = float(_scope_max_bounty(slug, scope_registry_path=scope_registry_path))
        days = _days_since_last_touched(slug, state, now=now)
        # Cold programs float: higher days_since_touched -> higher score.
        return (bounty_usd * multiplier) * max(days, 1.0)

    candidates.sort(key=lambda s: (-_rotation_score(s), s))
    return {"slug": candidates[0], "platform": "cantina"}


__all__ = [
    "DEFAULT_MAX_REGISTRY_SLUGS",
    "EmptyManifest",
    "NATIVE_STATE_RANK",
    "NativePickerEntry",
    "NativeStatusIncomplete",
    "PickRefused",
    "SCOPE_REGISTRY_DEFAULT",
    "bounty_priority_score",
    "filter_native_ready",
    "has_measured_delta",
    "is_saturated_for_rotation",
    "list_pickable_slugs",
    "native_status_of",
    "phase4_rotation_enabled",
    "pick_native_ready_or_raise",
    "pick_next_target_v6_phase4",
    "rank_pickable_slugs",
    "rotate_target",
]
