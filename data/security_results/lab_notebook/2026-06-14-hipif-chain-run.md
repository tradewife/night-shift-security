# Lab entry — HIPIF chain run (manual)

## Trigger
Manual full chain run (deterministic orchestrator; OAuth not available for agent cron).

## Folded history (10 subgoals)

| Subgoal | Outcome | Key metrics |
|---------|---------|-------------|
| bootstrap | context loaded | ok |
| scan_all | Immunefi+Cantina scan | 18 engine-ready, 4 submission-ready |
| depth_wormhole | triage depth | fork_reproduced=47, findings=13 |
| depth_kamino | KLend depth | solana_reproduced=95, findings=35 |
| hunt_rotation | fresh slug | balancer, fork=4, findings=25 |
| rsi_fold | RSI aggregated | top hint: kamino |
| refine_conditional | proposals + loop | kamino proposals; follow-up ethena loop |
| coordinator_conditional | coordinator cycle | wormhole missions planned |
| journal_fold | this entry | |
| gate | no submit_ready | human_gate_pending=false |

## Refine follow-up (CLI arg fix)
`--proposals` must precede subcommand: picked **ethena** on second refine loop.

## Notes
- Wall time ~2 min (wormhole reused prior 93s run; kamino ~8s)
- Folded context: `data/security_results/hipif/folded_context.json` chain_status=complete
- Agent cron still needs: `hermes --profile night-shift model`