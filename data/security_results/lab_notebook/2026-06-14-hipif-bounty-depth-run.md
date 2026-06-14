# Lab entry — HIPIF bounty-depth chain

- wall_time_s: 3237
- bounty_depth: NSS_HIPIF_BOUNTY_DEPTH=1
- klend_live: NSS_KLEND_FIXTURE=0

## Folded history

- **bootstrap**: context loaded — bounty depth profile depth=bounty
- **scan_all**: scan complete artifact=bounty_scan/latest.json
- **depth_wormhole**: wormhole depth (wormhole) 12 trials slug=wormhole trials=12 fork_reproduced=71 solana_reproduced=0 findings=13 label=wormhole
- **depth_kamino**: wormhole core/token_bridge refinement trials=4 mode=triage_proposals proposals=True slug=wormhole fork_reproduced=60 findings=13 targets=wormhole-core-ethereum,wormhole-token-bridge-ethereum
- **hunt_rotation**: kamino live preflight configured=True available=True validator_installed=True validator_ready=True env_vars=['SOLANA_MAINNET_RPC_URL', 'SOLANA_RPC_URL', 'SOLANA_USE_VALIDATOR']
- **rsi_fold**: kamino depth (kamino) 5 trials slug=kamino trials=5 fork_reproduced=0 solana_reproduced=106 findings=38 label=kamino
- **refine_conditional**: cantina-pendle depth (pendle) 3 trials slug=pendle trials=3 fork_reproduced=0 solana_reproduced=0 findings=38 label=cantina-pendle
- **coordinator_conditional**: cantina-morpho depth (morpho) 3 trials slug=morpho trials=3 fork_reproduced=98 solana_reproduced=0 findings=21 label=cantina-morpho
- **journal_fold**: cantina-euler depth (euler) 3 trials slug=euler trials=3 fork_reproduced=98 solana_reproduced=0 findings=21 label=cantina-euler
- **gate**: multi-target hunt rotation targets_requested=4 trials_each=3 slugs=['ethena'] fork_ready_only=True ethena_mode=proposals ethena_fork=0 ethena_findings=51 last_slug=ethena fork_reproduced=0 findings=51
- **gate**: RSI aggregated refinement_queue=11
- **gate**: refinement 3 passes count=3
- **gate**: coordinator depth cycles=2

## Last pipeline
- slug: morpho
- fork_reproduced: 98
- solana_reproduced: 0
- findings: 21
- submit_ready: False
