# Session plan — current

**Status: active** (2026-07-02, session 4)

**Arc:** OKX Labs DEX Onchain Bug Bounty (Cantina `00992789-fcd1-4bda-862e-463b0c73faa9`)

**Primary Target Subsystem:** Solana DEX Router core + ToB/TOC/wrap_unwrap
processors + Sanctum router LST bridge
(`okxlabs/Web3-DEX-Router-Solana-V1`).

**This session (4):** Sanctum router LST bridge deep-dive complete
(`adapters/sanctum_router.rs` 1523 lines + `adapters/sanctum.rs` 1538 lines).
Three sub-handlers dispatched at L1234-1278 by wsol mint position:
`withdraw_wsol`, `stake_wsol`, `prefund_swap_via_stake`. `bridge_seed =
(order_id & 0xFFFFFFFF) as u32` (L1427, L1578-1582); bridge_stake PDA
seeds = `['bridge_stake', user.pubkey, bridge_seed]`. New invariant
G-23 documented (cross-program authority check at L1420-1424). New lead
OKX-CORE-019 added: Sanctum router bridge_stake PDA uniqueness delegated
to Sanctum Router (cross-program trust assumption). `okx_bridge_program`
constant (constants.rs:119-129) is dead code.

**Previous sessions (1-3):** Audit PDF discovered
(13-page internal OKX Web3 Audit Team 2024-05-10, 4 findings all Fixed
in commit `a20505a`). V3 surface un-audited. Audit's specific bug class
(if/else if destination validation bypass) searched in V3 paths — no
analogues found. 48 invariants verified (G-1..G-23 + I/X/E). 2 leads
closed (MOONIT-AUTH false-positive, OKX-CORE-011 Token-2022 dead code).
2 reclassified (OKX-CORE-007/012 rent top-up over-delivers).

**Investigation:** `data/security_results/investigations/2026-07-02-okx-dex-solana-router/`

**Lab notebook:** `data/security_results/lab_notebook/2026-07-02-okx-dex-solana-router-session-{1,2,3,4}.md`

**Exit:** `submit_ready` via NSS gates OR evidence-backed honest-zero on core after persistent loops.

**Next focus:** Bankrun TS harness for OKX-CORE-017 (transfer_sol_fee rent top-up) to verify the off-chain log under-report claim. OKX-CORE-019 (Sanctum bridge PDA uniqueness) is cross-program and would require Sanctum Router source/IDL access to verify.