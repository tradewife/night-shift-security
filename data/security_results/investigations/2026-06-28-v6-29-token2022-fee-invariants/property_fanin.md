# Token-2022 Transfer Fee Property Fan-In (Reusable Template)

These properties are **protocol-agnostic**. Any Solana program that handles
Token-2022 mints in deposit/withdraw/liquidation flows MUST satisfy them.
Applied unchanged to OnRe, MarginFi v2, Drift, and any future Token-2022 target.

| ID | Surface | Invariant | Bug class | Kill criteria | Evidence required |
|----|---------|-----------|-----------|---------------|-------------------|
| `P-TF-001` | `deposit(Token-2022 with fee)` | Collateral or share credit equals **net** amount received by vault, not the **gross** amount the user signed. | accounting, token-extension | If pre-fee amount is recorded, the property fails. | vault delta vs recorded collateral; debug log of pre_fee_amount and post_fee_amount. |
| `P-TF-002` | `withdraw/redeem(Token-2022 with fee)` | User receives correct **net** amount back; the protocol's expected payout equals the **pre-fee-equivalent** of the requested net (rounding-aware). | accounting | If payout skips the fee (pays gross) the bug is OOB-protocol-loss. | user_delta vs oc.amount; log of pre/post fee math. |
| `P-TF-003` | `liquidate(seized_token = Token-2022 with fee)` | Liquidator receives exactly the seized amount approved by the protocol; protocol never records more collateral than it actually seized (after fee). | accounting, liquidation | If seized vault delta = recorded seized, ok. If seized vault delta < recorded, then bad debt accrues silently. | vault delta pre/post, recorded shares. |
| `P-TF-004` | `multi-step: deposit → settle → redeem/withdraw/liquidate` | Protocol does NOT pay the Token-2022 transfer fee twice for the same underlying tokens in one logical operation. | fee-on-fee | Sum of token-program fee deltas == 1× mint.fee × amount. | fee-account balance delta, fee decimals, vault balance delta. |
| `P-TF-005` | `fee-recipient / withdraw-fee handling` | Fee-recipient account is correct; rent never required from user for fee-recipient ATA; no DoS from missing fee-recipient ATA. | liveness, rent | If protocol reverts because fee-recipient ATA does not exist, the property fails. | instruction logs; receiver pubkey. |
| `P-TF-006` | `share/vault token math when underlying has fee` | Mint/redeem of vault shares uses the **net** underlying amount, so 1 share always matches a fixed quantity of **net** underlying. | accounting | If vault total_supply(token) × rate_per_share ≠ sum of net user ATAs, there's drift. | share calculations, vault token balance. |
| `P-TF-007` | `alternative transfer paths (CPI, intermediaries, mixed mints)` | Any path that transfers Token-2022 mints into or out of the protocol accounts for fee exactly once. No PDA-CPI bypass, no intermediary CTA bypass. | CPI, fee-on-fee | Sum of all CPI `transfer_checked` amounts on fee-bearing mints == net amount moved; sum of fee withdrawn by mint fee config ≈ expected. | all CPI logs, intermediary ATAs. |

## Cross-target applicability

| Target | P-001 | P-002 | P-003 | P-004 | P-005 | P-006 | P-007 |
|--------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| OnRe redemption | ✓ (H1 known) | ✓ | n/a | ✓ | ✓ | n/a | ✓ |
| OnRe offer-execution | **blocked by guard** (H1 kill) | – | – | – | – | – | – |
| Marginfi deposit/withdraw | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Marginfi liquidate | – | – | ✓ | – | – | – | – |
| Drift spot deposit | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) | ✓ (blocked) |

## Adoption tested targets

Status of run-state per target is tracked in `runs.jsonl`. Each row contains:

```json
{
  "attempt": N,
  "target": "onre|marginfi|drift",
  "strategy": "<strategy_name>",
  "build": "sbf|host",
  "run_mode": "stateless|stateful|matrix",
  "executed_units": N,
  "actions_observed": true,
  "needs_crucible_minimization": false,
  "panic_count": 0,
  "candidate_class": "production_defect|harness_artifact|engine_level_honest_zero",
  "metrics_path": "evidence/.../metrics.json"
}
```

## Drift verdict (v6.30)

All 7 properties are **HONEST-ZERO by design**. Drift's `validate_mint_fee()` function
(`controller/token.rs:214-227`) is a hard gate that rejects any Token-2022 mint with
a non-zero `TransferFeeConfig` extension, returning `ErrorCode::NonZeroTransferFee`.

This function is called in **every** token movement path:
- `send_from_program_vault_with_signature_seeds` (withdrawals) — line 69
- `receive` (deposits) — line 120
- `mint_tokens` — line 176
- `burn_tokens` — line 201
- `transfer_checked_with_transfer_hook` — line 241

There are no bypass paths. The only `invoke_signed` that does SPL token transfers is
in `controller/token.rs:274`. Liquidation is purely accounting-based (no on-chain token
transfers). Admin initialization (`handle_initialize_spot_market`) does not check for
transfer fees, but this is irrelevant because `validate_mint_fee` blocks all actual
transfers.

**Classification:** Guard-bound honest zero. Drift explicitly blocks Token-2022 transfer
fee tokens at the protocol level. No further campaign work required.

## Notes on strictness

- Rounding direction: We follow protocol's documented rounded behavior. We **never** assert the ceiling-vs-floor polarity *without* protocol doc support — bunker-mode invariant requires evidence of intent.
- New-feature boundaries: Fee-on-fee is **only** a defect when the same logical operation passes through the SPL token-program transfer twice. Phrased this way, we sidestep vacuous "double-trace" issues.
- Pause / kill / OOS guards are checked first; a guard-bound revert is `engine_level_honest_zero`, not a defect.
