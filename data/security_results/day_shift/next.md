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
