# Lab Notebook — 2026-06-28 — Drift Token-2022 Spot Path Discovery

## Session Summary

Codegraph-first structural analysis of Drift Protocol's Token-2022 transfer fee handling.
All 7 properties (P-TF-Drift-001 through P-TF-Drift-007) confirmed HONEST-ZERO by design.

## Key Findings

### Drift HONEST-ZERO — validate_mint_fee() hard gate

- **Mechanism:** `validate_mint_fee()` at `controller/token.rs:214-227` checks if a
  Token-2022 mint has a non-zero `TransferFeeConfig` extension. If fee != 0, returns
  `ErrorCode::NonZeroTransferFee`.
- **Coverage:** Called in ALL 5 token movement functions:
  1. `send_from_program_vault_with_signature_seeds` (withdrawals) — line 69
  2. `receive` (deposits) — line 120
  3. `mint_tokens` — line 176
  4. `burn_tokens` — line 201
  5. `transfer_checked_with_transfer_hook` — line 241
- **Bypass analysis:** No bypass paths exist. The only `invoke_signed` that does SPL
  token transfers is in `controller/token.rs:274`. All other invokes are system program
  operations (PDA creation) or order fulfillment (OpenBook/Serum/Phoenix).
- **Liquidation:** Purely accounting-based — `controller/liquidation.rs` uses
  `update_spot_balances_and_cumulative_deposits` with no on-chain token transfers.
- **Admin initialization:** `handle_initialize_spot_market` does NOT check for transfer
  fees at init time, but this is irrelevant because `validate_mint_fee` blocks all
  actual transfers.
- **Classification:** Guard-bound honest zero. Drift explicitly blocks Token-2022
  transfer fee tokens at the protocol level.

### Codegraph Intelligence

- **Index:** 15,908 nodes, 88,958 edges across 556 Rust/TypeScript files
- **Key discovery:** `controller/token.rs` is the single point of enforcement
- **Blast radius:** `validate_mint_fee` callers = 5, all in `controller/token.rs`
- **Token-2022 imports:** `controller/token.rs` (TransferFeeConfig),
  `state/spot_market.rs` (spl_token_2022), `instructions/admin.rs` (Token2022, TransferHook),
  `instructions/user.rs` (TokenInterface)

### Cross-Protocol Comparison

| Target | P-TF-001 | P-TF-002 | P-TF-003 | P-TF-004 | P-TF-005 | P-TF-006 | P-TF-007 |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| OnRe redemption | ✓ (H1) | ✓ | n/a | ✓ | ✓ | n/a | ✓ |
| Marginfi deposit/withdraw | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Drift spot deposit** | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) |

## Strategy Results

### Phase 1 Strategies (Primary Subsystem)

| Strategy | Result | Notes |
|----------|--------|-------|
| `drift_spot_deposit_fee_mismatch` | HONEST-ZERO | validate_mint_fee blocks non-zero fee tokens |
| `drift_liquidation_fee_bearing_collateral` | HONEST-ZERO | Liquidation is accounting-only; no on-chain transfers |
| `drift_spot_withdraw_net_amount` | HONEST-ZERO | validate_mint_fee blocks non-zero fee tokens |
| `drift_fee_on_fee_spot_flows` | HONEST-ZERO | No fee tokens can enter the system |

### Phase 2 Strategies (Secondary)

Not executed — Phase 1 honest-zero by design means Phase 2 is also honest-zero.

## Blocks

- None. Analysis complete via codegraph + source review.

## Decisions

1. Drift is guard-bound honest-zero for Token-2022 transfer fee — no validator deployment needed
2. The `validate_mint_fee` pattern is a clean defense: reject at the gate
3. No further campaign work required on Drift for this vector
4. Focus shifts to Marginfi (remaining candidate with pre-fee compensation pattern)

## Next Actions

1. Update SPEC.md with Drift Token-2022 honest-zero verdict
2. Deploy Marginfi .so to local validator and exercise Token-2022 paths
3. Write lab notebook entry for Marginfi analysis
4. Update corpus taxonomy: Token-2022 coverage = 1 confirmed (OnRe) + 1 guard-bound (Drift) + 1 candidate (Marginfi)
