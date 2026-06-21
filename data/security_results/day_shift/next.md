# Session plan - next
Status: queued

## Objective

v6.11 executable-invariant escalation after corrected v6.10 honest-zero.

## Blocks

- [ ] Lift KLend mirror build blocker in `sources/kamino/klend_mirror/` by using a compatible Solana platform-tools/Cargo dependency set or safely pinning dependencies; preserve source-equivalence notes before claiming substrate evidence
- [ ] If KLend mirror builds, run flash-loan invariant harness and record pass@k plus long-fuzz evidence under a new investigation directory
- [ ] Extend Marginfi `lend_flash_loan` with explicit `BorrowInCallback` and `LiquidateOther` action interleavings between `StartFlash` and `EndFlash`
- [ ] Create first Crucible harness for a Solana target when `.so` plus IDL or raw-call bindings are available; use `crucible run`, `show`, `tmin`, `cmin`, and coverage artifacts per `ultrafuzz-discovery`
- [ ] Keep `submit_ready=0` unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate

## Night Shift handoff

- Do **not** treat v6.10 as pending. Corrected outcome is engine-level honest-zero.
- Do **not** count fixed-input replay, dry-run, or replay-only runs as fuzzing.
- Use `ultrafuzz-discovery` before any engine-level honest-zero or candidate claim.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Do **not** run the full bounty-depth chain unless engine substrate counts/iterations change materially.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`