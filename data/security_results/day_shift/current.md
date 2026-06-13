# Session plan — KLend validator / Wormhole novel
Status: queued

## Objective

Move from catalogue fork replay to program-specific novel reproduction.

## Blocks

- [ ] Block A — KLend oracle/borrow invariant harness (non-catalogue validator seeds)
- [ ] Block B — Wormhole: map live EVM/Solana program IDs (not Nomad proxy analogue)
- [ ] Block C — Score novel candidates; human gate before external submit

## Night Shift handoff

- **Cron OK:** `nss-bounty-loop` daily 04:00 (`fbe84e39c1b1`) — primary + RSI
- **Cron OK:** `nss-investigate-queue` Sun 05:00 weekly (`d5f0875fe76c`) — Kamino depth only
- **Cron OK:** `nss-immunefi-scan` Wed/Sat digest
- **Cron skip (saturated):** aave, euler, kamino, marinade, orca, raydium, wormhole — loop state tracks these
- **Human gate:** `data/security_results/loop/submission_alert.json` on `submit_ready` only