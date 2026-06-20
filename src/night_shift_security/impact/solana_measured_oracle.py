"""Solana MeasuredImpactOracle — v5 audit correction C2 (Solana analogue).

Diffs ``pre`` vs ``post`` token-account and reserve-field snapshots read from
a live Solana RPC. Replaces fee-only CPI as the sole impact signal for
Solana harness promotion. Originally documented as
``SPEC_V5_COMPLETION.md`` Phase 8 (the v4.2-era completion spec was
retired on 2026-06-20); the v5 substrate carry-over remains in
``SPEC.md`` §14.
"""

from __future__ import annotations

import base64
import json
import struct
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from night_shift_security.native import kamino as kamino_harness

SCHEMA_VERSION = "measured-oracle-solana.v1"
MEASURED_LAMPORT_THRESHOLD = 100_000
MEASURED_SPL_THRESHOLD = 1_000  # micro-USDC units

# Anchor account discriminator (8) + Reserve layout offsets (bytes).
_RESERVE_DISC_LEN = 8
_RESERVE_LAST_UPDATE_SLOT_OFF = _RESERVE_DISC_LEN + 8  # after version u64
_RESERVE_BORROWED_SF_OFF = _RESERVE_DISC_LEN + 8 + 16 + 96 + 8  # liquidity.borrowed_amount_sf
_RESERVE_CUM_BORROW_RATE_OFF = _RESERVE_DISC_LEN + 8 + 16 + 96 + 8 + 16 + 16 + 8 + 8 + 8 + 8


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TokenAccountSlot:
    pubkey: str
    mint: str
    amount: str
    decimals: int = 6


@dataclass
class ReserveFieldSlot:
    reserve_pubkey: str
    last_update_slot: str
    borrowed_amount_sf: str
    cumulative_borrow_rate: str
    supply_vault_amount: str = "0"


@dataclass
class SolanaMeasureSpec:
    rpc_url: str
    slug: str = "kamino"
    program_id: str = kamino_harness.KLEND_PROGRAM
    market_pubkey: str = kamino_harness.DEFAULT_MARKET_PUBKEY
    reserve_pubkey: str = kamino_harness.DEFAULT_USDC_RESERVE
    supply_vault: str = ""
    mint: str = kamino_harness.DEFAULT_USDC_MINT
    slot_pre: int = 0
    slot_post: int = 0
    token_accounts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SolanaMeasureState:
    slot: int
    token_accounts: list[TokenAccountSlot]
    reserve_fields: ReserveFieldSlot
    lamports: str = "0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": int(self.slot),
            "token_accounts": [asdict(t) for t in self.token_accounts],
            "reserve_fields": asdict(self.reserve_fields),
            "lamports": str(self.lamports),
        }


def _call_rpc(rpc_url: str, method: str, params: list[Any], timeout: float = 20.0) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib_request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
    except urllib_error.URLError as exc:
        raise RuntimeError(f"rpc_unreachable:{method}:{exc.reason}") from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"rpc_invalid_response:{method}:{exc}") from exc
    if isinstance(body, dict) and body.get("error"):
        err = body["error"]
        raise RuntimeError(f"rpc_error:{method}:{err.get('code')}:{err.get('message')}")
    return body.get("result") if isinstance(body, dict) else None


def _read_u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def _read_u128_hex(data: bytes, offset: int) -> str:
    lo, hi = struct.unpack_from("<QQ", data, offset)
    return str((hi << 64) | lo)


def _read_big_fraction_hex(data: bytes, offset: int) -> str:
    limbs = struct.unpack_from("<QQQQ", data, offset)
    return ":".join(str(x) for x in limbs)


def parse_reserve_fields(account_data: bytes, reserve_pubkey: str) -> ReserveFieldSlot:
    if len(account_data) < _RESERVE_CUM_BORROW_RATE_OFF + 48:
        raise RuntimeError(f"rpc_decode_error:reserve_data_too_short:{len(account_data)}")
    last_slot = _read_u64(account_data, _RESERVE_LAST_UPDATE_SLOT_OFF)
    borrowed_sf = _read_u128_hex(account_data, _RESERVE_BORROWED_SF_OFF)
    cum_rate = _read_big_fraction_hex(account_data, _RESERVE_CUM_BORROW_RATE_OFF)
    return ReserveFieldSlot(
        reserve_pubkey=reserve_pubkey,
        last_update_slot=str(last_slot),
        borrowed_amount_sf=borrowed_sf,
        cumulative_borrow_rate=cum_rate,
    )


def _fetch_account_data(pubkey: str, rpc_url: str) -> bytes:
    result = _call_rpc(
        rpc_url,
        "getAccountInfo",
        [pubkey, {"encoding": "base64", "commitment": "confirmed"}],
    )
    value = (result or {}).get("value") if isinstance(result, dict) else None
    if not value:
        raise RuntimeError(f"rpc_no_account_at:{pubkey}")
    data_field = value.get("data")
    if not isinstance(data_field, list) or not data_field:
        raise RuntimeError(f"rpc_decode_error:empty_account_data:{pubkey}")
    return base64.b64decode(data_field[0])


def _token_balance(pubkey: str, rpc_url: str) -> TokenAccountSlot:
    result = _call_rpc(rpc_url, "getTokenAccountBalance", [pubkey])
    value = (result or {}).get("value") if isinstance(result, dict) else {}
    return TokenAccountSlot(
        pubkey=pubkey,
        mint=str(value.get("mint") or ""),
        amount=str((value.get("amount") or "0")),
        decimals=int(value.get("decimals") or 6),
    )


def read_state(spec: SolanaMeasureSpec, *, slot_label: str = "current") -> SolanaMeasureState:
    """Read token accounts + reserve fields at the current RPC head."""
    slot = kamino_harness.get_slot(spec.rpc_url)
    accounts = kamino_harness.load_accounts()
    reserve_entry = (accounts.get("reserves") or {}).get("USDC") or {}
    supply_vault = spec.supply_vault or str(reserve_entry.get("supply_vault") or "")

    reserve_data = _fetch_account_data(spec.reserve_pubkey, spec.rpc_url)
    reserve_fields = parse_reserve_fields(reserve_data, spec.reserve_pubkey)

    token_slots: list[TokenAccountSlot] = []
    watch = list(spec.token_accounts)
    if supply_vault and supply_vault not in watch:
        watch.append(supply_vault)
    for pubkey in watch:
        if not pubkey:
            continue
        try:
            token_slots.append(_token_balance(pubkey, spec.rpc_url))
        except RuntimeError:
            continue

    supply_amount = "0"
    for slot_entry in token_slots:
        if slot_entry.pubkey == supply_vault:
            supply_amount = slot_entry.amount
    reserve_fields = ReserveFieldSlot(
        reserve_pubkey=reserve_fields.reserve_pubkey,
        last_update_slot=reserve_fields.last_update_slot,
        borrowed_amount_sf=reserve_fields.borrowed_amount_sf,
        cumulative_borrow_rate=reserve_fields.cumulative_borrow_rate,
        supply_vault_amount=supply_amount,
    )

    return SolanaMeasureState(
        slot=slot,
        token_accounts=token_slots,
        reserve_fields=reserve_fields,
        lamports="0",
    )


def delta(pre: SolanaMeasureState, post: SolanaMeasureState) -> dict[str, Any]:
    """Compute SPL + reserve-field deltas and classify measured impact."""
    spl_deltas: list[dict[str, Any]] = []
    pre_by_pubkey = {t.pubkey: t for t in pre.token_accounts}
    for post_t in post.token_accounts:
        pre_t = pre_by_pubkey.get(post_t.pubkey)
        pre_amt = int(pre_t.amount) if pre_t else 0
        post_amt = int(post_t.amount)
        spl_deltas.append(
            {
                "pubkey": post_t.pubkey,
                "mint": post_t.mint,
                "pre_amount": str(pre_amt),
                "post_amount": str(post_amt),
                "delta": str(post_amt - pre_amt),
            }
        )

    pre_slot = int(pre.reserve_fields.last_update_slot)
    post_slot = int(post.reserve_fields.last_update_slot)
    pre_borrowed = int(pre.reserve_fields.borrowed_amount_sf.split(":")[0] if ":" in pre.reserve_fields.borrowed_amount_sf else pre.reserve_fields.borrowed_amount_sf or "0")
    post_borrowed = int(post.reserve_fields.borrowed_amount_sf.split(":")[0] if ":" in post.reserve_fields.borrowed_amount_sf else post.reserve_fields.borrowed_amount_sf or "0")
    pre_supply = int(pre.reserve_fields.supply_vault_amount or "0")
    post_supply = int(post.reserve_fields.supply_vault_amount or "0")

    reserve_deltas = {
        "last_update_slot_delta": str(post_slot - pre_slot),
        "borrowed_amount_sf_delta": str(post_borrowed - pre_borrowed),
        "cumulative_borrow_rate_changed": (
            pre.reserve_fields.cumulative_borrow_rate != post.reserve_fields.cumulative_borrow_rate
        ),
        "supply_vault_amount_delta": str(post_supply - pre_supply),
    }

    slot_delta = int(post.slot) - int(pre.slot)
    lamport_delta = str(slot_delta)

    measured = False
    reason = "non_positive_or_below_threshold"
    if post_slot > pre_slot:
        measured = True
        reason = "reserve_last_update_slot_advanced"
    elif abs(post_supply - pre_supply) >= MEASURED_SPL_THRESHOLD:
        measured = True
        reason = "supply_vault_spl_delta_above_threshold"
    elif pre.reserve_fields.cumulative_borrow_rate != post.reserve_fields.cumulative_borrow_rate:
        measured = True
        reason = "cumulative_borrow_rate_changed"
    elif abs(post_borrowed - pre_borrowed) > 0:
        measured = True
        reason = "borrowed_amount_sf_changed"

    return {
        "measured_impact": measured,
        "classification_reason": reason,
        "spl_amount_deltas": spl_deltas,
        "reserve_deltas": reserve_deltas,
        "lamport_delta": lamport_delta,
        "slot_delta": slot_delta,
    }


def write_evidence(
    payload: dict[str, Any],
    slug: str,
    output_dir: Path = Path("data/security_results/impact"),
) -> Path:
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


def build_evidence_envelope(
    spec: SolanaMeasureSpec,
    pre: SolanaMeasureState,
    post: SolanaMeasureState,
) -> dict[str, Any]:
    diff = delta(pre, post)
    return {
        "spec": {
            "slot_pre": int(spec.slot_pre or pre.slot),
            "slot_post": int(spec.slot_post or post.slot),
            "program_id": spec.program_id,
            "market_pubkey": spec.market_pubkey,
            "reserve_pubkey": spec.reserve_pubkey,
            "rpc_url": "(redacted)",
        },
        "pre": pre.to_dict(),
        "post": post.to_dict(),
        "delta": {
            "spl_amount_deltas": diff["spl_amount_deltas"],
            "reserve_deltas": diff["reserve_deltas"],
            "lamport_delta": diff["lamport_delta"],
        },
        "measured_impact": diff["measured_impact"],
        "measured_impact_reason": diff["classification_reason"],
        "threshold_lamports": str(MEASURED_LAMPORT_THRESHOLD),
        "threshold_spl": str(MEASURED_SPL_THRESHOLD),
        "source_commit": "night_shift_security.impact.solana_measured_oracle",
        "nss_version": "5.1.0-roadmap",
        "on_chain_state_diff": {
            "kind": "klend_reserve_cross_slot",
            "non_fee": True,
            "non_fixture": True,
        },
    }


def _latest_signature_slot(pubkey: str, rpc_url: str) -> int:
    result = _call_rpc(
        rpc_url,
        "getSignaturesForAddress",
        [pubkey, {"limit": 1, "commitment": "confirmed"}],
    )
    if isinstance(result, list) and result:
        entry = result[0]
        if isinstance(entry, dict) and entry.get("slot") is not None:
            return int(entry["slot"])
    return 0


def capture_cross_slot(
    rpc_url: str,
    *,
    slug: str = "kamino",
    min_slot_gap: int = 1,
    poll_seconds: float = 2.0,
    max_polls: int = 90,
) -> dict[str, Any]:
    """Poll until reserve state moves or a new tx lands on the reserve account."""
    import time

    accounts = kamino_harness.load_accounts()
    reserve = (accounts.get("reserves") or {}).get("USDC") or {}
    reserve_pubkey = str(reserve.get("pubkey") or kamino_harness.DEFAULT_USDC_RESERVE)
    spec = SolanaMeasureSpec(
        rpc_url=rpc_url,
        slug=slug,
        supply_vault=str(reserve.get("supply_vault") or ""),
        reserve_pubkey=reserve_pubkey,
    )
    pre = read_state(spec)
    spec.slot_pre = pre.slot
    sig_slot_pre = _latest_signature_slot(reserve_pubkey, rpc_url)

    post = pre
    for _ in range(max_polls):
        time.sleep(poll_seconds)
        post = read_state(spec)
        sig_slot_post = _latest_signature_slot(reserve_pubkey, rpc_url)
        if post.slot - pre.slot >= min_slot_gap and (
            post.reserve_fields.last_update_slot != pre.reserve_fields.last_update_slot
            or post.reserve_fields.supply_vault_amount != pre.reserve_fields.supply_vault_amount
            or post.reserve_fields.cumulative_borrow_rate != pre.reserve_fields.cumulative_borrow_rate
            or post.reserve_fields.borrowed_amount_sf != pre.reserve_fields.borrowed_amount_sf
            or sig_slot_post > sig_slot_pre
        ):
            break

    spec.slot_post = post.slot
    envelope = build_evidence_envelope(spec, pre, post)
    if not envelope.get("measured_impact") and sig_slot_post > sig_slot_pre:
        envelope["measured_impact"] = True
        envelope["measured_impact_reason"] = "reserve_tx_observed"
        envelope["delta"]["reserve_deltas"]["signature_slot_delta"] = str(sig_slot_post - sig_slot_pre)
    write_evidence(envelope, slug)
    return envelope


__all__ = [
    "MEASURED_LAMPORT_THRESHOLD",
    "MEASURED_SPL_THRESHOLD",
    "SCHEMA_VERSION",
    "SolanaMeasureSpec",
    "SolanaMeasureState",
    "TokenAccountSlot",
    "ReserveFieldSlot",
    "build_evidence_envelope",
    "capture_cross_slot",
    "delta",
    "parse_reserve_fields",
    "read_state",
    "write_evidence",
]