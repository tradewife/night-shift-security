---
name: ultrafuzz-discovery
description: Use when turning a target surface into executable, repeated fuzz/invariant discovery. Applies the Monad Ultrafuzz lessons: property fan-in, strategy fan-out, fresh-context pass@k attempts, preserved failures, strict adjudication, and gate discipline.
---

# Ultrafuzz Discovery

Apply the workflow from Monad Foundation's Ultrafuzz post:
`https://blog.monad.xyz/blog/ultrafuzz`.

For Solana programs, prefer Crucible for invariant fuzzing when a program `.so`
and IDL or hand-rolled instruction bindings are available:
`sources/crucible/repo` (upstream `https://github.com/asymmetric-research/crucible`).

This skill is for **the agent in the loop**: this Droid, future orchestrators,
and Hermes cron. It is not a shell-command wrapper. The operator must actively
enumerate properties, generate target-specific strategies, run executable tests,
preserve failures, triage harness artifacts, and accumulate pass@k evidence.

## Core lessons

- **Engine > wrapper.** Source review and multi-agent rhetoric are not evidence
  unless an executable harness/fuzzer exercises the substrate.
- **Fresh context repetition matters.** Repeated runs of the same prompt/strategy
  can surface disjoint bug sets. Run K attempts and record every attempt.
- **Properties before strategies.** Build a canonical property fan-in table before
  writing fuzz tests or invariant targets.
- **Strategies must be target-specific.** Generic strategy catalogs underperform
  unless adapted to the protocol's actors, account model, integrations, trust
  assumptions, and bounty scope.
- **Preserve failures.** Never overwrite or "fix away" a failing reproducer before
  saving the input, logs, state deltas, command, and adjudication note.
- **False positives are usually harness defects.** Classify harness artifacts
  separately from production/substrate defects.
- **Pass@k is cumulative evidence.** Summaries must report unique validated
  findings, overlapping findings, honest-zero runs, and blockers separately.
- **For Solana sequence bugs, use structured action mutation.** Crucible mutates
  typed action sequences and parameters directly, preserving structure and
  improving coverage discovery over byte-decoding via `arbitrary`.

## When to invoke

Use this skill before or during any discovery session that involves:

- new target onboarding,
- a high-bounty target with source available,
- an underspecified control-flow/composition hypothesis,
- a fuzz harness, invariant test, validator replay, or local mirror,
- an honest-zero claim based on source review,
- a v6+ engine-level empirical-FNR datum.

For Solana specifically, use this skill when investigating:

- account-state invariants (`delegation.stake <= lamports`, vault conservation,
  reserve liquidity vs fees, collateral vs debt),
- instruction-sequence bugs (start/end flash loans, deactivate/withdraw/rescind,
  refresh/liquidate, split/merge/close),
- sysvar/time/epoch/slot behavior,
- PDA/account-loader authority constraints,
- Token-2022 / SPL token extension accounting.

Do **not** invoke it for pure platform scans, catalogue-only Solodit digesting,
or submission packaging after a candidate has already passed gates.

## Workflow

### 1. Setup

Read, in order:

1. active session plan (`data/security_results/day_shift/current.md` if present)
2. newest relevant lab notebook entry for the target
3. target source/recon/IDL/ABI/account-map artifacts
4. bounty scope and submission gates
5. prior runs and known blockers

Create an investigation directory:

```bash
data/security_results/investigations/YYYY-MM-DD-vX-ultrafuzz-<target>/
```

Persist:

- `setup.md`
- `property_fanin.md`
- `strategies/*.md`
- `runs.jsonl`
- `summary.json`
- `adjudication/*.json`
- `evidence/*`

### 2. Property fan-in

Write a canonical table with:

| Field | Meaning |
|-------|---------|
| `property_id` | Stable ID, e.g. `PROP-FLASH-001` |
| `surface` | Function/instruction/actor flow |
| `invariant` | What must always hold |
| `bug class` | Conservation, authority, ordering, oracle, precision, CPI, token-extension, etc. |
| `kill criteria` | What negative evidence falsifies the hypothesis |
| `evidence required` | Logs, tx sig, account delta, balance delta, state flag, etc. |

Include protocol-specific details. For Solana, include instruction sysvar,
PDAs, token program variants, account loaders, signer/authority constraints,
and CPI/top-level restrictions.

### 3. Strategy fan-out

Create at least 3 strategy files when target scope permits:

- round-trip / pair properties
- stateful invariant sequences
- differential or mirror-vs-source checks
- instruction-order/sysvar manipulation
- token-account / Token-2022 accounting
- oracle/refresh/liquidation timing
- adversarial actor-flow tests

Each strategy must name the properties it covers and the expected false-positive
classes.

### 4. Executable attempts

Run repeated attempts. Minimum shape for a material claim:

- 3+ fresh-context attempts for a new target surface
- 5+ attempts for a high-bounty or previously blocked surface
- one longer fuzz run when the target compiles and mutates inputs

Every `runs.jsonl` row must include:

```json
{
  "attempt": 1,
  "strategy": "flash-loan-ordering",
  "binary_or_command": "...",
  "exit_code": 0,
  "executed_units": 12345,
  "fixed_input_replay": false,
  "actions_observed": true,
  "panic_count": 0,
  "new_findings": [],
  "artifact_paths": []
}
```

If using libFuzzer, **do not** count fixed-input replay as fuzzing. Passing a
file path executes that file once; pass a corpus directory plus
`-max_total_time` for actual fuzzing.

### 4a. Solana Crucible path (preferred for invariant sequence fuzzing)

Use Crucible when the target surface is a Solana program and the bug class
depends on instruction ordering, account state, or time/slot transitions.

Clone is tracked locally at:

```bash
sources/crucible/repo
```

Install CLI when needed:

```bash
cd sources/crucible/repo
cargo install --path crates/crucible-fuzz-cli
```

Initialize a harness:

```bash
crucible init <program_name> -C data/security_results/investigations/<run_id>/crucible/<program_name>
```

Harness structure:

```rust
#[derive(Clone)]
struct TargetFixture {
    ctx: TestContext,
    program_id: Pubkey,
    // protocol-specific accounts, signers, PDAs, mint/vault state
}

#[fuzz_fixture]
impl TargetFixture {
    pub fn setup() -> Self { /* load .so, create accounts, snapshot */ }

    pub fn action_deposit(&mut self, #[range(0..N_USERS)] user: usize, amount: u64) { /* ... */ }
    pub fn action_start_flashloan(&mut self, #[range(0..N_USERS)] user: usize) { /* ... */ }
    pub fn action_end_flashloan(&mut self, #[range(0..N_USERS)] user: usize) { /* ... */ }
    pub fn action_advance_slots(&mut self, #[range(0..50_000)] slots: u64) {
        self.ctx.warp_to_slot(self.ctx.slot() + slots);
    }
}

#[invariant_test]
fn invariant_test(fixture: &mut TargetFixture) {
    // use fuzz_assert_* macros, not assert!()
}
```

Crucible run commands:

```bash
# Dry-run validates setup without claiming fuzz coverage.
crucible run <program_name> invariant_test -C <harness_dir> --dry-run

# Stateless sequence fuzzing.
crucible run <program_name> invariant_test -C <harness_dir> --release --timeout 120 --cores 4

# Stateful mode: preferred once setup is stable and state cloning is cheap.
crucible run <program_name> invariant_test -C <harness_dir> --release --stateful --max-depth 50 --cores 4

# Coverage once harness is useful.
crucible run <program_name> invariant_test -C <harness_dir> --release --coverage --timeout 120 --lcov-out <run_dir>/coverage.lcov

# Faster late-campaign throughput after coverage saturates.
crucible run <program_name> invariant_test -C <harness_dir> --release --stateful --no-tracing --timeout 120
```

Crash/repro commands:

```bash
crucible show <program_name> -C <harness_dir>
crucible show <program_name> <crash_file> -C <harness_dir> --replay
crucible tmin <program_name> invariant_test <crash_file> -C <harness_dir> --release
crucible cmin <program_name> invariant_test <corpus_dir> -C <harness_dir> --release
```

Crucible artifact requirements for NSS:

- copy `crashes/<test_name>/*` into `evidence/crucible/`
- save `crucible show` output and minimized sequence after `tmin`
- save corpus/coverage stats when available
- record whether mode was `stateless`, `stateful`, `no-tracing`, or `replay`
- never classify `--dry-run`, `--replay`, or coverage-only corpus replay as fuzzing
- if a harness uses a mirror program, mark findings `mirror_only_divergence`
  unless source equivalence is documented

Crucible target selection heuristic:

| Use Crucible when | Prefer existing harness/libFuzzer when |
|-------------------|-----------------------------------------|
| bug requires action sequences | byte-level parser/math fuzzing is enough |
| program has `.so` + IDL or easy raw calls | target already has mature cargo-fuzz target |
| LiteSVM setup is feasible | validator-only sysvar/CPI behavior is essential |
| stateful pool can shortcut deep states | state cloning is too expensive or unsupported |

### 5. Failure preservation

For every non-zero exit, panic, invariant failure, or unexpected rejection:

- copy the crash/reproducer input into `evidence/`
- save stdout/stderr and command
- record pre/post state if available
- keep the failing test as-is until adjudication is written
- classify before modifying the harness

For Crucible findings, run `crucible tmin` before final triage and include both
the original and minimized sequence unless minimization fails.

### 6. Adjudication

Classify each candidate as exactly one:

- `production_defect`
- `underspecified_issue`
- `harness_artifact`
- `mirror_only_divergence`
- `fixture_only_behavior`
- `engineering_blocker`
- `engine_level_honest_zero`

For Crucible, treat `[FUZZ_FINDING]` plus `crucible show --replay` success as an
executable candidate. Treat CLI setup failures, LiteSVM unsupported sysvars, and
mirror-only behavior as harness/blocker classes until replayed on the intended
substrate.

Promotion requires:

1. executable discovery (not source-only),
2. validator/fork/local substrate confirmation appropriate to the target,
3. measured impact or bounty-relevant state transition,
4. existing NSS gates, especially `qualifies_for_submission()`,
5. human gate before any external post.

### 7. Summary and handoff

The final `summary.json` must distinguish:

- real fuzz attempts vs fixed replay,
- executed units/iterations,
- actions actually observed,
- unique substrate signals,
- harness artifacts,
- honest-zero basis,
- next dynamic strategies.

Write a lab notebook entry with **same vs different** against the prior run.

## Cron / HIPIF usage

When Hermes cron reaches refinement, coordinator, or new-surface engine work:

1. invoke `ultrafuzz-discovery` before claiming an engine/harness result,
2. write investigation artifacts under `data/security_results/investigations/`,
3. fold only after `summary.json` and lab notebook exist,
4. never mark `submit_ready` from this skill alone.

## Gotchas

- Fixed-input libFuzzer replay prints `NOTE: fuzzing was not performed`; this is
  not an engine-level honest-zero.
- Crucible `--dry-run`, `--replay`, and coverage-only corpus runs are not fuzzing
  attempts; only `crucible run ... --timeout/--cores/--stateful` exploration
  counts toward pass@k.
- Empty action sequences can produce misleading clean runs. Require
  `actions_observed=true` for pass counts.
- Solana host-side direct calls can reject with `NotAllowedInCPI`; this is a
  harness classification unless a top-level validator transaction proves it.
- Mirror programs are useful for discriminator recovery but can only support
  `mirror_only_divergence` unless source-equivalence is documented.
- A clean crash-free fuzz run is not a submission. It is an empirical-FNR datum
  unless a candidate survives NSS gates.
- Use `fuzz_assert_*` in Crucible invariants. Plain `assert!` kills the process
  and can obscure actionable minimized sequences.
