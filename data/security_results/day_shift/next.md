# Session plan — next

**Status: queued**

## Lombard cross-layer (closed acceptable-with-gaps, v6.51.19)

- **Verdict:** no submission-ready finding; **submit_ready: false**
- **Strands closed:** 3 substrate-confirmed honest-zeros (R1 rollback, R2 PDA collision, R3 Rust probes) + 1 round-level engineering_blocker
- **PROP-EVM-MBOX-005 deferred:** cross-layer refund — requires Hardhat fork, not available
- **Do not reopen** without new bounty scope additions, program versions, or explicit Hardhat fork substrate

## Priority candidates

1. **Drift Token-2022 spot path testing** local validator, fee mint collateral vs recorded
2. **next Cantina/Immunefi slug** (operator choice)
3. **Lombard Crucible** if mailbox + bridge instructions get new action coverage
4. **Midas Stream B** validator repro mint_request reject_mint_request

## Carry-forward

- Resolve OnRe human-gate (submit_ready queue)
- Superform submitted 2026-07-01 await triage
- Weekly: platform sync all
- `delivered_vs_promised.json` and round-level engineering_blocker reclassification: now standard practice in all STRAT specs

## Night Shift handoff

- Do not promote candidates without human gate
- Lombard closed acceptable-with-gaps — deprioritize on cron
- Prefer Crucible for Solana invariant fuzz when feasible
- Intel: data/security_results/intel/latest.md

## Blocks

- [ ] Kate: choose next bounty / program for current.md
- [ ] Human-review outstanding submissions (OnRe)
- [ ] Hardhat fork env needed for PROP-EVM-MBOX-005

## Makina carry-over (post-2026-07-05 hard-rule halt)

- **submit_ready: false.** Decision: NO invocation of `/submission-reporting` without fork-verified PoC against deployed bytecode.
- `submission-packs/H5`, `H1`, `H10H11` remain gated on human review (per `current.md` Pre-Human-Gate Screening).
- Fork-probe infrastructure is **durable**: `hermes/scripts/makina_fork_probe_verify.py` + `foundry/src/makina/tests/ForkProbe_H1_H21.t.sol` (3 tests passing) reproduced against `ALCHEMY_API_KEY` at block 25463221.

### Re-queue triggers (any one reopens Makina)

1. New audit-completion event from Ottersec / Cantina / Trail-of-Bits / Spearbit on the same scope.
2. Makina team announcement of v1.3 release.
3. Public bug disclosure from a third-party researcher.

### Deferred attack-surface hypotheses (operator's pick when re-queued)

- **H22 Deep read of `DirectDepositor`:** Even though direct depositor is non-nonReentrant, the real Machines use WETH/USDC tokens (no hooks). Try to instrument a Foundry fork with a malicious mock token to demonstrate H22 does not actually surface in production.
- **H23 Stale-AUM sandwich:** Explicitly OoS by Cantina page. The remaining concrete move is to document the OoS finding text + keep the falsifier as a forensic artifact only.
- **H24 cross-adapter goroutine:** Out-of-scope-adjacent. Build the round-trip fixture between AcrossV3 and CCTPV2 to confirm the "wrong bridge data hash on receiver side" OoS by example.
- **H25 Production-state differential scan:** Need paid Alchemy tier for full-archive `eth_getLogs` with >10-block window — top-up prerequisites on the operator side.

### Outstanding artifacts (keep-local)

- `data/security_results/investigations/2026-07-04-makina-cantina/HUNTING-ARC-HANDOFF.md`
- `data/security_results/lab_notebook/2026-07-05-session-makina-fork-probe.md`
