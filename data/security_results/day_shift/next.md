# Session plan — next

**Status: queued**

## Objective

v6.29 completed: (1) Variational sidecar closed (Medium finding), (2) Corpus correlation matrix added to SPEC §9.2, (3) Marginfi v2 Crucible harness built and fuzzed — 11.3M iterations, 0 crashes, 0 invariant violations (6th empirical-FNR datum). `submit_ready=0`.

**Next priority — from corpus gap analysis:**
1. **Extend Lombard Crucible harness** beyond consortium to mailbox + bridge instructions (corpus shows 91 bridge patterns, strong indicator for novel finding potential).
2. **Complete Midas Stream B** — validator reproduction of `mint_request → reject_mint_request` with payment-token-side lamport measurement.
3. **Add Token-2022 transfer fee invariant** to standard Crucible template — corpus blind spot, highest novelty potential.

**Carry-forward from prior sessions:**
1. Resolve the OnRe human-gate decision.
2. Build a production-bootstrap PositionManager scaffold for H1-prime falsifier on 3F Grunt substrate.
3. Stateful-fuzz campaign on H4/H9/H11/H17 surface using forge-std's orchestrator on 3F Grunt.
4. Continue Midas sidecar: extend Crucible harness beyond reject handlers (Stream B).
5. Continue Lombard second-ring surfaces (mailbox + bridge).
6. Continue Origin ARM after fresh `nss_origin_jit_monitor.py` run finds non-zero signals.
7. Maintain Sidecar posture until a reproduction-tier path survives submission gates.

## Blocks

- [x] ~~Human-review H1 pack~~ — **DONE.** Variational: downgraded to Medium.
- [ ] Human-review OnRe NSS-ONRE-1.json.
- [ ] Human-review Origin WEB-003.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen ORIGIN-ARM-JIT-1 only if material discount release.
- [ ] Build PM scaffold for H1-prime on 3F Grunt substrate.
- [ ] Extend Lombard Crucible: mailbox + bridge actions.
- [ ] Complete Midas Stream B validator reproduction.
- [ ] Add Token-2022 transfer fee invariant to Crucible template.
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote any candidate without human gate.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`

## v6.29 key references

- `data/security_results/lab_notebook/2026-06-28-v6-29-variational-sidecar.md`
- `data/security_results/investigations/2026-06-28-v6-29-variational-sidecar/setup.md`
- `data/security_results/investigations/2026-06-28-v6-29-variational-sidecar/property_fanin.md`
- `data/security_results/investigations/2026-06-28-v6-29-variational-sidecar/adjudication/H1_batch_deposit_creator_overdeposit_critical_permanent_freeze.json`
- `foundry/test/VariationalFalsifier.t.sol`
- `sources/variational/repo/source_manifest.json`
