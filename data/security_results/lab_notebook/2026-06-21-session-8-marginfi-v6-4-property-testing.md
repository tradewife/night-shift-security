# v6.4 Session 8 — Marginfi v2 Source-Grounded Property Testing

**Date:** 2026-06-21
**Spec:** v6.4.0-proposal-session8
**Source:** `sources/marginfi/repo/` (HEAD `4d57e2c`, org renamed mrgnlabs→0dotxyz)
**Outcome:** Honest-zero — no exploitable bug found; 3rd empirical FNR datum

## What was done

### Ultrafuzz decomposition (Step 0)
Fetched and independently decomposed the Ultrafuzz blog post (blog.monad.xyz/blog/ultrafuzz).
Identified 7 leverage points v6.3 missed: engine > wrapper, emergent disjointness, pass@k cumulative,
executable strategy as unit of work, generic + per-target strategies, artifact handoff, 5-judge committee.
Saved decomposition to SPEC.md §0.1.

### Path A resolution (Step 1)
Resolved canonical Marginfi v2 mainnet addresses through multi-source cross-verification:
- Group: `4qp6Fx6tnZkY5Wropq9wUYgtFxXKwE6viZxFHg3rdAG8`
- USDC Bank: `2s37akK2eyBbp8DZgCm7RtsaEz8eJP3Nxd4urLHQv7yB`
- Liquidity Vault: `7jaiZR5Sk8hdYN9MxTpczTcwbWpb5WEoxSANuUwveuat`
Verified via Anchor.toml fixture, on-chain getAccountInfo parsing, Solscan vault authority, transaction ALT expansion.
Updated `marginfi.py` defaults from sentinels to real addresses. Updated `native_harness_status.json`:
marginfi_v2 `scaffolded`→`ready`, ready_count 8→9.

### BPF build (Step 3)
- Installed anchor 0.31.1 via avm
- Fixed corrupted platform-tools (re-downloaded via cargo build-sbf)
- Built marginfi.so and mocks.so as BPF (SBF)
- Rebuilt with `mainnet-beta` feature to match test binary
- Test framework verified: `flashloan_success_1op` passes

### Property enumeration (Step 4)
Wrote `data/security_results/investigations/2026-06-21-v6-4-properties/properties.md` with 6 enumerated invariants:
1. Flash-fee purity (FlashLoan)
2. Conservation of value (Bankruptcy)
3. Oracle freshness during bankruptcy
4. Liquidation oracle consistency
5. Flash loan + rate limiter bypass
6. socialize_loss edge case — zero shares

### Source analysis + test execution (Step 5-6)
Read and analyzed the following source files:
- `flashloan.rs` — CPI guard, health check at end, flag management
- `liquidate_start.rs` — validate_ixes_exclusive, validate_ix_first/last, no signer required
- `liquidate_end.rs` — pre_health > post_health check, seized <= repaid * max_fee
- `handle_bankruptcy.rs` — insurance coverage, socialize_loss, repay(bad_debt)
- `socialize_loss` in bank.rs — proportional loss socialization, zero-share safety
- `check_account_bankrupt` — uses HealthPriceMode::Live (not cached), BANKRUPT_THRESHOLD = $0.10
- `check_account_init_health` — skips during flash loan, uses Live prices at end
- `is_signer_authorized` — blocks account's own authority during receivership
- `withdraw.rs` — health check skipped during receivership, is_signer_authorized with allow_receivership=true
- `accrue_interest` — simple interest model, revenue == fees (verified algebraically)
- `calc_interest_rate_accrual_state_changes` — lending/borrowing rate spread = fees
- Share conversion: `get_asset_shares` (div, truncate), `get_asset_amount` (mul, truncate) — safe direction
- `decrease_balance_internal` — asset/liability boundary handling, BypassBorrowLimit for liquidation
- `SECURITY.md` — known issues and scope clarifications

Ran existing test suites:
- Flash loan tests: 10 passed (10 scenarios)
- Bankruptcy tests: 36 passed (not bankrupt, no debt, fully insured, partially insured, not insured, 3 depositors)
- Deleverage tests: 10 passed (happy path, cannot worsen health, close balances, tokenless, not risk admin, pause)
- Total: 56 tests passed, 0 failed

### Key findings (all non-exploitable)

1. **Flash loan + liquidation composition BLOCKED**: `validate_ixes_exclusive` in `start_liquidation`
   only allows START, END, INIT_LIQUIDATION_RECORD, WITHDRAW, REPAY instructions. Flash loan
   instructions (START_FLASHLOAN, END_FLASHLOAN) and BORROW are NOT in the allowlist.
   Additionally, `validate_not_cpi_by_stack_height` prevents both from being called via CPI.

2. **Self-liquidation via receivership BLOCKED**: `is_signer_authorized` returns
   `marginfi_account.authority != signer` during receivership — the account's own authority
   is explicitly blocked. Even with a proxy keypair, the `pre_health > post_health` check in
   `end_receivership` catches any health deterioration from asset withdrawal.

3. **socialize_loss math CORRECT**: `new_share_value = (total_value - loss) / total_shares`.
   Zero-share edge case handled (total_value <= loss_amount triggers kill_bank, avoiding div-by-zero).

4. **Bankruptcy uses LIVE prices**: `check_account_bankrupt` uses `HealthPriceMode::Live`, not
   cached prices. The `.ok()` on `fetch_unbiased_price_for_bank` only affects cache update, not
   the bankruptcy determination.

5. **Interest accrual accounting CONSISTENT**: Revenue (borrowing - lending spread) == fees
   collected (insurance + group + protocol). Verified algebraically for all utilization rates.

6. **Share conversion rounding SAFE**: Both `get_asset_shares` (division) and `get_asset_amount`
   (multiplication) truncate toward zero in I80F48. Protocol always retains the rounding remainder.
   Error magnitude: 2^-48 per operation — negligible, not exploitable.

7. **Known issues from SECURITY.md**: 15 known issues/scope clarifications documented.
   Most relevant: interest accrual gaps (#11), flash loan rate limits (#4), staked collateral
   pricing (#3) — all explicitly out-of-scope or Info/Low.

## Why no bug was found

The marginfi v2 protocol has multiple defense layers that make it resistant to the attack
vectors examined:

1. **Instruction-level isolation**: `validate_ixes_exclusive` prevents dangerous instruction
   combinations (flash loan + liquidation) in the same transaction.
2. **Health check enforcement**: `pre_health > post_health` in `end_receivership` ensures
   liquidation never worsens account health.
3. **Authority checks**: `is_signer_authorized` blocks self-liquidation during receivership.
4. **Price mode selection**: Live prices for critical decisions (bankruptcy, end-flashloan),
   cached prices only for non-critical comparisons (end-receivership health delta).
5. **Rounding direction**: Truncation toward zero in share conversions — protocol retains dust.
6. **Extensive existing tests**: 471 tests covering deposit, withdraw, borrow, repay, flash loan
   (10 scenarios), bankruptcy (6+ scenarios), deleverage (6+ scenarios), orders (30+ tests).

## Empirical FNR dataset

| # | Target | Approach | Outcome | Date |
|---|--------|----------|---------|------|
| 1 | Ethena V1 | uint64 truncation probe | Honest-zero | 2026-06-20 |
| 2 | Marginfi v2 | novel-vec probe (sentinel defaults) | Honest-zero | 2026-06-20 |
| 3 | Marginfi v2 | Source-grounded property testing (v6.4) | Honest-zero | 2026-06-21 |

This 3rd datum strengthens the audit-saturation framing: a well-audited protocol with
extensive existing tests (471 tests), known issues documentation, and multi-layer defenses
is resistant to property-based testing approaches, even when the tester has full source
access and a working BPF test framework.

## Artifacts produced

- `SPEC.md` v6.4.0-proposal-session8 (§0.1 Ultrafuzz decomposition + 9-step plan)
- `CHANGELOG.md` v6.4 entry
- `sources/marginfi/marginfi_accounts.json` (verified mainnet addresses)
- `src/night_shift_security/native/marginfi.py` (defaults updated)
- `tests/test_native_marginfi.py` (tests adapted)
- `data/security_results/loop/native_harness_status.json` (marginfi_v2 ready)
- `data/security_results/investigations/2026-06-21-v6-4-properties/properties.md`
- `sources/marginfi/repo/target/deploy/marginfi.so` (BPF build)
- `sources/marginfi/repo/target/deploy/mocks.so` (BPF build)
