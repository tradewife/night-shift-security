# Session plan - next
Status: queued

## Objective

v6.17 handoff: continue the 3F Grunt execution track started in v6.17, then
return to the v6.15 et al. submission gates. Three concrete carries-forward:

1. Resolve the OnRe human-gate decision first (unchanged from previous
   handoff; no autonomous submission from v6.17 either).
2. Build a production-bootstrap PositionManager scaffold (multi-position
   seeded state) for an H1-prime falsifier; record results as v6.18
   evidence. The current H1-prime static analysis killed within session
   budget; carry-forward signal stays positive but does not yet flip a
   candidate.
3. Only continue Origin ARM after a fresh `nss_origin_jit_monitor.py` run
   finds non-zero `pendingRedeemAssets` AND material cross-discount release.

## Blocks

- [ ] Human-review `data/security_results/bounty/submittable/onre/NSS-ONRE-1.json` and decide whether to submit externally, including the configuration-dependent exposure caveat.
- [ ] Human-review WEB-003 (`findings/WEB-003-blind-trust-external-aggregator-tx.md`) once Origin reviewers are available.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen `ORIGIN-ARM-JIT-1` only if Ethena ARM is unpaused with non-zero `pendingRedeemAssets` and material discount release.
- [ ] Build a production-bootstrap PM scaffold for H1-prime on the 3F Grunt substrate, capture static + dynamic evidence into the v6.18 investigation folder.
- [ ] Stateful-fuzz campaign on the H4 surface using forge-std's orchestrator.
- [ ] Non-role liquidator nested-callback harness for H8-prime.
- [ ] Re-run `hermes/scripts/v6_16_grunt_static_probe.py` after every in-scope source change and diff against the baseline envelope.
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote `ORIGIN-ARM-JIT-1` from research on local PoC alone; live materiality is currently zero.
- Do **not** autonomously submit OnRe `NSS-ONRE-1` or Origin `WEB-003`; both are still human-gated.
- Do **not** promote a 3F Grunt candidate solely on the v6.17 H4 falsifier green: that is a falsifier-pass datum, not an absence-of-bug proof.
- Do **not** count fixed-input replay, dry-run, or replay-only runs as fuzzing.
- Use `ultrafuzz-discovery` before any engine-level honest-zero or candidate claim.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Do **not** run the full bounty-depth chain unless engine substrate counts/iterations change materially.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`
