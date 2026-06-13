# Lab entry — bounty-loop Cantina verify (pendle)

## Trigger
Manual verify post v3.0.9: `NSS_LOOP_DEPTH_SLUG=pendle hermes/scripts/nss-bounty-loop.sh --iterations 1`

## Run
- slug: pendle
- platform: cantina
- config: `data/security_results/loop/configs/pendle-loop.json` (base `euler_cantina.json`)
- wall time: ~31s (pipeline logged 6s)
- findings: 30
- fork confirmed: **3/3** (catalogue EVM anchors: euler, nomad, wormhole)
- fork_reproduced: 0
- foundry confirmed: 1/2
- best_recommendation: hold (catalogue analogues + grade 1)

## vs pre-fix Pendle cron
| | Pre-fix | This run |
|---|---------|----------|
| fork confirmed | 0/0 | 3/3 |
| fork_reproduced | 0 | 0 |
| pipeline time | ~1s | 6s |
| config base | kamino_klend (wrong) | euler_cantina |

## Interpretation
Config bug is fixed: EVM fork stage runs with `top_n: 3`. Run stays short because there is no `targets/pendle.json` or Pendle live fork harness — forks replay catalogue anchors only, and Pendle `flash_loan_oracle` hypotheses do not reproduce on those contracts. Wormhole depth (~245s) uses `wormhole_triage.json` + live program fork targets.

## Next depth for Cantina
Add Pendle mainnet fork targets (recon → `fork_targets.py` + `targets/pendle.json`) to get Morpho-class runtime and live `fork_reproduced` signal.