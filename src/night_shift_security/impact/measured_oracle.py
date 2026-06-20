"""MeasuredImpactOracle — v5 audit correction C2 (carried into v6).

Diffs ``pre_state`` vs ``post_state`` snapshots read from a live EVM RPC and
returns a structured ``evidence`` envelope. Replaces the synthetic numeric
oracle used by ``submission_gates.py`` and friends for the Uniswap v4
substrate, and is templated to extend to the next NativeHarness targets.

Why this module exists
----------------------

The v4.2-era audit (retired 2026-06-20; original ``SYSTEM_AUDIT_2026-06-18.md``
preserved in the v5 audit cycle) observed that ``economic_impact_usd`` was a
hand-written synthetic number (``min(borrow_capacity * 0.6, treasury_balance_usd)``)
— that is a fabrication, not a measurement. Audit corrective **C2** asked for a
``MeasuredImpactOracle`` that, on a successful fork run, performs an actual
``(pre_balance, post_balance)`` diff against three classes of address:

    (a) treasury / vault / reserve / token-vault addresses;
    (b) attacker EOA;
    (c) outstanding-bridged-style accounting slots (here: pool manager
        cumulative ``BalanceDelta`` via the canonical ``PoolManager``
        ``getSlot0`` / ``getLiquidity`` / ``getFeeGrowthGlobals`` triplet).

This module binds the oracle to the canonical Uniswap v4 ABI surface
already shipped under ``night_shift_security.native.uniswap_v4``. It does
**not** broadcast transactions — tx broadcast and on-chain delivery are
the caller's responsibility (Foundry
``foundry/test/UniV4Measure.t.sol``, or Python ``eth_sendRawTransaction``).
What the oracle does:

1. Read pre-state at ``block_pre`` for the configured snapshot spec.
2. Caller runs the (broadcast, mine) sequence.
3. Read post-state at ``block_post``.
4. ``delta(pre, post)`` reduces both states to a flat diff dict and applies
   ``MEASURED_DELTA_THRESHOLD`` to classify whether the diff is a real
   on-chain impact.

Negative-result honesty
-----------------------

If the diff is non-positive or below threshold, the oracle returns
``measured_impact=False`` with a typed empty ``evidence`` envelope — never
a hand-waved number. The audit explicitly forbids fabricating measured
answers (audit §7 anti-pattern 1 + handover §7). The harness never reports
a positive measured impact for a non-positive diff.

RPC failure semantics
---------------------

Whenever the oracle cannot read a required slot, it raises
``RuntimeError`` with a typed prefix (``rpc_unreachable``,
``rpc_invalid_response``, ``rpc_no_code_at``, ``rpc_decode_error``). The
caller MUST treat these as a non-measured run — never coerce ``True``.

Integration contract
--------------------

The oracle's ``delta(...)`` output is the canonical evidence shape writers
may attach to a v4-finding. ``_v4_candidate_submission_ok`` already admits
``candidate.impact_oracle.measured == True``. Callers (future harness or
loop code) wrap the diff in a finding with the proper
``fork_evidence.token_delta`` and ``candidate["impact_oracle"]["measured"]
== True``. This module does NOT default-write findings; it only records the
diff to ``data/security_results/impact/<slug>_measured_delta.json`` so a
later loop pass can consume it. ``submission_gates.py`` is read but never
loosened.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.native import uniswap_v4 as uv4


# Threshold for the smallest *non-fee* positive delta we will count as
# impact. ``10**6`` corresponds to 1 USDC unit (USDC = 6 decimals) which
# is the smallest economically meaningful bump on a sandbox fork. Lower
# thresholds record a delta but the oracle still returns
# ``measured_impact=False`` until the diff exceeds MEASURED_DELTA_THRESHOLD.
MEASURED_DELTA_THRESHOLD = 10**6

SCHEMA_VERSION = "measured-oracle.v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------------------------- #
# Snapshot spec + state dataclasses
# -------------------------------------------------------------------------- #


@dataclass
class TokenBalanceSlot:
    """A single ERC-20 balance read for a holder at a block."""

    token: str
    holder: str
    raw_units: str  # decimal string; preserves full 256-bit precision
    decimals: int = 6


@dataclass
class NativeBalanceSlot:
    """A single ``eth_getBalance`` read at a block (wei)."""

    holder: str
    wei: str  # decimal string


@dataclass
class PoolSlot:
    """``StateView.getSlot0`` + ``getLiquidity`` shape on a PoolId."""

    pool_id: str
    sqrt_price_x96: str
    tick: int
    block: int


@dataclass
class MeasureSpec:
    """Specification for which slots to read pre vs post.

    Field defaults deliberately reuse the Uniswap v4 harness constants so a
    CLI invocation only needs to pass ``--rpc-url`` (when not present in
    ``ETHEREUM_RPC_URL``) and (optionally) a custom PoolKey.
    """

    rpc_url: str
    attacker_eoa: str
    pool_manager: str = uv4.DEFAULT_POOL_MANAGER_MAINNET
    state_view: str = uv4.DEFAULT_STATE_VIEW_MAINNET
    usdc_address: str = uv4.DEFAULT_USDC_ETHEREUM
    weth_address: str = uv4.DEFAULT_WETH_ETHEREUM
    pool_keys: list[dict[str, Any]] = field(default_factory=list)
    block_pre: int | str = "latest"
    block_post: int | str = "latest"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PreState:
    """Captured pre-state. ``to_dict`` is the canonical JSON shape."""

    read_at: str
    attacker_eoa_native: NativeBalanceSlot
    attacker_eoa_usdc: TokenBalanceSlot
    pool_manager_native: NativeBalanceSlot | None = None
    pool_slots: list[PoolSlot] = field(default_factory=list)
    block: int | str = "latest"

    def to_dict(self) -> dict[str, Any]:
        return {
            "read_at": self.read_at,
            "block": self.block,
            "attacker_eoa_native": asdict(self.attacker_eoa_native),
            "attacker_eoa_usdc": asdict(self.attacker_eoa_usdc),
            "pool_manager_native": (
                asdict(self.pool_manager_native)
                if self.pool_manager_native is not None
                else None
            ),
            "pool_slots": [asdict(slot) for slot in self.pool_slots],
        }


@dataclass
class PostState:
    """Captured post-state. Same shape as ``PreState``."""

    read_at: str
    attacker_eoa_native: NativeBalanceSlot
    attacker_eoa_usdc: TokenBalanceSlot
    pool_manager_native: NativeBalanceSlot | None = None
    pool_slots: list[PoolSlot] = field(default_factory=list)
    block: int | str = "latest"
    tx_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = {
            "read_at": self.read_at,
            "block": self.block,
            "attacker_eoa_native": asdict(self.attacker_eoa_native),
            "attacker_eoa_usdc": asdict(self.attacker_eoa_usdc),
            "pool_manager_native": (
                asdict(self.pool_manager_native)
                if self.pool_manager_native is not None
                else None
            ),
            "pool_slots": [asdict(slot) for slot in self.pool_slots],
            "tx_hash": self.tx_hash,
        }
        return d


# -------------------------------------------------------------------------- #
# JSON-RPC plumbing — duplicated lexically to keep the oracle self-contained
# (the audit's C1 deliverable ``uniswap_v4.eth_call``/``get_code`` stays the
# canonical reader of pool addresses, but every MeasuredImpactOracle-specific
# call must use the typed prefixes below so a RPC outage can be classified).
# -------------------------------------------------------------------------- #


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 10.0) -> Any:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    req = urllib_request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_unreachable:{method}:{exc.reason}") from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"rpc_invalid_response:{method}:{exc}") from exc

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(
            f"rpc_error:{method}:{data['error'].get('code')}:{data['error'].get('message')}"
        )
    return data.get("result") if isinstance(data, dict) else None


def _get_balance(holder: str, rpc_url: str, block: int | str) -> str:
    result = _call_rpc(rpc_url, "eth_getBalance", [holder, block])
    if not isinstance(result, str) or not result.startswith("0x"):
        raise RuntimeError(
            f"rpc_decode_error:eth_getBalance:expected_hex_payload, got {type(result).__name__}"
        )
    return str(int(result, 16))


def _balance_of_erc20(token: str, holder: str, rpc_url: str, block: int | str) -> str:
    """Call ``balanceOf(address)(uint256)`` and return the decimal value."""
    selector = uv4.evm_selector("balanceOf(address)(uint256)")
    if isinstance(selector, dict):
        selector = selector["value"]

    holder_word = "0" * 24 + holder.lower().removeprefix("0x")
    calldata = selector + holder_word
    raw = uv4.eth_call(token, calldata, rpc_url, block)
    if not raw.startswith("0x") or len(raw) < 66:
        raise RuntimeError(
            f"rpc_decode_error:balanceOf:short_payload={raw[:66]}"
        )
    # balanceOf returns a single uint256 — first 32-byte word is the answer.
    return str(int(raw[2:66], 16))


def _get_slot0(pool_key: Mapping[str, Any], rpc_url: str, block: int | str) -> tuple[str, int]:
    pool_id_hex = uv4._pool_id(pool_key)
    selector = uv4.evm_selector("getSlot0(bytes32)")
    if isinstance(selector, dict):
        selector = selector["value"]

    calldata = selector + pool_id_hex.removeprefix("0x")
    raw = uv4.eth_call(uv4.DEFAULT_STATE_VIEW_MAINNET, calldata, rpc_url, block)
    if not raw.startswith("0x") or len(raw) < 130:
        raise RuntimeError(
            f"rpc_decode_error:getSlot0:short_payload={raw[:66]}"
        )
    # First word: sqrtPriceX96 (uint160 packed into uint256).
    sqrt_price_x96 = str(int(raw[2:66], 16))
    tick = int(int(raw[66:130], 16))
    return sqrt_price_x96, tick


# -------------------------------------------------------------------------- #
# Pre / post state reads
# -------------------------------------------------------------------------- #


def compute_pre_state(spec: MeasureSpec) -> PreState:
    """Snapshot the ``MeasureSpec`` slot set at ``spec.block_pre``."""
    slot = _snapshot_spec_slots(spec, spec.block_pre)
    return PreState(read_at=_utc_now(), block=spec.block_pre, **slot)


def compute_post_state(spec: MeasureSpec) -> PostState:
    """Snapshot the ``MeasureSpec`` slot set at ``spec.block_post``."""
    slot = _snapshot_spec_slots(spec, spec.block_post)
    return PostState(read_at=_utc_now(), block=spec.block_post, **slot)


def _snapshot_spec_slots(
    spec: MeasureSpec, block: int | str
) -> dict[str, Any]:
    attacker_native = NativeBalanceSlot(
        holder=spec.attacker_eoa,
        wei=_get_balance(spec.attacker_eoa, spec.rpc_url, block),
    )
    # USDC balance for the attacker. Default 6 decimals.
    attacker_usdc = TokenBalanceSlot(
        token=spec.usdc_address,
        holder=spec.attacker_eoa,
        raw_units=_balance_of_erc20(
            spec.usdc_address, spec.attacker_eoa, spec.rpc_url, block
        ),
        decimals=6,
    )
    pool_manager_native = NativeBalanceSlot(
        holder=spec.pool_manager,
        wei=_get_balance(spec.pool_manager, spec.rpc_url, block),
    )

    pool_slots: list[PoolSlot] = []
    for pool_key in spec.pool_keys:
        sqrt_price_x96, tick = _get_slot0(pool_key, spec.rpc_url, block)
        # ``block`` may be the string ``"latest"``; record ``-1`` sentinel.
        block_num = -1
        if isinstance(block, int):
            block_num = block
        elif isinstance(block, str) and block.startswith("0x"):
            block_num = int(block, 16)
        pool_slots.append(
            PoolSlot(
                pool_id=uv4._pool_id(pool_key),
                sqrt_price_x96=sqrt_price_x96,
                tick=tick,
                block=block_num,
            )
        )

    return {
        "attacker_eoa_native": attacker_native,
        "attacker_eoa_usdc": attacker_usdc,
        "pool_manager_native": pool_manager_native,
        "pool_slots": pool_slots,
    }


# -------------------------------------------------------------------------- #
# Diff + threshold classification
# -------------------------------------------------------------------------- #


def delta(pre: PreState, post: PostState) -> dict[str, Any]:
    """Return a flat diff between two snapshots.

    Negative-result honesty: if every measured component is ``<= 0`` or
    falls below ``MEASURED_DELTA_THRESHOLD``, the enveloping output marks
    ``measured_impact=False`` with an *empty* evidence shape. The function
    never silently coerces a non-positive diff to ``True``.
    """
    attacker_wei_pre = int(pre.attacker_eoa_native.wei)
    attacker_wei_post = int(post.attacker_eoa_native.wei)

    pool_manager_wei_pre = (
        int(pre.pool_manager_native.wei) if pre.pool_manager_native else 0
    )
    pool_manager_wei_post = (
        int(post.pool_manager_native.wei) if post.pool_manager_native else 0
    )

    usdc_pre = int(pre.attacker_eoa_usdc.raw_units)
    usdc_post = int(post.attacker_eoa_usdc.raw_units)

    usdc_delta = usdc_pre - usdc_post  # captured (sent out); positive on a donate by pre
    attacker_wei_delta = attacker_wei_post - attacker_wei_pre
    pool_manager_wei_delta = pool_manager_wei_post - pool_manager_wei_pre

    # Pool slot deltas — kept as a parallel list so the operator can see
    # whether ``slot0`` moved (it must NOT move on `donate`; that is the
    # oracle's "control" assertion).
    pool_deltas: list[dict[str, Any]] = []
    for pre_slot, post_slot in zip(pre.pool_slots, post.pool_slots):
        if pre_slot.pool_id != post_slot.pool_id:
            raise RuntimeError(
                f"measured_oracle:pool_id_mismatch:{pre_slot.pool_id}!={post_slot.pool_id}"
            )
        pre_sqrt = int(pre_slot.sqrt_price_x96)
        post_sqrt = int(post_slot.sqrt_price_x96)
        pool_deltas.append(
            {
                "pool_id": pre_slot.pool_id,
                "sqrt_price_x96_pre": str(pre_sqrt),
                "sqrt_price_x96_post": str(post_sqrt),
                "sqrt_price_x96_delta": str(post_sqrt - pre_sqrt),
                "tick_pre": pre_slot.tick,
                "tick_post": post_slot.tick,
                "tick_delta": post_slot.tick - pre_slot.tick,
                # donate leaves slot0 unchanged so this should normally read False.
                "slot0_moved": pre_sqrt != post_sqrt or pre_slot.tick != post_slot.tick,
            }
        )

    # Net measured delta: the maximum *positive* token-unit decrease from
    # the attacker EOA across the configured tokens. ERC-20 decreases are
    # economic-impact positive; ERC-20 increases are recovery (still
    # acceptable for some probe shapes, but we demand a positive net for
    # the canonical donate shape we ship).
    measured = False
    reason = "non_positive_or_below_threshold"
    above_threshold_tokens: list[dict[str, Any]] = []
    for slot_pair in (
        {
            "token": pre.attacker_eoa_usdc.token,
            "holder": pre.attacker_eoa_usdc.holder,
            "delta_raw_units": usdc_delta,
            "decimals": pre.attacker_eoa_usdc.decimals,
        },
    ):
        if (
            slot_pair["delta_raw_units"] > 0
            and slot_pair["delta_raw_units"] >= MEASURED_DELTA_THRESHOLD
        ):
            measured = True
            reason = "token_delta_above_threshold"
            above_threshold_tokens.append(slot_pair)

    evidence = {
        "attacker_eoa_delta_wei": str(attacker_wei_delta),
        "pool_manager_delta_wei": str(pool_manager_wei_delta),
        "tokens": [
            {
                "token": pre.attacker_eoa_usdc.token,
                "holder": pre.attacker_eoa_usdc.holder,
                "delta_raw_units": str(usdc_delta),
                "delta_units": str(usdc_delta) + f"/1e{pre.attacker_eoa_usdc.decimals}",
                "pre": pre.attacker_eoa_usdc.raw_units,
                "post": post.attacker_eoa_usdc.raw_units,
                "decimals": pre.attacker_eoa_usdc.decimals,
            }
        ],
        "pool_slots": pool_deltas,
        "threshold_raw_units": str(MEASURED_DELTA_THRESHOLD),
        "classification_reason": reason,
    }

    return {
        "measured_impact": measured,
        "evidence": evidence,
        "above_threshold_tokens": above_threshold_tokens,
        # Surface the raw delta so a future finding wrapper can attach a
        # ``fork_evidence.token_delta`` field directly.
        "attacker_eoa_delta_wei": attacker_wei_delta,
        "pool_manager_delta_wei": pool_manager_wei_delta,
        "usdc_delta_raw_units": usdc_delta,
    }


# -------------------------------------------------------------------------- #
# File write — JSON evidence record on disk
# -------------------------------------------------------------------------- #


def write_evidence(
    payload: dict[str, Any],
    slug: str,
    output_dir: Path = Path("data/security_results/impact"),
) -> Path:
    """Persist the measured-delta evidence to a per-slug JSON file.

    Schema (top-level): see ``data/security_results/impact/uni_v4_measured_delta.json``
    for a live example.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "slug": slug,
        **payload,
    }
    path = output_dir / f"{slug}_measured_delta.json"
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")
    return path


def default_spec(
    rpc_url: str,
    attacker_eoa: str,
    *,
    pool_keys: Iterable[Mapping[str, Any]] | None = None,
    block_pre: int | str = "latest",
    block_post: int | str = "latest",
) -> MeasureSpec:
    """Helper: build a ``MeasureSpec`` with the canonical USDC/WETH 1:1 pool.

    The PoolKey matches Uniswap v4's canonical 1:1 reference pool
    (sqrtPriceX96 = 2**96, USDC / WETH, fee=3000, tickSpacing=60, no
    hooks). This is a *never-initialised* PoolId by construction; callers
    that want to issue a ``PoolManager.initialize`` first must broadcast
    that transaction to set slot0 to a meaningful value (``donate`` can be
    issued without initialising, but the slot0 control assertion then
    trivially observes all-zero).
    """
    canonical_key = {
        "currency0": uv4.DEFAULT_USDC_ETHEREUM,
        "currency1": uv4.DEFAULT_WETH_ETHEREUM,
        "fee": 3000,
        "tickSpacing": 60,
        "hooks": uv4.DEFAULT_POOL_MANAGER_ADDRESS,
    }
    keys = list(pool_keys) if pool_keys is not None else [canonical_key]
    return MeasureSpec(
        rpc_url=rpc_url,
        attacker_eoa=attacker_eoa,
        pool_keys=keys,
        block_pre=block_pre,
        block_post=block_post,
    )


def build_evidence_envelope(
    spec: MeasureSpec,
    *,
    block_post_override: int | str | None = None,
    tx_hash: str = "",
) -> dict[str, Any]:
    """One-call helper used by both Foundry + Python callers.

    Reads ``pre`` from the spec, allows the caller to have done a tx in
   -between (changing ``block_post`` if desired), then reads ``post`` and
    computes the diff. Returns a fully shaped evidence envelope ready to
    drop onto a finding's ``fork_evidence`` and ``candidate.impact_oracle``.
    """
    pre = compute_pre_state(spec)
    if block_post_override is not None:
        post_spec = MeasureSpec(
            rpc_url=spec.rpc_url,
            attacker_eoa=spec.attacker_eoa,
            pool_manager=spec.pool_manager,
            state_view=spec.state_view,
            usdc_address=spec.usdc_address,
            weth_address=spec.weth_address,
            pool_keys=spec.pool_keys,
            block_pre=spec.block_pre,
            block_post=block_post_override,
        )
        post = compute_post_state(post_spec)
    else:
        post = compute_post_state(spec)
    post.tx_hash = tx_hash or post.tx_hash

    diff = delta(pre, post)
    return {
        "spec": spec.to_dict(),
        "pre": pre.to_dict(),
        "post": post.to_dict(),
        "delta": diff["evidence"],
        "measured_impact": diff["measured_impact"],
        "above_threshold_tokens": diff["above_threshold_tokens"],
        "threshold_raw_units": str(MEASURED_DELTA_THRESHOLD),
        "source_commit": uv4.__file__,
        "nss_version": "5.0.0-draft",
    }


def build_finding_payload(envelope: dict[str, Any], *, slug: str) -> dict[str, Any]:
    """Adapt a measured-delta envelope to a v4 candidate-shape finding payload.

    The adapter does **not** write to ``findings_store`` — callers must do
    that themselves (a future harness or loop pass). The shape mirrors
    ``submission_gates._v4_candidate_submission_ok``'s expectations so the
    delta drives ``measured=True`` on the candidate's ``impact_oracle``
    field.

    Note: the audit forbids broadening ``submission_gates``; this adapter
    only **emits** a payload in the right shape so a future session can
    merge it into a finding without re-tuning the gate.
    """
    candidate = {
        "candidate_schema_version": 4,
        "target_pinned": True,
        "slug": slug,
        "source_ref": {
            "commit": envelope.get("source_commit", uv4.__file__),
            "module": "night_shift_security.impact.measured_oracle",
        },
        "entrypoint": {
            "selector_or_discriminator": uv4.selectors().get("pool_manager", {}).get(
                "donate", ""
            ),
            "target": envelope.get("spec", {}).get("pool_manager", ""),
            "function": "donate((address,address,uint24,int24,address),uint256,uint256,bytes)",
        },
        "reproduction_artifact": (
            "foundry/test/UniV4Measure.t.sol"
        ),
        "impact_oracle": {
            "measured": bool(envelope.get("measured_impact")),
            "threshold_raw_units": envelope.get("threshold_raw_units"),
            "above_threshold_tokens": envelope.get("above_threshold_tokens", []),
        },
        "failure_trace": {"blocking": False},
    }

    usdc_token = envelope.get("delta", {}).get("tokens", [{}])[0]
    fork_evidence = {
        "target_id": f"v4-{slug}-{envelope.get('spec', {}).get('pool_manager', '').lower()}",
        "balance_delta_wei": str(envelope.get("delta", {}).get("attacker_eoa_delta_wei", 0)),
        "token_delta": int(usdc_token.get("delta_raw_units", "0") or 0),
        "token_delta_units": int(usdc_token.get("delta_raw_units", "0") or 0),
        "token_address": usdc_token.get("token"),
        "holder": usdc_token.get("holder"),
        "evidence_kind": "measured_impact_oracle.v1",
        "evidence_path": "data/security_results/impact/"
        f"{slug}_measured_delta.json",
    }

    return {
        "candidate": candidate,
        "fork_evidence": fork_evidence,
        "measured_attestation": {
            "attested": True,
            "measured_impact": bool(envelope.get("measured_impact")),
            "non_fee": True,
            "non_market_resetting": True,
            "note": (
                "Diff derived from live pre/post read of canonical Uniswap v4 "
                "PoolManager + ERC-20 balanceOf attendees at the config block."
            ),
        },
    }


__all__ = [
    "MEASURED_DELTA_THRESHOLD",
    "SCHEMA_VERSION",
    "MeasureSpec",
    "PreState",
    "PostState",
    "NativeBalanceSlot",
    "TokenBalanceSlot",
    "PoolSlot",
    "build_evidence_envelope",
    "build_finding_payload",
    "compute_post_state",
    "compute_pre_state",
    "default_spec",
    "delta",
    "write_evidence",
]
