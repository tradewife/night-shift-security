# Lab entry — HIPIF bounty-depth chain

- wall_time_s: 4820
- bounty_depth: NSS_HIPIF_BOUNTY_DEPTH=1
- klend_live: NSS_KLEND_FIXTURE=0

## Folded history

- **bootstrap**: context loaded — bounty depth profile depth=bounty
- **scan_all**: scan complete + v4 semantic recon artifact=bounty_scan/latest.json semantic={'slug': 'wormhole', 'semantic_recon': 'ok', 'entrypoints': 606, 'candidate_count': 559, 'source_commit': '48258bc67e578830f47d28bd608323a72b11612c'}
- **depth_wormhole**: wormhole depth (wormhole) 12 trials slug=wormhole trials=12 fork_reproduced=70 solana_reproduced=0 findings=13 label=wormhole
- **kamino_preflight**: kamino live preflight configured=True available=True validator_installed=True validator_ready=True env_vars=['SOLANA_MAINNET_RPC_URL', 'SOLANA_RPC_URL', 'SOLANA_USE_VALIDATOR']
- **depth_kamino**: kamino depth (kamino) 5 trials slug=kamino trials=5 fork_reproduced=0 solana_reproduced=110 findings=38 label=kamino
- **cantina_slates**: cantina slates (4 programs) slates=[{'slug': 'reserve-protocol', 'trials': 3, 'fork_reproduced': 75, 'solana_reproduced': 0, 'findings': 30, 'label': 'cantina-reserve-protocol'}, {'slug': 'coinbase', 'trials': 3, 'fork_reproduced': 57, 'solana_reproduced': 0, 'findings': 28, 'label': 'cantina-coinbase'}, {'slug': 'morpho', 'trials': 3, 'fork_reproduced': 97, 'solana_reproduced': 0, 'findings': 20, 'label': 'cantina-morpho'}, {'slug': 'euler', 'trials': 3, 'fork_reproduced': 100, 'solana_reproduced': 0, 'findings': 22, 'label': 'cantina-euler'}] count=4
- **hunt_rotation**: multi-target hunt rotation targets_requested=4 trials_each=3 slugs=['wormhole', 'morpho', 'euler', 'ethena'] fork_ready_only=True ignore_saturation=True wormhole_mode=depth_pin wormhole_fork=72 wormhole_findings=13 morpho_mode=depth_pin morpho_fork=97 morpho_findings=19 euler_mode=depth_pin euler_fork=98 euler_findings=20 ethena_mode=proposals ethena_fork=0 ethena_findings=50 last_slug=ethena fork_reproduced=0 findings=50
- **rsi_fold**: RSI aggregated refinement_queue=11
- **depth_wormhole_bridge**: wormhole core/token_bridge refinement trials=4 mode=triage_proposals proposals=True slug=wormhole fork_reproduced=20 findings=13 targets=wormhole-core-ethereum,wormhole-token-bridge-ethereum
- **refine_conditional**: refinement 3 passes count=3
- **coordinator_conditional**: coordinator depth cycles=2

## Last pipeline
- slug: euler
- fork_reproduced: 100
- solana_reproduced: 0
- findings: 23
- submit_ready: False
