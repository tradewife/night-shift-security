# 2026-06-21 — Session 12: v6.8 Ultrafuzz 4-Phase Campaign on Kamino KLend Flash-Loan

**Author:** Orchestrator (Principal On-Chain Forensic Investigator)
**Session:** Twelfth orchestrator session (v6.8.0-proposal-session12 spec)
**Target:** Kamino KLend (`KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD`, Solana, $1.5M Immunefi bounty)
**Outcome:** **Honest-zero at source-review level.** 5 hypotheses traced through fee calculation chain; 3 falsified with high confidence, 2 underspecified (require executable testing). 6th empirical-FNR datum recorded. `submit_ready` remains 0.

---

## Why this session exists

The Ultrafuzz post (Monad Foundation, https://blog.monad.xyz/blog/ultrafuzz) re-read in session 11 established the structural gap: sessions 5-10 ran the wrapper without the engine. Session 11 (v6.7) ran the engine on Marginfi but only the existing cargo-fuzz harness. Session 12 (v6.8) applies the full 4-phase Ultrafuzz workflow (Setup, Properties, Strategies, Review) to Kamino KLend, which has the highest bounty ($1.5M) in our corpus and has never been exercised through an executable flash-loan engine.

The June 10 Raydium exploit ($1.34M via missing LP mint validation in deprecated AMM V3) is the exact vulnerability class the Ultrafuzz methodology would catch. The question: does Kamino KLend have similar validation gaps in its flash-loan path?

## What was built

| File | Change |
|------|--------|
| `sources/kamino/klend/tests/fixtures/klend.so` | NEW -- deployed KLend BPF binary from mainnet via Alchemy RPC |
| `sources/kamino/klend/target/idl/klend.json` | NEW -- fetched IDL from deployed program (8685 lines) |
| `sources/kamino/klend/tests/flash_loan_fuzz.ts` | NEW -- Anchor TS test harness (559 lines, 5 strategies x 3 attempts) |
| `data/security_results/investigations/2026-06-21-v6-8-kamino-ultrafuzz/properties.md` | NEW -- 12 flash-loan invariants + 5 attack hypotheses |
| `data/security_results/investigations/2026-06-21-v6-8-kamino-ultrafuzz/assessment.md` | NEW -- full forensic tracing + quorum adjudication |
| `data/security_results/investigations/2026-06-21-v6-8-kamino-ultrafuzz/summary.json` | NEW -- campaign summary with hypothesis verdicts |
| `hermes/scripts/v6_8_ultrafuzz_orchestrator.py` | NEW -- orchestrator script (212 lines) |
| `SPEC.md` | Bumped to v6.8.0-proposal-session12 |
| `CHANGELOG.md` | v6.8.0 entry |

## Phase 2: Properties (12 invariants)

PROP-001 through PROP-012 covering:
- Flash-loan fee purity (fee is pure fn of amount + referral params)
- Borrow-repay pairing (identical accounts enforced)
- No-CPI-between (stack height + program_id check)
- Multiple-borrow rejection
- Config gate (u64::MAX disables)
- Conservation of value (vault balance check)
- Reserve accounting (total_available_liquidity)
- Rate monotonicity (cumulative_borrow_rate_bsf)
- Obligation health
- Reserve isolation
- Refresh ordering
- Fee independence from reserve state

## Phase 3: Forensic Tracing (5 hypotheses)

### H4: Fee Precision Loss (FALSIFIED, 95% confidence)

The fee calculation chain:
1. `flash_borrow` calls `refresh_reserve(price: None)` -- no oracle price update
2. `flash_repay` calls `calculate_flash_loan_fees(amount, referral_fee_bps, has_referrer)`
3. `calculate_fees` with `FeeCalculation::Exclusive`: `fee = amount * fee_rate`
4. Minimum fee enforced: `fee.max(1u64)`
5. Guard: `if fee >= amount` -> `BorrowTooSmall`

For `flash_loan_fee_sf = 0`, the early return produces `(0, 0)` fees. But this value is admin-writable only via `update_global_config` / `clone_reserve_config`. Flash-loan operations do NOT mutate `reserve.config.fees`.

### H1: Fee Bypass via Reserve State Mutation (FALSIFIED, 95% confidence)

`calculate_flash_loan_fees` reads ONLY:
- `self.flash_loan_fee_sf` (config, immutable during flash-loan)
- `referral_fee_bps` (lending_market, immutable during flash-loan)
- `has_referrer` (account presence)

It does NOT read `cumulative_borrow_rate_bsf`, `borrowed_amount_sf`, `total_available_amount`, or any oracle price. Fee is structurally independent of reserve state.

### H3: Multi-Flash-Loan Bypass (FALSIFIED, 95% confidence)

`flash_borrow_checks_internal` scans forward in the SAME transaction only. Cross-block flash-loans are independent sequential transactions.

### H2: Obligation Health Race (UNDERSPECIFIED, 60% confidence)

Flash-loan path does NOT interact with obligations. Requires executable test: create obligation, flash-borrow same reserve, attempt liquidation in separate transaction.

### H5: Token-2022 Double-Charge (UNDERSPECIFIED, 70% confidence)

SPL Token-2022 transfer fee extension may deduct transfer fee IN ADDITION to flash-loan fee. Requires Token-2022 reserve setup and executable test.

## Phase 4: Quorum Adjudication

| Hypothesis | Classification | Confidence |
|-----------|---------------|-----------|
| H4 | False positive | 95% |
| H1 | False positive | 95% |
| H2 | Underspecified | 60% |
| H3 | False positive | 95% |
| H5 | Underspecified | 70% |

**No production defects found.** `submit_ready = 0`. `pack_count = 0`.

## Empirical-FNR datum (N=6, source review)

| # | Substrate | Frame | Outcome |
|---|-----------|-------|---------|
| 1 | Ethena V1 (EVM) | uint64 truncation | Honest-zero |
| 2 | Marginfi v2 (Solana) | Sentinel-default discovery gap | Honest-zero |
| 3 | Kamino (Solana) | Flash-loan composition (3 frames) | Honest-zero |
| 4 | Drift (Solana) | LP pool constituent arithmetic | Honest-zero |
| 5 | Meteora DLMM (Solana) | 5-frame quorum + Token-2022 | Honest-zero |
| 6 | Kamino KLend (Solana) | Flash-loan fee precision + bypass | Honest-zero |

## What this is NOT

- **Not a `submit_ready` event.** No production defect found.
- **Not an engine-level test.** The test harness was written but `npm install` did not complete; the BPF binary was downloaded and the IDL fetched. Execution deferred to next session.
- **Not an exhaustive fuzz run.** The full 15-run campaign requires `solana-test-validator` with the KLend program deployed and all token accounts initialized. This is deferred.
- **Not a gate mutation.** `qualifies_for_submission()` is unchanged.

## Limitations

1. **npm install stall.** The Kamino klend repo's `package.json` references `@project-serum/anchor: ^0.25.0` which conflicts with `@coral-xyz/anchor` used in the test harness. Resolving this requires either updating the package.json or using a separate workspace.
2. **Toolchain mismatch.** The repo pins Rust 1.74.1 which is not available on this system. `anchor build` cannot produce a fresh BPF binary. The deployed binary from mainnet was used instead.
3. **No flash-loan fuzz harness.** Unlike Marginfi (which ships `programs/marginfi/fuzz/`), Kamino KLend does not ship a cargo-fuzz harness. Building one is a significant engineering effort.

## Next steps

1. **Resolve npm dependency conflict** and run the test harness on `solana-test-validator`
2. **H2 executable test**: obligation + flash-borrow + liquidation race
3. **H5 executable test**: Token-2022 transfer fee interaction
4. **Build cargo-fuzz harness** for Kamino KLend (following the Marginfi `fuzz/` template)
5. **Engine-level N=2**: if harness is built, run libfuzzer on Kamino flash-loan path

— kthxbye.
