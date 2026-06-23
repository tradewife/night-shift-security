# Session plan - next
Status: queued

## Objective

v6.15 handoff: resolve the OnRe human-gate decision first, then continue Origin
only if JIT monitor or cross-chain state becomes material.

## Blocks

- [ ] Human-review `data/security_results/bounty/submittable/onre/NSS-ONRE-1.json` and decide whether to submit externally, including the configuration-dependent exposure caveat.
- [ ] Run `hermes/scripts/nss_origin_jit_monitor.py`; only reopen `ORIGIN-ARM-JIT-1` if Ethena ARM is unpaused with non-zero `pendingRedeemAssets` and material discount release.
- [ ] If Origin continues, prioritize CrossChain/Morpho V2 paths where Master cached balances can over-credit Remote value, not conservative undercounts.
- [ ] If Origin stays non-material, rotate back to the next high-bounty substrate with executable harness potential.
- [ ] Keep `submit_ready=0` for new research unless a concrete measured-impact candidate passes `qualifies_for_submission()` and the human gate.

## Night Shift handoff

- Do **not** promote `ORIGIN-ARM-JIT-1` from research on local PoC alone; live materiality is currently zero.
- OnRe `NSS-ONRE-1` is the only current human-gated `submit_ready=1` pack.
- Do **not** count fixed-input replay, dry-run, or replay-only runs as fuzzing.
- Use `ultrafuzz-discovery` before any engine-level honest-zero or candidate claim.
- Prefer Crucible from `sources/crucible/repo` for Solana invariant sequence fuzzing when feasible.
- Do **not** run the full bounty-depth chain unless engine substrate counts/iterations change materially.
- Weekly: `platform sync --all`
- Intel: `data/security_results/intel/latest.md`