# Next session queue

**1inch Smart Contracts: sessions 1–8. Escrow + farming∩hooks + delegation + settlement honest-zero. submit_ready=0.**

> **Cross-target add-on (2026-07-24, closeout 2026-07-25 — v6.60.0):**
> Horizen ZEN Staking session 1 closed: NSS pass complete on Primary Subsystem
> (RewardAccumulator ↔ ZenStaker). 1 minor candidate (FINDING-001) out of scope per
> project's own carveout; `submit_ready=0`.
> **Phase B mandatory re-evaluation 2026-07-27** if Immunefi scope/reward/config deltas appear.
> Otherwise leave Horizen parked at honest-zero.
> Optional Phase 2 expansion: subgraph stub-Deposit owner-poisoning frontend audit
> against `staker-services` `frontend/` (H009 informational approach).
> No further Horizen SC work needed before Phase B unless a new surface opens.

> **Cross-target add-on (2026-07-25 — v6.60.1, Horizen Session 2 round-2 walk):**
> Round-2 4d-chess-sequential on session 1 closeout crossed **27/27** cumulative
> adversarial tests. New durable artifact: orphan donation to **staker** does NOT
> auto-credit anyone (NNEW9) — survived the round-2 sweep, but worth re-checking when
> Phase B introduces real Phase-2 surfaces (e.g. higher-earning-power calculator or
> new reward notifier roles).
> **Final plan:**
> - **Phase B re-evaluation 2026-07-27** (mandatory) — if Immunefi scope/reward or
>   known-issue list changes, open a short delta session; otherwise stay parked.
> - **Optional Phase 2 expansion (low priority):** staker-services frontend
>   + subgraph integration review against `frontend/` — only if Phase B introduces
>   no higher-value surfaces and bandwidth allows.
> - **Primary open track** remains the 1inch Smart Contracts arc.

## Priority 0 — session 8b / 9

1. Full `4d-chess-sequential` on **LOP NativeOrder** (`NativeOrderFactory` / `NativeOrderImpl`).
2. Mainnet fork Settlement + live fill path if RPC.
3. Permit2Proxy makerAssetSuffix assembly.

## Already exhausted (skip re-run)

- Cross-chain escrow (EVM/Solana/Fusion) — sessions 1–5
- Farming ∩ Token-hooks — session 6
- Delegation — session 7
- limit-order-settlement surplus/whitelist/Kyc/priority — session 8 (32/32)

## Priority 1

SDK E2E / Crucible / other 1inch scope expansion.
