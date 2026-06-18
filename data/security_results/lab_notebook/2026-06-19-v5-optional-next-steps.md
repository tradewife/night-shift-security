# v5 optional next steps — 2026-06-19

## Morpho Blue liquid-market promotion

- Switched probe market to USDC/cbBTC `0x64d65c9a…` (~$266M supply).
- `MorphoBlueMeasure.t.sol`: dynamic fork blocks, `MarketState` struct, env overrides.
- Capture: `measured_impact=true`, supply delta `2564241898730`, borrow delta `320936104`.
- Manifest: `morpho_blue: ready`, `ready_count=7`.

## Solana semantic maps (G3)

| Slug | Candidates | Repo |
|------|------------|------|
| jito | 523 | `sources/jito/repo` (stakenet) |
| raydium | 239 | `sources/raydium/repo` |
| orca | 475 | `sources/orca/repo/programs/whirlpool` |
| kamino | 163 | (rebuilt) |
| wormhole | 559 | (rebuilt) |
| uniswap_v4 | 66 | (rebuilt) |

**Note:** Orca/Jito need semantic map **without** `--kind amm|staking` filter (Solana entrypoints lack those tokens). Rebuilt store sequentially after parallel-write race (`2025` total rows).

## Cron / discovery env

- `.env` / `.env.example`: `NSS_PREFER_SOLANA=1`, `NSS_DISCOVERY_MISSING_PCT=0.8`.
- `OPERATOR_APPLY.md` + `jobs.example.yaml` documented.
- Dryrun: `pause_for_native=0`, `bounty_depth=1`, `script_timeout=10800`.

## Code fixes

- `pick_next_target_v6_phase4`: fallback `programs` key; saturated + cooldown parity with legacy picker.
- Tests: morpho promotion assertion; phase4-off for legacy ready-vs-built test.

## Tests

`682 passed, 3 skipped`

## Still open (G5)

`submit_ready=0` — hunt depth, not a manual blocker.