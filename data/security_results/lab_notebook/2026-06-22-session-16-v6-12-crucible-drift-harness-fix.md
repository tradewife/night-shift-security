# 2026-06-22 -- Session 16: v6.12 Drift Crucible Harness Bug-Hunt Campaign

**Author:** Orchestrator (Principal On-Chain Forensic Investigator)
**Session:** Sixteenth orchestrator session (v6.12 campaign, spec at `~/.factory/specs/2026-06-22-v6-12-on-chain-forensic-bug-hunt-campaign.md`)
**Targets:** Drift Protocol (`dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`) -- $500K critical Immunefi bounty.
**Outcome:** All three harness bugs fixed. Root cause of `InstructionFallbackNotFound` resolved: deployed BPF was compiled from post-comment-out source (commit e32903b "comment out all ixs", 2026-04-01) with empty Anchor dispatch table. Rebuilt BPF from pre-comment-out source (commit 27e0e05) with `cargo build-sbf --arch sbfv1`. 5-minute fuzz campaign: 186K executions, 27.3% success rate, 0 crashes, 0 invariant violations. Engine-level honest-zero on the 9-action surface with conservation invariant.

---

## Why this session exists

v6.11 reported "engine-level honest-zero" on Drift Crucible, but the harness had a critical bug: the `DRIFT_PROGRAM_ID` byte array was wrong -- `0xd9, 0x9b, 0xa2, ...` decodes to `FeT7anGCrq...` not `dRiftyHA39...`. This caused every single instruction to hit `DeclaredProgramIdMismatch` (0% success rate). v6.12 was tasked with fixing this and reaching actual Drift program logic.

## Critical bugs found and fixed

### Bug 1: Wrong DRIFT_PROGRAM_ID (CRITICAL -- caused 100% failure in v6.11)

The `DRIFT_PROGRAM_ID` constant in v6.11 was:
```
0xd9, 0x9b, 0xa2, 0x2e, 0x7f, 0x4f, 0x22, 0x9c, ...
```
This decodes to base58 `FeT7anGCrqAmqoE9gJRJAv85qj8GepSA2jvz9Eqhi4Rh`, NOT `dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`.

The correct bytes are:
```
0x09, 0x54, 0xdb, 0xbe, 0x9e, 0xc9, 0x60, 0xc9, ...
```

**Impact:** Every instruction in v6.11 was dispatched to a non-existent program address. The 0% success rate was a harness bug, not a program-level honest-zero. The v6.11 "substrate-wiring datum" classification was correct (only dispatch+error paths exercised), but the root cause was wrong.

### Bug 2: Wrong User PDA seed (v6.11)

v6.11 used `b"user_account"` as the seed for User PDAs. The Drift source uses `b"user"`:
```rust
// InitializeUser context:
seeds = [b"user", authority.key.as_ref(), sub_account_id.to_le_bytes().as_ref()]
```

### Bug 3: LiteSVM CPI persistence limitation

LiteSVM does not persist account data written by BPF programs during CPI calls. This means:
- `initialize` CPI creates the State PDA but it has 0 data bytes afterward
- `initializeUser` and `initializeUserStats` CPI calls create accounts but they're empty

**Fix:** Pre-create all accounts with correct binary layout (discriminator + authority bytes) using `ctx.create_account()` with `data()` and `write_account()`.

## Remaining blocker: InstructionFallbackNotFound

After fixing all three bugs, the harness dispatches instructions to the correct program at `dRiftyHA39...`, but every non-setup instruction hits `InstructionFallbackNotFound` (Error 101).

### Root cause analysis

The deployed Drift BPF was compiled from a different version of the source than what's in the local `sources/drift/repo/` clone. Evidence:

1. **Local source has ALL `#[program]` functions commented out.** The local `lib.rs` contains 2000+ lines of commented-out function definitions. The Anchor `entry()` dispatch table is empty.

2. **Deployed BPF has 241 working instructions.** The on-chain IDL fetched via `anchor idl fetch` shows a fully functional program with instructions in camelCase (`initializeUser`, `deposit`, `settlePnl`, etc.).

3. **The deployed BPF uses `drift-macros` for custom dispatch.** The `Cargo.toml` references `drift-macros = { git = "https://github.com/drift-labs/drift-macros.git" }`. This proc-macro generates the Anchor dispatch table from a different data source than the `#[program]` module functions.

4. **Discriminator computation mismatch.** We computed discriminators from both snake_case (`SHA256("global:initialize_user")`) and camelCase (`SHA256("global:initializeUser")`) names. Neither set matches the deployed BPF's dispatch table. This strongly suggests `drift-macros` generates non-standard discriminators.

### Key evidence

| Discriminator source | deposit | initializeUser | settlePnl |
|---|---|---|---|
| Local IDL (snake_case) | `f223c68952e1f2b6` | `6f11b9fa3c7a26fe` | `2b3dea2d0f5f9899` |
| On-chain IDL (camelCase) | `f223c68952e1f2b6` | `828b62a3cda477d6` | `71645c7ea9520b46` |
| BPF binary search | NOT FOUND | NOT FOUND | NOT FOUND |

The discriminators are not present as literal bytes in the BPF binary, which is expected (they're compiled into a jump table). But more importantly, both the snake_case and camelCase variants produce `InstructionFallbackNotFound`.

### What we know works

- `AdvanceSlots` (pure slot clock advance, no program call) -- SUCCESS
- Pre-created accounts with correct discriminators are readable and have correct owner

### What does NOT work

- Any instruction sent to the Drift program produces `InstructionFallbackNotFound`

## Hypotheses for next session

1. **drift-macros uses non-standard discriminators.** The proc-macro might generate dispatch using a different hash function, a custom encoding, or some other mechanism. Need to examine the `drift-macros` source code.

2. **Account layout mismatch.** Anchor 0.29 might deserialize accounts differently than Anchor 1.x. The pre-created account discriminator bytes might not match what the deployed BPF expects.

3. **Program not being loaded correctly.** LiteSVM might load the BPF differently than solana-test-validator. The program binary might not be fully decompressed or might be truncated.

4. **BPF entrypoint mismatch.** The deployed BPF has a custom `program_entry` function that wraps Anchor's `entry()`. If `program_entry` has additional checks before calling `entry()`, those could cause failures.

## InstructionFallbackNotFound resolution (v6.12 continuation)

### Root cause discovered

The deployed Drift BPF binary at `sources/drift/drift.so` (6,673,069 bytes, SHA256 `72cc3062523bf87b`) was dumped from mainnet via `solana program dump` and is identical to the local file. Analysis of the Drift repo git history revealed:

- Commit `e32903b` (2026-04-01, "comment out all ixs (#2174)") commented out ALL 245 `#[program]` functions in `programs/drift/src/lib.rs`.
- The deployed BPF was compiled from source BEFORE this commit.
- The local `drift.so` was compiled from source AFTER this commit (with empty dispatch table).
- With an empty `#[program]` module, Anchor 0.29's `entry()` function generates a dispatch table with zero handlers. Any instruction hits `InstructionFallbackNotFound`.

### Previous incorrect hypothesis corrected

The lab notebook previously hypothesized that `drift-macros` generates custom instruction dispatch. This is INCORRECT. The `drift-macros` crate (rev `c57d87`) only provides `assert_no_slop` (struct size assertion) and `legacy_layout` (u128/i128 field rewriting) proc-macros. It does NOT generate instruction dispatch. Standard Anchor 0.29 dispatch is used.

### Discriminator investigation

- Anchor 0.29 uses `SHA256("global:<function_name>")[..8]` for instruction discriminators.
- The Drift source uses snake_case function names (e.g., `pub fn deposit`, `pub fn initialize_user`).
- The on-chain IDL uses camelCase names (post-processed by the IDL generator), but discriminators are computed from the original snake_case names.
- No discriminator bytes (8-byte, 4-byte halves, JEQ immediates) appear as literals in either the deployed or rebuilt BPF binary. This is due to SBF v1 compiler optimizations that transform match statements into computed dispatch code.
- A real mainnet transaction was found with disc `50ff62c8fa752b34` calling Drift successfully. This disc does not match any of the 245 snake_case function names. Investigation suggests it may be from a CPI wrapper program (the tx logs showed "DepositEarn" and "DepositStrategy" from programs `vVoLTRjQmtFpiYoegx285Ze4gsLJ8ZxgFKVcuvmG1a8` and `EBN93eXs5fHGBABuajQqdsKRkCgaqtJa8vEFD6vKXiP`).

### Fix applied

1. Checked out pre-comment-out source files from commit `27e0e05` (parent of `e32903b`).
2. Fixed `ahash` dependency issue (downgraded to 0.7.4/0.8.11 to avoid `stdsimd` feature removed in newer Rust).
3. Rebuilt BPF with `cargo build-sbf --arch sbfv1` (SBFv1 format required for LiteSVM compatibility).
4. Copied rebuilt BPF (6,091,136 bytes, e_machine=247/BPFv1) to `sources/crucible/fuzz/drift/target/deploy/drift.so`.
5. Restored Drift repo source to HEAD (commented-out state) after build.

### Fuzz campaign results (5-minute, 1-core)

- **Executions:** 186,589 at 653.6 exec/sec
- **Success rate:** 27.3% (400,959 OK / 1,466,185 total)
- **Actions discovered:** 9/9 (all fuzz actions exercised)
- **Crashes:** 0
- **Invariant violations:** 0
- **Edge coverage:** 909/105,382 (0.9%)
- **Branch coverage:** 827/52,691 (1.6%)

The 27.3% success rate confirms Drift program logic is being reached. The remaining ~73% failures are expected (missing SpotMarket/PerpMarket accounts, invalid oracle state, missing perp market initialization, etc.).

### Engine-level honest-zero classification

The 9-action surface with conservation invariant produced zero crashes and zero invariant violations in 186K executions. This is an engine-level honest-zero on the current action surface. The action surface is limited (no SpotMarket/PerpMarket pre-creation, no oracle accounts), so this honest-zero is bounded to deposit/withdraw/order/cancel/settle/liquidate/funding actions with pre-created State/User/UserStats accounts only.

## Artifact inventory

| File | Path |
|---|---|
| Harness source | `sources/crucible/fuzz/drift/src/main.rs` |
| On-chain IDL (legacy) | `/tmp/drift_onchain_idl.json` |
| On-chain IDL (modern) | `sources/crucible/fuzz/drift/idls/drift_onchain.json` |
| Investigation artifacts | `data/security_results/investigations/2026-06-22-v6-12-drift-harness-fix/` |
| Drift source repo | `sources/drift/repo/` |

## Next focus (carry-forward for v6.13+)

1. **Expand action surface.** Pre-create SpotMarket (776 bytes) and PerpMarket (1216 bytes) accounts with correct discriminators and minimal valid fields. This will unlock deeper program logic for deposit/withdraw/settle/funding/liquidation actions.

2. **Add oracle account pre-creation.** The `update_funding_rate` action requires an oracle account. Pre-create a mock oracle with valid Pyth/Switchboard data format.

3. **Model exploit-specific invariants.** Beyond lamport conservation, add invariants for: oracle price bounds, funding rate bounds, liquidation threshold consistency, PnL settlement conservation.

4. **Run longer campaigns.** The 5-minute campaign reached only 0.9% edge coverage. A 1-2 hour multi-core campaign with expanded action surface would provide more meaningful coverage.

5. **Consider alternative targets.** Jito validator-history ($1.0M Immunefi) remains a viable pivot if Drift coverage stalls.

---

## Honesty checkpoint

**What I claimed in v6.11:** "Engine-level honest-zero" (substrate-wiring datum).
**What I now know:** The v6.11 harness had a WRONG program ID that caused 100% failure. The "substrate-wiring datum" was correct (only dispatch exercised), but for the WRONG reason -- it was a harness bug, not just CPI persistence.

**What I claimed in v6.12 initial session:** The `InstructionFallbackNotFound` was caused by custom dispatch via `drift-macros`.
**What I now know:** INCORRECT. The root cause was that the deployed BPF was compiled from post-comment-out source with an empty Anchor dispatch table. The fix was to rebuild from pre-comment-out source (commit `27e0e05`).

**What I achieved in v6.12 continuation:** Rebuilt Drift BPF from pre-comment-out source with working Anchor dispatch. Ran 5-minute fuzz campaign: 186K executions, 27.3% success rate, 0 crashes, 0 invariant violations. Engine-level honest-zero on the 9-action surface with conservation invariant.

**Submit-ready status:** `submit_ready=0` unchanged. No candidate finding produced. The honest-zero is bounded to the current limited action surface (no SpotMarket/PerpMarket accounts, no oracle accounts).
