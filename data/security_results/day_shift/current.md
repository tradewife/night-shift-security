# Session plan — current

**Status: active** (2026-07-05, Lombard Finance cross-layer — STRAT-S15/S16/S17 closure)

**Arc:** Lombard Finance Immunefi — Primary Target: Solana `lombard_token_pool` + cross-layer EVM/Solana message and asset flows.

**Workspace:** `data/security_results/investigations/2026-07-03-lombard-cross-layer/` (local-only)
**Repos:** `sources/lombard-finance/repo` and `sources/lombard-finance/evm-smart-contracts`
**Prior:** STRAT-S14 (engine_level_honest_zero on Bascule off-rollback), STRAT-S15 (acceptable-tier, had R3 5->2 silent drop), STRAT-S16 (acceptable-with-gaps, round-level engineering_blocker introduced)

## Session results (v6.51.19)

**R1 — Rollback substrate LOCKED (validator_backed_honest_zero):**
- N5 (sister-program PDA uninit after failed executeOfframp) + N6 (AmountMismatch error at release_or_mint_tokens.rs:212 AFTER mailbox_receive_message CPI) together prove the CPI chain: offramp -> token_pool -> release_or_mint -> mailbox.handle_message -> bridge.gmp_receive -> AmountMismatch -> atomic rollback. N6 stall in v6.51.18 was a false alarm (missing SystemProgram & messageHandledPDA in remaining_accounts). **14/14 ccip.ts tests passing.**

**R2 — Crucible + PDA collision:**
- PROP-CR-008 same_pda_collision_probe (3/3 Rust tests). Crucible R2: 3335 iters, 10/10 actions, 0 crashes.

**R3 — 5-strand expansion (24/24 consortium tests):**
- PROP-CR-007: mid-session valset rotation (3/3) preserved
- PROP-TP-002: destination_caller confusion (3/3) N1 validator proof
- PROP-TP-003: multi-decimal mismatch (5/5) Rust probe
- PROP-MBOX-005/006: mailbox fee race closed engine_level_honest_zero (inbound has no fee)
- PROP-EVM-MBOX-005: deferred (Hardhat fork needed)

**R4:** Zero-survivor forensic log produced.
**R5:** RSI ledger written.
**R6:** Closure adjudication (acceptable-with-gaps).
**R7:** Compliance audit: 27-skill palette documented, delivered_vs_promised.json enforced.

**Classification:** STRAT-S16 closed at acceptable-with-gaps tier. submit_ready: false (unchanged at 0).

## Next actions

- **PROP-EVM-MBOX-005** (cross-layer refund): needs Hardhat fork requires a separate EVM session.
- **27-skill palette** now documented in STRAT-S16 strategy file; maintain per-round ladder going forward.
- delivered_vs_promised.json and round-level engineering_blocker reclassification now standard practice.

**Night Shift handoff:** Lombard cross-layer investigation is at acceptable-with-gaps closure. Do not reopen without new program additions or bounty scope changes. Rotate to next target per next.md.
