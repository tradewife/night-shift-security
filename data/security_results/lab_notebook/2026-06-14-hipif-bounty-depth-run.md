# Lab entry — HIPIF bounty-depth chain

- wall_time_s: 5603
- bounty_depth: NSS_HIPIF_BOUNTY_DEPTH=1
- klend_live: NSS_KLEND_FIXTURE=0

## Folded history

- **bootstrap**: context loaded — bounty depth profile depth=bounty
- **scan_all**: scan complete artifact=bounty_scan/latest.json
- **depth_wormhole**: wormhole depth (wormhole) 12 trials slug=wormhole trials=12 fork_reproduced=69 solana_reproduced=0 findings=13 label=wormhole
- **depth_wormhole_bridge**: wormhole core/token_bridge refinement trials=4 mode=triage_proposals proposals=True slug=wormhole fork_reproduced=60 findings=13 targets=wormhole-core-ethereum,wormhole-token-bridge-ethereum
- **kamino_preflight**: kamino live preflight configured=True available=True validator_installed=True validator_ready=True env_vars=['SOLANA_MAINNET_RPC_URL', 'SOLANA_RPC_URL', 'SOLANA_USE_VALIDATOR']
- **depth_kamino**: kamino depth (kamino) 5 trials slug=kamino trials=5 fork_reproduced=0 solana_reproduced=104 findings=39 label=kamino
- **cantina_slates**: cantina slates (4 programs) slates=[{'slug': 'reserve-protocol', 'trials': 3, 'fork_reproduced': 76, 'solana_reproduced': 0, 'findings': 33, 'label': 'cantina-reserve-protocol'}, {'slug': 'coinbase', 'trials': 3, 'fork_reproduced': 57, 'solana_reproduced': 0, 'findings': 28, 'label': 'cantina-coinbase'}, {'slug': 'morpho', 'trials': 3, 'fork_reproduced': 97, 'solana_reproduced': 0, 'findings': 19, 'label': 'cantina-morpho'}, {'slug': 'euler', 'trials': 3, 'fork_reproduced': 96, 'solana_reproduced': 0, 'findings': 18, 'label': 'cantina-euler'}] count=4
- **hunt_rotation**: multi-target hunt rotation targets_requested=4 trials_each=3 slugs=['wormhole', 'morpho', 'euler', 'ethena'] fork_ready_only=True ignore_saturation=True wormhole_mode=depth_pin wormhole_fork=60 wormhole_findings=13 morpho_mode=depth_pin morpho_fork=99 morpho_findings=21 euler_mode=depth_pin euler_fork=99 euler_findings=21 ethena_mode=proposals ethena_fork=0 ethena_findings=54 last_slug=ethena fork_reproduced=0 findings=54
- **rsi_fold**: RSI aggregated refinement_queue=11
- **refine_conditional**: refinement 3 passes count=3
- **coordinator_conditional**: coordinator depth cycles=2
- **journal_fold**: lab notebook path=2026-06-14-hipif-bounty-depth-run.md elapsed_s=5602
- **gate**: submit_ready=False elapsed_s=5602 chain_status=complete

## Last pipeline
- slug: morpho
- fork_reproduced: 98
- solana_reproduced: 0
- findings: 20
- submit_ready: False
