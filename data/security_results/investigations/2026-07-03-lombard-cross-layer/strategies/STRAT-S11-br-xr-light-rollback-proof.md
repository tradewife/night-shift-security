# STRAT-S11 — BR-XR-LIGHT Validator Rollback Proof

## Round metadata

| Field | Value |
|------|-------|
| Round | v6.51.12 |
| Lead | `BR-XR-LIGHT`, `SIG-XR-001-ROLLBACK` |
| Skill chain | `operator-recon` → `codegraph-x-ray` → `ultrafuzz-discovery` → `agentic-strategy-generation` → `operator-triage` |
| Evidence | `evidence/rollback-br-xr-light-validator-rerun.log` |

## Goal

Replay the R3/N4 rollback assertion in a real Anchor validator run:

`mailbox.handle_message` writes `Handled` before recipient CPI →
`release_or_mint_tokens` reverts downstream →
Solana transaction atomicity must roll back the mailbox write so
`messageInfo.status` remains `Delivered`.

## Runtime repair

The prior session was blocked because `yarn` was not on `PATH`.

This round used a temporary shim outside the repo:

```bash
PATH=/tmp/nss-yarn-shim:/home/kt/.cargo/bin:/home/kt/.local/share/solana/install/active_release/bin:$PATH \
ANCHOR_MOCHA_FILES=tests/ccip.ts \
anchor test --skip-build -- --features localnet --no-default-features
```

The shim dispatches `yarn run ts-mocha ...` to `node_modules/.bin/ts-mocha`.
No repository config was changed.

## Bug fix before replay

The N4 test body reached execution but failed on a local TypeScript encoding
bug:

```text
TypeError: Cannot mix BigInt and other types, use explicit conversions
```

Fixed locally in the gitignored Lombard source clone:

```ts
amountLeBytes.writeBigUInt64LE(BigInt(wrongAmount.toString()));
```

## Result

The targeted CCIP suite now passes:

```text
✔ N4 v6.51: failed executeOfframp ROLLS BACK mailbox messageInfo.status
  (still Delivered, not Handled) (2440ms)

11 passing (40s)
```

## Adjudication

`SIG-XR-001-ROLLBACK` is **closed as validator-backed honest-zero**.

The Solana mailbox does assign:

```rust
message_info.status = MessageState::Handled;
invoke_signed(...)?;
```

but the recipient CPI revert rolls back the whole transaction, including the
pre-CPI status write. The post-state stays `Delivered` (`MessageState` enum
byte `1` at offset 8 after the Anchor discriminator), not `Handled` (`2`).

## Submission status

No submission-ready Lombard finding.

This closes the strongest open fund-loss-looking Solana cross-layer signal as
safe under validator semantics.

## Carry-forward

1. Continue Crucible state expansion (`action_create_session`,
   `action_post_session_signatures_*`).
2. Keep `SIG-CR-001-OOB-DOS` informational unless validator reachability plus
   bounty-relevant impact is proven.
3. Keep EVM divergence as design contrast only unless an unauthorized mint,
   double spend, or bridge-accounting delta emerges.
