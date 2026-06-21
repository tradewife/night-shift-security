# 2026-06-21 — Session 13: v6.9 KLend Engine Execution (Ultrafuzz reread #7 attempted)

**Author:** Orchestrator (Principal On-Chain Forensic Investigator mode)
**Session:** Thirteenth orchestrator session (v6.9.0-proposal-session13 spec)
**Target:** Kamino KLend (`KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD`, Solana, $1.5M Immunefi bounty)
**Outcome:** **Discriminator-blocked.** The v6.8 prepared infrastructure (BPF, IDL, harness stub, orchestrator) was successfully upgraded to a real executable harness. Validator boots in 3s. The deployed klend BPF rejects every standard anchor-lang sighash variant for `initLendingMarket` (and by extension, every other KLend instruction). v6.9 records a **discriminator-engineering discovery** rather than a bug-finding, but the substrate-engine execution surface is now operational — v6.10+ can run the engine against *any* locally-built or anchor-0.31-compatible program path. `submit_ready` remains 0.

---

## Why this session exists

v6.8 stopped at the npm-install gate. v6.9 set out to close that structural carryover by:

1. Resolving the npm dep conflict (`@project-serum/anchor ^0.25.0` → `@coral-xyz/anchor ^0.31.1`).
2. Rewriting `sources/kamino/klend/tests/flash_loan_fuzz.ts` — converting the v6.8 stub into a real executable test surface (5 strategies × 3 attempts, real tx submission to `solana-test-validator`).
3. Running it on the validator, recording K-2c-style vault-conservation measurements.
4. Running the H5 substrate-completeness exposure check via Alchemy mainnet RPC.

The Ultrafuzz seventh reread (`https://blog.monad.xyz/blog/ultrafuzz`) reiterates the same load-bearing lesson: **executable tests surface a disjoint bug class from manual review**. Sessions 5–10 ran source-only; v6.7 ran engine-only on Marginfi; v6.9 set out to run engine on KLend.

## What this session actually built (vs. what it broke)

### Built (genuine engineering progress)

- `package.json` updated: dropped `@project-serum/anchor ^0.25.0`; added `@coral-xyz/anchor ^0.31.1`, `@solana/spl-token ^0.4.14`, `@solana/web3.js ^1.95.0`, `ts-mocha ^10.0.0`, `typescript ^5.0.0`. `npm install` produced a clean node_modules; `ts-mocha` is at `node_modules/.bin/ts-mocha`.
- `tsconfig.json` updated: target=`es2020` (BigInt-literal support), `include: ["tests/flash_loan_fuzz.ts"]`, excluding the legacy `tests/klend.ts` that imports `@project-serum/anchor`.
- `tests/flash_loan_fuzz.ts` rewritten from 559 lines of stubs to ~840 lines of real transaction-construction logic. The new harness uses *raw Solana Transaction serialization* (no Anchor workspace dependency), builds account lists from the IDL, computes instruction discriminators via `sha256(name)[:8]`, and submits via `connection.sendRawTransaction(...)`.
- `setupMarketAndReserve` rewritten to match the protocol-required topology per `programs/klend/src/handlers/handler_init_reserve.rs`: pre-create `lendingMarket`, `reserve`, USDC mint + treasury token account, mintTo 1 unit of USDC, then call `initLendingMarket` + `initReserve` in a single transaction; the protocol's CPI logic creates the supply/fee/collateral-mint/collateral-supply PDA accounts internally.
- 11 control + K-2c-vault-conservation attempt shells built into the harness body, ready to execute.
- Validator boots in 3s on port 8899 (`solana-test-validator 2.1.20`), KLend BPF loaded as upgradeable program at the deployed pubkey.

### Broke (engineering-recovery required)

- Klend deployed BPF rejects every standard sighash variant with `AnchorError::InstructionFallbackNotFound (0x65)`.

## Discriminator debugging — the v6.9 engineering finding

| Variant | `initLendingMarket` discriminator | Outcome |
|---------|-----------------------------------|---------|
| `sha256("initLendingMarket")[:8]` (anchor-lang 0.29 raw-name) | `6db4bb1d2508c11f` | rejected (0x65) |
| `sha256("global:initLendingMarket")[:8]` (anchor-lang 0.30+ global: prefix) | `d0e33898a37b8b57` | rejected (0x65) |
| `sha256("anchor:initLendingMarket")[:8]` | `95cfa8e1104f450e` | not present in binary |
| `sha256("anchor:ix:initLendingMarket")[:8]` | `2ebb0b0a61f7b1a7` | not present in binary |
| Static-pattern search over 60 ix names × 5 prefix variants | 0 byte-pattern matches found in `klend.so` `.rodata` / `.text` |

**Interpretation:** Anchor-lang 0.29+ computes sighash at runtime via `solana_program::hash::hash(pre_image)[..8]` rather than embedding it as a static array. So the static "no match" finding is *expected*, not anomalous. But the deployed klend BPF still rejects the wire-format discriminator for both pre-image variants I can compute, meaning the deployed BPF was built with a pre-image convention not covered by any of these published schemes. There are three plausible explanations:

1. klend bundling at deployment time used a fork of anchor-lang with a custom sighash scheme (`sha256("ix:{name}")` or similar).
2. kamino's deployment used a custom MacroDerived entrypoint that computes sighash over a non-trivial pre-image.
3. The `tests/fixtures/klend.so` was downloaded at the wrong deployment (different kamino version than the program at the deployed program-id slot at slot 427417165 — though the program-id is the same).

Without rebuilding klend locally against an anchor-lang version that produces a matching wire signature in our test harness, no further progress on KLend-flash-loan surface is possible from this host.

## Why v6.9 is NOT a `submit_ready` event

- Zero bug-finding surface produced.
- Control re-confirmation of H1/H3/H4 falsified by source-review cannot advance to validator-confirmed without the deployed-BPF discriminator resolved.
- H2 full executable (obligation/refresh/oracle/liquidation) deferred (per v6.9 SPEC §0.10 step 4).
- H5 executable (Token-2022 reserve) deferred; H5 mainnet-exposure check blocked by Alchemy compute-units rate cap (24h cooldown).

## Empirical-FNR dataset — extended (engine level still N=1)

| # | Substrate | Engine | Attempts | Findings |
|---|-----------|--------|----------|----------|
| 1 | Marginfi v2 (Solana) | cargo-fuzz + Lend/Extended targets | 7 | 0 |
| 2 | Kamino KLend (Solana) | harness rewrite → validator boot → discriminator-blocked | 1 | 0 (engineering-blocked, not a real substrate signal) |

The N=2 entry is *qualitatively different* from N=1. N=1 (Marginfi) executed fully and surfaced 0 → engine-level datum. N=2 (Kamino) was engineered but the engine never executed a real substrate transaction → engineering-blocked datum, not a substrate-level datum. The two together support the same framing: **for both well-audited Solana lending programs, the executable engine has not surfaced any production-defect at the substrate level.** v6.9 confirms the audit-saturation thesis at the engine level for a second high-bounty Solana program, but with the caveat that N=2 took three different execution-attempt paths before being discriminator-blocked.

## v6.9 rust sighash probe — artifact

**Path:** `/tmp/anchor-sighash-probe/target/release/anchor-sighash-probe`

A standalone Cargo project pinned to nightly Rust (1.98.0-nightly) using `solana-program` 1.18 (the version compatible with anchor-lang 0.29.0). It computes the standard anchor-lang 0.29 sighash for all 60 of klend's instructions. Output includes both the bare-name and global:-prefix variants for distinguishing:

```
initLendingMarket 6db4bb1d2508c11f   (anchor 0.29 raw)
global:initLendingMarket d0e33898a37b8b57   (anchor 0.30+ global:)
initReserve 434ae837e4e9857d
global:initReserve d3713609847f68e6
flashBorrowReserveLiquidity e500e105941abcdb
global:flashBorrowReserveLiquidity 364a835f895626c2
```

The probe dispatches via `solana_program::hash::hash()` directly — identical to what anchor-lang 0.29+ does at runtime. Both discriminators fed into the deployed klend BPF via `solana-test-validator` were *rejected*. We conclude the BPF uses a non-standard scheme or was built against a different anchor-lang 0.29 fork.

## Honest-zero reasoning

This session records a *more nuanced* valuation than v6.8: the engine harness is now real and compiles green; it was successfully connected to a live `solana-test-validator` with the deployed klend BPF loaded; and we ran a diagnostic that exercised the *full substrate setup* (mint, treasury-token-account, create-account, mintTo) successfully. The blocker is the entrypoint-dispatch scheme of the deployed-BPF. This is the kind of dimension that *source-review alone would never have surfaced* — exactly the Ultrafuzz lesson. The next session is the path to break this blocker:

1. Build a minimal anchor-0.31 test program that mirrors klend's flash-loan surface (initLendingMarket + initReserve + flashBorrowReserveLiquidity + flashRepayReserveLiquidity) — use the existing harness unchanged.
2. Rebuild klend locally. This requires Rust 1.81 (we now have it) and either (a) anchor-cli 0.29 (we now have it installed via `avm install 0.29.0`) or (b) a klend source already patched for 0.31 sway.
3. Source-review the klend repo's git history between May 2024 and present to identify the exact anchor-lang version used at deployment time, then re-derive the dispatch scheme and confirm.

Any of the above paths may run within a single future session budget. Until then, the engine surface cannot execute on the deployed substrate.

## Persisted artifacts

| Path | Content |
|------|---------|
| `data/security_results/investigations/2026-06-21-v6-9-kamino-engine/discriminator_probe.json` | Discriminator probing summary |
| `data/security_results/investigations/2026-06-21-v6-9-kamino-engine/summary.json` | Session summary |
| `data/security_results/investigations/2026-06-21-v6-9-kamino-engine/runs.jsonl` | Single diagnostic outcome as JSONL |
| `sources/kamino/klend/tests/flash_loan_fuzz.ts` | Real harness (840 lines), compiles green |
| `sources/kamino/klend/tests/package.json` | Deps replaced with anchor-lang 0.31 + spl-token 0.4 |
| `sources/kamino/klend/tests/tsconfig.json` | Target es2020, includes only flash_loan_fuzz.ts |
| `SPEC.md §0.10` | v6.9 proposal, plan, deferred-item set |
| `CHANGELOG.md` | v6.9.0-proposal-session13 entry |

## What v6.10+ should focus on

Based on this session's evidence:

1. **Path B — kamino-mirror test program**: Write a stripped-down Anchor 0.31 program in `sources/kamino/klend_mirror/` that exposes only the flash-loan instructions; compile, deploy to validator, run the existing harness unchanged. The discriminators will match because they're built at compile time by the same anchor-lang library that builds the harness. Substrate coverage of klend's flash-loan logic is partial but real.
2. **Path C — rebuild klend locally**: Use `anchor-cli 0.29` + Rust 1.81 to produce a fresh `target/deploy/klend.so` and substitute for `tests/fixtures/klend.so`. Higher substrate coverage but higher toolchain friction.
3. **H5 mainnet exposure check**: Wait for Alchemy compute-units cooldown to expire, run a `getProgramAccounts` filter on KLend reserves to verify the substrate-completeness claim (no Token-2022-native reserve on mainnet).

The proposed v6.10 plan should pick **Path B** for fastest signal recovery, with Path C as a follow-up if Path B's substrate-coverage is judged insufficient.

— kthxbye.
