# Next session queue

**1inch Smart Contracts: sessions 1–8. Escrow + farming∩hooks + delegation + settlement honest-zero. submit_ready=0.**

> **Cross-target closeout (2026-07-25 — v6.60.2, Horizen Session 3):**
> Extended 4d-chess-sequential press closed: ~90+ NSS tests R3–R26, live mainnet pre-flush +
> testnet post-flush, frontend/subgraph/OFT/Binary. **submit_ready=0.** FINDING-001 refined
> (mid-stream dust blends). Investigation + harnesses **keep-local** per AGENTS.md.
>
> **Horizen plan (ordered):**
> 1. **Phase B re-evaluation 2026-07-27 (mandatory)** — Immunefi scope/reward/config deltas only.
> 2. **First-flush live check** — when `data/security_results/investigations/2026-07-24-horizen-zen-staking/watch-first-flush.sh` reports `POST_FIRST_FLUSH`, re-run `NSSRound22FirstFlushFork` / claim-all solvent. MEV/capital share is not a bug.
> 3. **Do not** re-invest in RA core, OFT token, or Identity EP without a new surface.
> 4. Optional low-pri: subgraph sticky-owner mapping note (informational only; not fund theft).
>
> **Primary open track** remains the 1inch Smart Contracts arc below.

> **Prior (v6.60.0 / v6.60.1):** Sessions 1–2 honest-zero; 27 tests through Round-2; NNEW9 orphan-to-staker.

## Priority 0 — session 8b / 9

1. Full `4d-chess-sequential` on **LOP NativeOrder** (`NativeOrderFactory` / `NativeOrderImpl`).
2. Mainnet fork Settlement + live fill path if RPC.
3. Permit2Proxy makerAssetSuffix assembly.

## Already exhausted (skip re-run)

- Cross-chain escrow (EVM/Solana/Fusion) — sessions 1–5
- Farming ∩ Token-hooks — session 6
- Delegation — session 7
- limit-order-settlement surplus/whitelist/Kyc/priority — session 8 (32/32)
- **Horizen RA ↔ ZenStaker primary + Session 3 extended press** — v6.59.0–v6.60.2 (honest-zero)

## Priority 1

SDK E2E / Crucible / other 1inch scope expansion.
