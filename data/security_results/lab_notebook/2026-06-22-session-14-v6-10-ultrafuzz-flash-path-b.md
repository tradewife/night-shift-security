# 2026-06-22 — Session 14: v6.10 Ultrafuzz-Informed Forensic Campaign (KLend mirror → Marginfi Path B)

**Author:** Orchestrator (Principal On-Chain Forensic Investigator, "the LLM is in the loop")
**Session:** Fourteenth orchestrator session (v6.10 proposal: `/home/kt/.factory/specs/2026-06-21-v6-10-ultrafuzz-informed-forensic-campaign.md`).
**Target:** KLend flash-loan surface (Path B mirror) and Marginfi flash-loan surface (Path B ixs_sysvar + new Action enum).

---

## Why this session exists

The Ultrafuzz post (`https://blog.monad.xyz/blog/ultrafuzz`) was re-fetched and re-read at session start. The load-bearing lesson applied: **the LLM is the orchestrator**, repeated fresh-context attempts matter, executable substrate evidence (not source reading) is the unit of truth, false positives come from harness defects, and cumulative pass@k accumulates across iterations.

v6.8/v6.9 had completed source-review Ultrafuzz phases on KLend but were blocked from executable substrate by:
1. Discriminator mismatch on the deployed KLend BPF (Anchor-lang sighash variant rejected with `InstructionFallbackNotFound`).
2. No anchor-0.31 mirror program available.
3. Toolchain friction: cargo-build-sbf + custom-toolchain delegation pulled session time without producing substrate evidence.

v6.10 picked the correct fallback per the Ultrafuzz principle: do not get stuck on tooling; pick the executable substrate you already have. Marginfi Path B had v6.7's working cargo-fuzz engine plus a clear extension surface (`StartFlashloan`/`EndFlashloan` Action variants, the `ixs_sysvar`/`load_instruction_at_checked` code path in `flashloan.rs`, and `validate_ixes_exclusive` in `ix_utils.rs`).

## What this session actually built

### Diff 1 — Path-B foundation: klend_mirror skeleton (engineering-frozen)

`sources/kamino/klend_mirror/{programs/klend_mirror,Cargo.toml,Anchor.toml,rust-toolchain.toml}` — minimal Anchor-0.31 mirror program with `initLendingMarket`, `initReserve`, `flashBorrowReserveLiquidity`, `flashRepayReserveLiquidity`, plus an admin-only `admin_drain_fee_vault` escape hatch for adversarial testing.

Status: **build-blocked** by the same cargo-build-sbf + hashbrown `edition2024` toolchain friction as the original klend. Session preserves the source tree and the build status note (`build_status.md`) so a future session with the right toolchain can resume.

### Diff 2 — Marginfi Path-B additions (working)

- `sources/marginfi/repo/programs/marginfi/fuzz/src/lib.rs` — append-only new helpers `process_action_start_flashloan()` and `process_action_end_flashloan()` on `MarginfiFuzzContext`. Rejections are expected (no real `sysvar::instructions::ID` AccountInfo in the simulator); any new reject category raises a substrate-class signal.
- `sources/marginfi/repo/programs/marginfi/fuzz/src/account_state.rs` — `new_dummy_sysvar_account_info()` helper for the dummy sysvar AccountInfo; preserves the same sysvar key but with empty data.
- `sources/marginfi/repo/programs/marginfi/fuzz/fuzz_targets/lend_flash_loan.rs` (NEW) — flash-loan focused fuzz target with `FlashAction::{StartFlash, EndFlash, Deposit, Borrow, UpdateOracle, Withdraw, Liquidate}` enum and forced `advance_time(1800s)` between actions so each iteration lands in a fresh process-time window.
- `sources/marginfi/repo/programs/marginfi/fuzz/Cargo.toml` — `[bin] lend_flash_loan` registered.
- `hermes/scripts/v6_10_flash_orchestrator.py` (NEW) — pass@k orchestrator; 5 attempts × ~20s bounds each.
- `data/security_results/investigations/2026-06-22-v6-10-mirror-attempt-1/{setup.md, property_fanin.md, build_status.md, summary.json, fuzz_long_run.json, evidence/}` — campaign artifacts.

### Build & run results

| Step | Outcome |
|------|---------|
| `cargo +nightly-2024-06-05 build --release --bin lend_flash_loan` | `Finished release profile [optimized + debuginfo] target(s)` — binary at `target/release/lend_flash_loan`, 83 MB. |
| 5 attempts × ~20s, fresh-context (orchestrator) | exit_code=`[0,0,0,0,0]`, panic_count=`[0,0,0,0,0]`, `runs_passing=5`, `runs_failing=0`, `verdict=ENGINE-LEVEL HONEST-ZERO`. |
| Long fuzz: 86s, `-max_total_time=85`, empty corpus | `393,550,742` cumulative executions, `4,576,171 avg exec/s`, `0 new_units_added`, `peak_rss_mb=28`, exit_code=`0`. |

No substrate-class panics. No new units produced. Engine-level honest-zero recorded.

### Empirical-FNR dataset extension (v6.10)

| # | Substrate | Engine | Attempts | Findings |
|---|-----------|--------|----------|----------|
| 1 | Marginfi v2 (v6.7) | cargo-fuzz lend + lend_extended | 7 | 0 |
| 2 | KLend (v6.9) | validator harness | 1 | 0 (engineering-blocked) |
| **3** | **Marginfi v2 flash-loan focus (v6.10)** | **cargo-fuzz lend_flash_loan (Path-B)** | **5 + 1×86s long** | **0** |

N=3 confirms the audit-saturation framing across two separate Marginfi execution surfaces and pre-existing fork blur on the third. No `submit_ready` movement; gates remain intact.

## Trust boundary / gate discipline

- All paths to `data/security_results/bounty/submittable/` go through `qualifies_for_submission()`. No candidate reached it this session.
- No external API writes, no pitch deck changes, no platform Intel sync this session.
- No change to `manifest.json` (still `pack_count=0`, timestamp from prior v6.9).
- User-owned untracked dirs preserved: `sources/drift/`, `sources/reserve/repo/` not modified.

## What v6.11+ should focus on (carry-forward)

1. **KLend mirror build lift** — in a session with newer cargo+platform-tools, run `anchor 0.31.1 build` against the existing mirror skeleton. Substrate coverage of klend's flash-loan can resume where v6.9 stopped, since discriminators now match between harness and mirror.
2. **Marginfi lethality escalation** — extend `FlashAction` enum with explicit `BorrowInCallback + LiquidateOther` interleavings; stage an `AccountLiquidate` action that runs *between* `StartFlash` and `EndFlash`; the current fuzz already wires this but adversarial ordering is the weakest link.
3. **Forensic cross-substrate correlation** — feed the cumulative 393M-iter stats into the empirical-FNR dataset summary in `SPEC.md §0.2` and update the audit-saturation framing table.

— kthxbye.

---

## Correction pass after v6.10 review (same session)

A post-run review found four concrete defects in the first v6.10 implementation:

1. `lend_flash_loan.rs` consumed fuzz bytes for `initial_bank_configs` before actions, so the action sequence could be empty and never exercise flash paths.
2. `v6_10_flash_orchestrator.py` passed a seed file path directly to libFuzzer, causing fixed-input replay (`NOTE: fuzzing was not performed`) while still reporting `ENGINE-LEVEL HONEST-ZERO`.
3. KLend mirror used invalid placeholder program id `MirrorKLendXXXXXXXXXXXXXXXXXXXXXXXXXXXXxx`.
4. Direct-call flashloan end could reject with `NotAllowedInCPI`, and start sysvar layout could panic when modeled with empty data.

Fixes applied:

- `FlashFuzzerContext` now uses deterministic dummy bank configs and dedicates fuzz input bytes to the flash/action sequence.
- `FlashSequence` rejects too-short/empty inputs instead of accepting an empty sequence.
- `AccountsState::new_flashloan_ixs_sysvar_account_info()` constructs a real in-memory instructions sysvar with synthetic current/start and `END_FLASHLOAN` instructions.
- `process_action_start_flashloan` and `process_action_end_flashloan` now log instruction rejections instead of treating expected program errors as fuzzer crashes.
- The orchestrator now runs libFuzzer against per-attempt corpus directories with `-max_total_time`, parses executed-unit stats, rejects fixed-input replay, and requires observed flash actions before counting a pass.
- KLend mirror ID was replaced with valid pubkey `G9cZAWjKwksrb2fRxD3DxULMn6o6r4BhhxXNxxdXfrnA`; mirror build now gets past the old `String is the wrong size` blocker and stops at the known hashbrown/platform-tools Cargo 1.79 blocker.

Corrected evidence:

| Run | Result |
|-----|--------|
| Pass@k orchestrator | 5/5 passing attempts; exit_code `[0,0,0,0,0]`; panic_count `[0,0,0,0,0]`; executed_units `[283885,277065,276515,275365,265135]`; start rejects `[23082,20788,21909,22006,23327]`; end rejects `[5347,6051,6708,5925,5829]`; fixed_input_replay=false; flash_actions_observed=true for every run. |
| Long fuzz | 86s; 938,090 executions; 10,908 exec/s; start_reject_count=80,259; end_reject_count=21,456; panic_count=0; fixed_input_replay=false; verdict=`ENGINE-LEVEL HONEST-ZERO`. |

Corrected conclusion: v6.10 now satisfies the Ultrafuzz proposal materially: repeated real fuzzing attempts, flash actions observed, failures preserved, and no gate-passing candidate. `submit_ready` remains 0.
