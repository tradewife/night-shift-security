# Lab entry — HIPIF bounty-depth chain

- wall_time_s: 4805
- bounty_depth: NSS_HIPIF_BOUNTY_DEPTH=1
- klend_live: NSS_KLEND_FIXTURE=0

## Folded history

- **bootstrap**: context loaded — bounty depth profile depth=bounty
- **scan_all**: scan complete + v4 semantic recon artifact=bounty_scan/latest.json semantic={'slug': 'wormhole', 'semantic_recon': 'ok', 'entrypoints': 606, 'candidate_count': 559, 'source_commit': '48258bc67e578830f47d28bd608323a72b11612c'}
- **depth_wormhole**: wormhole depth (wormhole) 12 trials slug=wormhole trials=12 fork_reproduced=67 solana_reproduced=0 findings=13 label=wormhole
- **kamino_preflight**: kamino live preflight configured=True available=True validator_installed=True validator_bin=/home/kt/.local/share/solana/install/active_release/bin/solana-test-validator validator_ready=True env_vars=['SOLANA_MAINNET_RPC_URL', 'SOLANA_RPC_URL', 'SOLANA_USE_VALIDATOR']
- **depth_kamino**: kamino depth (kamino) 5 trials slug=kamino trials=5 fork_reproduced=0 solana_reproduced=106 findings=41 label=kamino
- **cantina_slates**: cantina slates (9 programs) slates=[{'slug': 'uniswap', 'trials': 3, 'fork_reproduced': 8, 'solana_reproduced': 0, 'findings': 31, 'label': 'cantina-uniswap'}, {'slug': 'reserve-protocol', 'trials': 3, 'fork_reproduced': 75, 'solana_reproduced': 0, 'findings': 30, 'label': 'cantina-reserve-protocol'}, {'slug': 'euler', 'trials': 3, 'fork_reproduced': 101, 'solana_reproduced': 0, 'findings': 24, 'label': 'cantina-euler'}, {'slug': 'polymarket', 'trials': 3, 'fork_reproduced': 33, 'solana_reproduced': 0, 'findings': 51, 'label': 'cantina-polymarket'}, {'slug': 'coinbase', 'trials': 3, 'fork_reproduced': 57, 'solana_reproduced': 0, 'findings': 27, 'label': 'cantina-coinbase'}, {'slug': 'morpho', 'trials': 3, 'fork_reproduced': 98, 'solana_reproduced': 0, 'findings': 21, 'label': 'cantina-morpho'}, {'slug': 'pendle', 'trials': 3, 'fork_reproduced': 0, 'solana_reproduced': 0, 'findings': 41, 'label': 'cantina-pendle'}, {'slug': 'okx', 'trials': 3, 'fork_reproduced': 57, 'solana_reproduced': 0, 'findings': 26, 'label': 'cantina-okx'}, {'slug': 'paxos', 'trials': 3, 'fork_reproduced': 0, 'solana_reproduced': 0, 'findings': 24, 'label': 'cantina-paxos'}] count=9
- **hunt_rotation**: multi-target hunt rotation targets_requested=4 trials_each=3 slugs=['wormhole', 'morpho', 'euler', 'ethena'] fork_ready_only=True ignore_saturation=True wormhole_mode=depth_pin wormhole_fork=71 wormhole_findings=13 morpho_mode=depth_pin morpho_fork=100 morpho_findings=23 euler_mode=depth_pin euler_fork=95 euler_findings=18 ethena_mode=proposals ethena_fork=0 ethena_findings=52 last_slug=ethena fork_reproduced=0 findings=52
- **rsi_fold**: RSI aggregated refinement_queue=13
- **depth_wormhole_bridge**: wormhole core/token_bridge refinement trials=4 mode=triage_proposals proposals=True slug=wormhole fork_reproduced=10 findings=13 targets=wormhole-core-ethereum,wormhole-token-bridge-ethereum
- **refine_conditional**: refinement 3 passes count=3
- **coordinator_conditional**: coordinator depth cycles=2

## Last pipeline
- slug: euler
- fork_reproduced: 99
- solana_reproduced: 0
- findings: 21
- submit_ready: False
