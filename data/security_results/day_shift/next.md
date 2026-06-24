# Session plan - next
Status: queued

## Objective

v6.16 handoff: continue the 3F Grunt substrate added in session-20, then
return to the v6.15 et al. submission gates. Three concrete carries-forward:

1. Resolve the OnRe human-gate decision first (unchanged from previous
   handoff; no autonomous submission from v6.16 either).
2. Build a Foundry test harness for at least one H1/H3/H4-prime variant of
   the 3F Grunt hypothesis ledger. Static probe invariants must hold across
   each tested commit.
3. Only continue Origin ARM after a fresh `nss_origin_jit_monitor.py` run
   finds non-zero `pendingRedeemAssets` AND material cross-discount release.

## Blocks

- [ ] Human-review `data/security_results/bounty/submittable/onre/NSS-ONRE-1.json` and decide whether to submit externally, including the configuration-dependent exposure caveat.
- [ ] Human-review WEB-003 (`findings/WEB-003-blind-trust-external-aggregator-tx.md`) once Origin reviewers are available.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; reopen `ORIGIN-ARM-JIT-1` only if Ethena ARM is unpaused with non-zero `pendingRedeemAssets` and material discount release.
- [ ] Build a Foundry test harness for H1-prime (PositionManager share-inflation via Morpho donation) and H3-prime (Request pull/repay bypass) on the 3F Grunt substrate.
- [ ] Re-run `hermes/scripts/v6_16_grunt_static_probe.py` after every in-scope source change and diff against the baseline envelope.
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote `ORIGIN-ARM-JIT-1` from research on local PoC alone; live materiality is currently zero.
- Do **not** autonomously submit OnRe `NSS-ONRE-1` or Origin `WEB-003`; both are still human-gated.
- Do **not** promote a 3F Grunt candidate solely on the static probe; the next session must produce an executable Foundry reproduction against an in-scope commit.
- Do **not** count fixed-input replay, dry-run, or replay-only runs as fuzzing.
- Use `ultrafuzz-discovery` before any engine-level honest-zero or candidate claim.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Do **not** run the full bounty-depth chain unless engine substrate counts/iterations change materially.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`
