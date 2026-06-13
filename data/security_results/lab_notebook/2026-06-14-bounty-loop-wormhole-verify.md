# Lab entry — bounty-loop depth verify (wormhole)

## Trigger
Manual verify post v3.0.9 fix: `NSS_LOOP_DEPTH_SLUG=wormhole hermes/scripts/nss-bounty-loop.sh --iterations 1`

## Run
- slug: wormhole
- platform: immunefi
- wall time: ~4m17s (pipeline logged 245s)
- findings: 13
- fork_reproduced: 47
- fork confirmed: 41/41 (live EVM targets incl. wormhole-core/token-bridge/pauser)
- solana_reproduced: 0
- best_recommendation: hold (grade 1 survivors; no submit_ready)
- depth_pass: wormhole

## vs broken Pendle run (pre-fix)
- Pendle: ~1s, fork 0/0, fork_reproduced 0
- Wormhole depth: minutes, fork 41/41, fork_reproduced 47

## Notes
Fix confirmed: loop now runs mainnet fork validation when depth slug or EVM config applies. RSI queued refinement on access_control_escalation; wormhole remains in saturated_slugs.