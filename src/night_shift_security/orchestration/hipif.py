"""HIPIF — Hierarchical Planning and Information Folding.

Folded context C_k,j for long-horizon agent orchestration:
  c: task description
  H_<k: folded_history (completed subgoals)
  g_k: current_subgoal
  T_k,j: local_history (active subgoal only)
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from night_shift_security.data.program_registry import get_program_by_slug

CHAIN_SUBGOALS: tuple[str, ...] = (
    "bootstrap",
    "scan_all",
    "depth_wormhole",
    "depth_wormhole_bridge",
    "kamino_preflight",
    "depth_kamino",
    "cantina_slates",
    "hunt_rotation",
    "rsi_fold",
    "refine_conditional",
    "coordinator_conditional",
    "journal_fold",
    "gate",
)

_DEFAULT_CONTEXT_PATH = Path("data/security_results/hipif/folded_context.json")
_LOOP_STATE_PATH = Path("data/security_results/loop/state.json")
_SCAN_PATH = Path("data/security_results/bounty_scan/latest.json")
_HINTS_PATH = Path("data/security_results/loop/refinement_hints.json")
_ALERT_PATH = Path("data/security_results/loop/submission_alert.json")
_DAY_SHIFT_PATH = Path("data/security_results/day_shift/current.md")

_KNOWN_CLI_TOKENS = frozenset(
    {
        "scan",
        "bounty",
        "loop",
        "improve",
        "coordinator",
        "hipif",
        "git",
        "pull",
        "nss-write-proposals.py",
        "nss-write-scan-proposals.py",
    }
)

_TAG_REFLECTION = re.compile(r"<reflection>(.*?)</reflection>", re.DOTALL | re.IGNORECASE)
_TAG_COMPLETION = re.compile(r"<completion>\s*(yes|no)\s*</completion>", re.IGNORECASE)
_TAG_SUBGOAL = re.compile(r"<subgoal>\s*([^<]+?)\s*</subgoal>", re.IGNORECASE)
_TAG_ACTION = re.compile(r"<action>\s*([^<]+?)\s*</action>", re.IGNORECASE)
_SLUG_IN_ACTION = re.compile(r"\b([a-z][a-z0-9-]{1,40})\b")
_FILE_IN_ACTION = re.compile(r"[\w./-]+\.(?:json|jsonl|md|sh|py)\b")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LocalStep:
    action: str
    observation: str
    at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocalStep:
        return cls(
            action=str(data.get("action") or ""),
            observation=str(data.get("observation") or ""),
            at=str(data.get("at") or _utc_now()),
        )


@dataclass
class FoldedRecord:
    subgoal_id: str
    outcome_summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    ended_at: str = field(default_factory=_utc_now)
    step_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FoldedRecord:
        return cls(
            subgoal_id=str(data.get("subgoal_id") or ""),
            outcome_summary=str(data.get("outcome_summary") or ""),
            metrics=dict(data.get("metrics") or {}),
            ended_at=str(data.get("ended_at") or _utc_now()),
            step_count=int(data.get("step_count") or 0),
        )

    def compact_line(self) -> str:
        parts = [f"[{self.subgoal_id}]", self.outcome_summary]
        for key in ("fork_reproduced", "solana_reproduced", "findings", "status"):
            if key in self.metrics:
                parts.append(f"{key}={self.metrics[key]}")
        return " ".join(parts)


@dataclass
class FoldedContext:
    task: str
    folded_history: list[FoldedRecord] = field(default_factory=list)
    current_subgoal: str = "bootstrap"
    local_history: list[LocalStep] = field(default_factory=list)
    subgoal_index: int = 0
    chain_status: str = "running"
    version: int = 1
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "task": self.task,
            "folded_history": [r.to_dict() for r in self.folded_history],
            "current_subgoal": self.current_subgoal,
            "local_history": [s.to_dict() for s in self.local_history],
            "subgoal_index": self.subgoal_index,
            "chain_status": self.chain_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FoldedContext:
        return cls(
            version=int(data.get("version") or 1),
            task=str(data.get("task") or ""),
            folded_history=[
                FoldedRecord.from_dict(r) for r in (data.get("folded_history") or [])
            ],
            current_subgoal=str(data.get("current_subgoal") or "bootstrap"),
            local_history=[
                LocalStep.from_dict(s) for s in (data.get("local_history") or [])
            ],
            subgoal_index=int(data.get("subgoal_index") or 0),
            chain_status=str(data.get("chain_status") or "running"),
            created_at=str(data.get("created_at") or _utc_now()),
            updated_at=str(data.get("updated_at") or _utc_now()),
        )


@dataclass
class ParsedTurn:
    reflection: str
    completion: bool | None
    subgoal: str
    action: str
    format_ok: bool
    format_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GroundingResult:
    ok: bool
    missing_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepetitionResult:
    repeat_count: int
    blocked: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_context(path: Path | None = None) -> FoldedContext | None:
    p = path or _DEFAULT_CONTEXT_PATH
    if not p.is_file():
        return None
    return FoldedContext.from_dict(json.loads(p.read_text()))


def save_context(ctx: FoldedContext, path: Path | None = None) -> Path:
    p = path or _DEFAULT_CONTEXT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    ctx.updated_at = _utc_now()
    p.write_text(json.dumps(ctx.to_dict(), indent=2) + "\n")
    return p


def init_context(task: str, path: Path | None = None) -> FoldedContext:
    ctx = FoldedContext(
        task=task.strip(),
        current_subgoal=CHAIN_SUBGOALS[0],
        subgoal_index=0,
        chain_status="running",
    )
    save_context(ctx, path)
    return ctx


def next_subgoal_id(ctx: FoldedContext) -> str | None:
    idx = ctx.subgoal_index + 1
    if idx >= len(CHAIN_SUBGOALS):
        return None
    return CHAIN_SUBGOALS[idx]


def subgoal_action_hint(subgoal_id: str) -> str:
    hints = {
        "bootstrap": "git pull; read lab notebook + day_shift/current.md; hipif read",
        "scan_all": "scan --platform all",
        "depth_wormhole": "NSS_LOOP_DEPTH_SLUG=wormhole bounty loop --iterations 1",
        "depth_wormhole_bridge": "nss-write-wormhole-triage-proposals.py + wormhole_shoestring loop",
        "kamino_preflight": "klend_live_preflight; NSS_KLEND_FIXTURE=0",
        "depth_kamino": "NSS_LOOP_DEPTH_SLUG=kamino bounty loop --iterations 1",
        "cantina_slates": "NSS_HIPIF_CANTINA_SLATES depth passes (pendle,morpho,euler)",
        "hunt_rotation": "fork-ready hunt with NSS_LOOP_DEPTH_SLUG per slug (ignores saturation)",
        "rsi_fold": "improve; read refinement_hints.json + improvement_ledger tail",
        "refine_conditional": "if hints: nss-write-proposals.py then bounty loop --proposals",
        "coordinator_conditional": "if Kamino hints: coordinator plan --top 1 + cycle",
        "journal_fold": "lab-notebook entry; hipif fold",
        "gate": "check submission_alert.json; stop if submit_ready",
    }
    return hints.get(subgoal_id, "")


def parse_agent_turn(text: str) -> ParsedTurn:
    """subgoal_parser: extract structured tags from agent output."""
    errors: list[str] = []
    reflection_m = _TAG_REFLECTION.search(text)
    completion_m = _TAG_COMPLETION.search(text)
    subgoal_m = _TAG_SUBGOAL.search(text)
    action_m = _TAG_ACTION.search(text)

    reflection = (reflection_m.group(1).strip() if reflection_m else "")
    completion: bool | None = None
    if completion_m:
        completion = completion_m.group(1).lower() == "yes"
    subgoal = (subgoal_m.group(1).strip() if subgoal_m else "")
    action = (action_m.group(1).strip() if action_m else "")

    if not reflection_m:
        errors.append("missing <reflection>")
    if not completion_m:
        errors.append("missing <completion>")
    if not action_m and completion is False:
        errors.append("missing <action> when completion=no")

    return ParsedTurn(
        reflection=reflection,
        completion=completion,
        subgoal=subgoal,
        action=action,
        format_ok=len(errors) == 0,
        format_errors=errors,
    )


def _known_slugs() -> set[str]:
    slugs = {s for s in CHAIN_SUBGOALS if s not in ("bootstrap", "gate", "journal_fold")}
    slugs.update({"wormhole", "kamino", "pendle", "morpho", "euler", "raydium", "orca", "marinade"})
    if _LOOP_STATE_PATH.is_file():
        state = json.loads(_LOOP_STATE_PATH.read_text())
        for slug in state.get("saturated_slugs") or []:
            slugs.add(str(slug))
        for run in state.get("runs") or []:
            if run.get("slug"):
                slugs.add(str(run["slug"]))
    return slugs


def grounding_check(
    ctx: FoldedContext,
    subgoal: str,
    action: str,
    *,
    repo_root: Path | None = None,
) -> GroundingResult:
    """Validate subgoal and action refer to objects present in the environment."""
    root = repo_root or Path.cwd()
    missing: list[str] = []

    sg = (subgoal or ctx.current_subgoal).strip().lower()
    if sg and sg not in CHAIN_SUBGOALS:
        missing.append(f"unknown_subgoal:{sg}")

    action_lower = action.lower()
    has_cli = any(tok in action_lower for tok in _KNOWN_CLI_TOKENS)
    if action.strip() and not has_cli:
        missing.append("no_known_cli_verb")

    known = _known_slugs()
    depth_slugs = {"wormhole", "kamino", "pendle", "morpho", "euler", "uniswap"}
    for slug in depth_slugs:
        if slug in action_lower and get_program_by_slug(slug) is None:
            missing.append(f"unknown_program_slug:{slug}")

    if "refinement_hints" in action_lower and not (_HINTS_PATH.is_file() or root.joinpath(_HINTS_PATH).is_file()):
        if sg == "refine_conditional":
            pass  # empty hints is valid skip
        else:
            missing.append("missing:refinement_hints.json")

    if "bounty_scan" in action_lower or "scan --platform" in action_lower:
        if not (_SCAN_PATH.is_file() or root.joinpath(_SCAN_PATH).is_file()):
            if sg != "scan_all":
                missing.append("missing:bounty_scan/latest.json")

    if "submission_alert" in action_lower:
        alert = root / _ALERT_PATH
        if not alert.is_file():
            missing.append("missing:submission_alert.json")

    if "day_shift" in action_lower:
        if not (root / _DAY_SHIFT_PATH).is_file():
            missing.append("missing:day_shift/current.md")

    for path_match in _FILE_IN_ACTION.findall(action):
        if path_match.startswith("data/") or path_match.startswith("hermes/"):
            if not (root / path_match).exists() and sg not in (
                "scan_all",
                "refine_conditional",
                "journal_fold",
            ):
                missing.append(f"missing_file:{path_match}")

    return GroundingResult(ok=len(missing) == 0, missing_refs=missing)


def repetition_monitor(
    local_history: list[LocalStep],
    action: str,
    *,
    observation: str = "",
    threshold: int = 3,
) -> RepetitionResult:
    """Flag when the same action-observation pair repeats >= threshold times."""
    if not action.strip():
        return RepetitionResult(repeat_count=0, blocked=False)

    norm_action = action.strip().lower()
    norm_obs = observation.strip().lower()
    pair_count = 0
    action_only_count = 0

    for step in reversed(local_history):
        step_action = step.action.strip().lower()
        step_obs = step.observation.strip().lower()
        if step_action == norm_action:
            action_only_count += 1
            if norm_obs and step_obs == norm_obs:
                pair_count += 1
            elif not norm_obs:
                pair_count = action_only_count

    count = pair_count if norm_obs else action_only_count
    blocked = count >= threshold
    msg = ""
    if blocked:
        msg = f"repeated action {threshold}+ times: {action[:80]}"
    return RepetitionResult(repeat_count=count, blocked=blocked, message=msg)


def history_folder(
    ctx: FoldedContext,
    subgoal_id: str,
    outcome_summary: str,
    *,
    metrics: dict[str, Any] | None = None,
) -> FoldedContext:
    """Fold completed subgoal local history into compact H_<k record."""
    record = FoldedRecord(
        subgoal_id=subgoal_id,
        outcome_summary=outcome_summary.strip(),
        metrics=dict(metrics or {}),
        step_count=len(ctx.local_history),
    )
    ctx.folded_history.append(record)
    ctx.local_history = []
    if subgoal_id in CHAIN_SUBGOALS:
        ctx.subgoal_index = CHAIN_SUBGOALS.index(subgoal_id) + 1
    else:
        ctx.subgoal_index += 1
    if ctx.subgoal_index >= len(CHAIN_SUBGOALS):
        ctx.current_subgoal = "gate"
        ctx.chain_status = "complete"
    else:
        ctx.current_subgoal = CHAIN_SUBGOALS[ctx.subgoal_index]
    return ctx


def record_step(
    ctx: FoldedContext,
    action: str,
    observation: str,
) -> FoldedContext:
    ctx.local_history.append(LocalStep(action=action, observation=observation))
    return ctx


def fold_current_subgoal(
    ctx: FoldedContext,
    outcome_summary: str,
    *,
    metrics: dict[str, Any] | None = None,
) -> FoldedContext:
    return history_folder(ctx, ctx.current_subgoal, outcome_summary, metrics=metrics)


def chain_complete(ctx: FoldedContext) -> bool:
    return ctx.chain_status in ("complete", "submit_ready") or (
        ctx.current_subgoal == "gate"
        and len(ctx.folded_history) >= len(CHAIN_SUBGOALS) - 1
    )


def submit_ready() -> bool:
    if not _ALERT_PATH.is_file():
        return False
    try:
        alert = json.loads(_ALERT_PATH.read_text())
        return alert.get("status") == "submit_ready"
    except (json.JSONDecodeError, OSError):
        return False


def refinement_hints_present(repo_root: Path | None = None) -> bool:
    root = repo_root or Path.cwd()
    path = root / _HINTS_PATH
    if not path.is_file():
        return False
    try:
        hints = json.loads(path.read_text())
        return bool(hints.get("top") or hints.get("entries") or hints.get("slug"))
    except (json.JSONDecodeError, OSError):
        return False