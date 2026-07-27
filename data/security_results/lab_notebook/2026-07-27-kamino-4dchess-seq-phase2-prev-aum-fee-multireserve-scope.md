# Lab entry — 2026-07-27 Kamino 4d-chess-sequential Phase 2: prev_aum/fee/multi-reserve/Scope CLMM

## Trigger
Resume from prior Kamino Hard-First wave 2 — execute 4d-chess-sequential on Priority 0 unprivileged surfaces: charge_fees/prev_aum perf fee gaming (PROP-X-030), multi-reserve redeem (PROP-X-032), Scope CLMM composites, and deposit_and_withdraw elevation edges.

## Engine outcome

### PROP-X-030: charge_fees / prev_aum perf fee gaming — HONEST-ZERO
Code traced across all 5 update_prev_aum call sites (deposit, withdraw, redeem_in_kind, charge_fees, give_up_pending_fee). prev_aum is correctly set to `post-operation AUM` after every operation. No path to artificially inflate/deplete AUM then charge asymmetric fees.

- deposit: `prev_aum = current_vault_aum + tokens_deposited`
- withdraw: `prev_aum = current_vault_aum - net_amount_withdrawn`
- redeem_in_kind: `prev_aum = current_vault_aum - actual_liquidity_value`
- charge_fees: `prev_aum = new_aum - new_fees`
- give_up_pending_fee: `prev_aum = total_sum - new_pending_fees`

Same-tx deposit+withdraw calls charge_fees twice — correct (seconds_passed=0 → mgmt=0, prev_aum correctly advanced). withdraw_pending_fees guarded by `vault_admin_authority: Signer`.

**submit_ready=0.** No unprivileged fee extraction path.

### PROP-X-032: Multi-reserve redeem unfairness — HONEST-ZERO
AUM computation (`compute_aum` at vault_state.rs:178) correctly uses `token_available + invested_total - pending_fees`. invested_total = Σ `ctoken_allocation × exchange_rate` across all allocated reserves. Exchange rate is read at refresh time (post-flash-borrow, same slot).

The "unfairness" scenario (one reserve frozen, withdraw from another capturing frozen value) is a **liquidity risk** not a code bug — frozen KLend market prevents ctoken redemption upstream, but AUM correctly reflects current exchange rate × ctoken balance. Immunefi likely OOS as "market condition" not code error.

### Scope CLMM oracle freshness gap — CONFIRMED WEAKNESS, not submit_ready
Analyzed all 3+1 Scope CLMM modules:
- **meteora_dlmm.rs, orca_whirlpool.rs, raydium_ammv3.rs**: Pool `sqrt_price` / `active_id` read at face value. Returned `last_updated_slot` is set to `clock.slot` (the refresh time), **not** from pool observation data. A pool stale for 10k slots appears freshly updated.
- **No TWAP**: All three use instantaneous price only.
- **No sanity bound**: No check against reference (Pyth/Chainlink) price.
- **MultiplicationChain downstream**: Can propagate manipulated CLMM leg → zero/corrupted chain price.
- **CappedMostRecentOf cap_entry stale**: At `capped_most_recent_of.rs:57-61`, cap price loaded with zero freshness validation against `sources_max_age_s`. Cap is upper-bound only (`min()`) so can only underprice (protective against over-borrow, not exploitable for theft).
- **Conditional as kill-switch**: Conditional returning `{value:0}` multiplies to zero in MultiplicationChain — intentional circuit-breaker.

Submit_ready remains 0: this is a design weakness (known CLMM oracle pattern), requires specific KLend market configuration to be exploitable, and attacker needs external pool manipulation.

### Fixed-term rollover — reviewed
Cross-reserve rollover ceiling floor asymmetry produces sub-unit dust (ROLLOVER-ROUNDING-DUST.md). Not Critical. Same-token constraint, borrow-factor match, elevation-group exclusion properly harden.

### Obligation orders — reviewed
Always+Deleverage liquidations skip `min_full_liquidation_value_threshold` → can drain small positions. Requires obligation owner to set the order (rare). Bonus capped at 10% sanity limit.

### Atomic deposit_and_withdraw — reviewed
LTV post-check ensures LTV ≤ initial LTV. Elevation group max-collateral checked. No bypass path.

### SCOPE-ORD-001 — still latent
Max live Scope exp=18. No permissionless path to exp>19 shown without admin FixedPrice misconfig.

## submit_ready
**0** — unchanged. Honest-zero extended across all Priority 0 surfaces.

## Layered coverage summary
| Layer | Surface | Result |
|-------|---------|--------|
| KLend | Flash fee purity | v6.8 honest-zero |
| KLend | Elevation group | honest-zero (wave2) |
| KVault | Flash+vault share | honest-zero (wave1) |
| KVault | Ticket soft reservation | honest-zero (wave2) |
| KVault | Farms CPI | honest-zero (wave2) |
| KVault | charge_fees/prev_aum perf fee | honest-zero (this session) |
| KVault | Multi-reserve redeem unfairness | honest-zero (liquidity risk) |
| Scope | SCOPE-ORD-001 | latent (no exp>19 trigger) |
| Scope | CLMM freshness | confirmed weakness, no submission path |
| Scope | CappedMRO stale cap | confirmed weakness, capped-only (protective) |
| Cross | KLEND-T22-001 | OOS privileged PD |
| Cross | Fixed-term rollover | dust only |
| Cross | Obligation orders | drain requires owner-set Always |

## Next session priorities
1. Revisit T22 PD as hardening-only inventory (write SPEC.md note if not done)
2. If NSS_HIPIF scope re-opens Kamino, target KLend↔Scope path with executable fork (LiteSVM: create exp>19 Scope price → trigger SCOPE-ORD-001 → demonstrate KLend borrow/liq impact)
3. Else rotate to next Hard-First target per data/security_results/day_shift/next.md
