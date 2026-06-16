# Lab entry — Polymarket catalogue-only pass and target config fix

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Polymarket
- config: `src/night_shift_security/config/polymarket_cantina.json`

## Command

```bash
set -a && source .env && set +a
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/polymarket_cantina.json \
  bounty loop --target polymarket --iterations 1 --trials 1
```

## Result

The run completed with live RPC/fork validation:

- `fork_confirmed=61/69`
- `fork_reproduced=30`
- findings: 46
- Immunefi research packs: 2
- `submit_candidates=[]`
- best recommendation: `polish_validator`

The strongest findings were governance-capture candidates:

- `NSS-0007`: evidence grade 4, `catalog_analogue=true`, `qualifies=false`
- `NSS-0008`: evidence grade 4, `catalog_analogue=true`, `qualifies=false`

Most flash-loan/oracle candidates remained `deployed_viable=false` simulation-only Mango analogues.

## System Change

During the run, `polymarket_cantina.json` was found to point at `targets/euler-cantina.json`. `coinbase_cantina.json` had the same stale target path.

Fixed both:

- `polymarket_cantina.json` -> `targets/polymarket.json`
- `coinbase_cantina.json` -> `targets/coinbase.json`

Added minimal target metadata files and a regression test ensuring dedicated Cantina override configs resolve to matching target IDs.

## Decision

No submission candidate. The current Polymarket pass remains catalogue analogue research.

The target-path fix is important because future target-pinned reporting and coordinator state should not inherit Euler metadata for Polymarket or Coinbase runs.
