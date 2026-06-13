# Session plan — next (post–bounty-loop audit)
Status: queued

## Objective

Day Shift escape hatch when cron loop stalls on catalogue analogues: KLend validator harness or Wormhole program-specific IDs.

## Blocks

- [ ] Block A — KLend oracle/borrow invariant harness (non-catalogue validator seeds)
- [ ] Block B — Wormhole live program map (EVM + Solana; not Nomad proxy)
- [ ] Block C — If loop hits `submit_ready`, triage `submission_alert.json` before external post

## Night Shift handoff

- Bounty loop owns daily cross-platform rotation + RSI; investigate-queue weekly for Kamino only
- Day Shift does not repeat saturated assays in `loop/state.json`
- Intel: `data/security_results/intel/latest.md`