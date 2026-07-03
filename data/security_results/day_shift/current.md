# Session plan — current

**Status: active** (2026-07-03, Agglayer Cantina deep-dive)

**Arc:** Agglayer by Polygon — Cantina `3aaad22b-52ee-4bb2-bed2-4be53b0993cc`

**Primary Target Subsystem:** Pessimistic proof verification + `AgglayerManager` + `AgglayerBridge` + `AgglayerGER` + `AgglayerGateway` settlement/root invariants.

**This session (Agglayer R1):** Cloned `agglayer-contracts`, `agglayer`, `lxly-bridge-and-call`. Codegraph + x-ray artifacts in `investigations/2026-07-03-agglayer-cantina/`. Executable round: **58+** Hardhat/Forge/Cargo tests on reviewed core paths — engine-level honest-zero on encoding parity (`e2e-verify-proof`), migration bootstrap (`UpgradeToPP`), `claimMessage` reentrancy, gateway routes, FEP verify. **`submit_ready`: false.**

**Prior arc (OKX session 4):** Sanctum router LST bridge deep-dive complete
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

**Investigation:** `data/security_results/investigations/2026-07-03-agglayer-cantina/`

**Lab notebook:** `data/security_results/lab_notebook/2026-07-03-agglayer-cantina-round5.md`

**Exit:** Persistent loop until NSS `qualifies_for_submission()` + human gate. All 9 invariant classes tested (R5 closure). Honest-zero across all.

**R5 closure (2026-07-03):** 19 attempts, 0 findings. PROP-AGG-003 (overflow) passes via U512 intermediates. PROP-AGG-001 (encoding) confirmed matching via test vector public_values hex. PROP-AGG-004 (migration) analyzed: bootstrap starts from empty state consistent on both sides. H-FEE-001 closed (origin ERC20 uses balance delta). `runbook.md` updated with `CARGO_BUILD_JOBS=1`. Remaining: SP1 bootstrap proof for non-empty exit tree (requires SP1 toolchain). Recommend pivot unless SP1 PC is commissioned.

**R2–R4:** protoc; GlobalIndex 5/5; GER 3/3; runbook R4; H-FEE Test.