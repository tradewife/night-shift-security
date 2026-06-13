# Lab entry — 2026-06-13

## Trigger
Day Shift: Alchemy archive RPC wired; continue Euler/Wormhole fork validation.

## RPC
- `ETHEREUM_RPC_URL` via Alchemy (`.env`, gitignored)
- Archive verified: WETH bytecode at Euler block 16,825,925

## Fix
Stale fork contract addresses corrected:
- Euler EVC: `0x27182842E098f60e3D576794A5bFFb0777E025d3`
- Nomad bridge router: `0x88A69B4E698A4B090DF6CF5Bd7B2D47325Ad30A3`
- `foundry/test/ForkHistorical.t.sol` + `fork_targets.py` + euler target JSONs

## Pipeline runs

| Campaign | Findings | fork_reproduced | deployed_viable | Shoestring |
|----------|----------|-----------------|-----------------|------------|
| `euler-cantina-2026-06` | 18 | 18 | 18 | `bounty/shoestring/euler/` NSS-0002 |
| `wormhole-fork-2026-06` | 13 | 13 | 13 | `bounty/shoestring/wormhole/` NSS-0003 |

Foundry `ForkHistoricalTest`: 4/4 pass with live Alchemy RPC.

## Same vs different
**Different:** First live EVM `fork_reproduced` + `deployed_viable` on Euler and Wormhole-framed Nomad analogue. Fork scoring bonus applied (×1.2).

**Same:** Still catalogue analogue anchors (`euler-finance-2023`, `nomad-bridge-2022`) — Kate gate on external Immunefi submit unchanged. Evidence grade still low (1) on wormhole top pick; Euler packs at grade 3+.

## Night Shift handoff
- Cron skip: Euler/Wormhole fork re-runs (completed)
- Cron OK: scan refresh; novel KLend harness
- Blocker cleared: archive `ETHEREUM_RPC_URL`

## Next action
KLend-specific validator seeds or program-specific Wormhole contract (not Nomad proxy) for novel tier.