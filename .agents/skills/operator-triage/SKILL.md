---
name: operator-triage
description: Phase D impact triage — oracle vs DEX divergence, TVS sibling sweep, submission readiness.
---

# Operator Triage

Post-PoC impact sizing and promotion gate. Run after `operator-exploit` when a fork reproduces.

## Step 1 — Oracle arbitrage check

On an active Anvil fork:

```bash
.venv/bin/python -m night_shift_security.cli.main impact oracle \
  --oracle 0x... \
  --getter "latestAnswer()(int256)" \
  --pair 0x... \
  --rpc-url http://127.0.0.1:8545 \
  --threshold-pct 2.0
```

`exploitable: true` when oracle diverges from DEX spot beyond threshold.

## Step 2 — TVS maximization sweep

Rank sibling pools / clone deployments by on-fork liquidity proxy:

```bash
.venv/bin/python -m night_shift_security.cli.main impact tvs \
  --base-pool 0x... \
  --siblings config/wormhole_siblings.json \
  --holder 0x... \
  --rpc-url http://127.0.0.1:8545
```

## Step 3 — Pipeline gates (authoritative)

```bash
.venv/bin/python -m night_shift_security.cli.main bounty score \
  --input data/security_results/findings.json --min-evidence-grade 3
```

Novel candidates still require `DELTA_WEI` / task verifier. MCP/impact output is untrusted until gates pass.

## Step 4 — Checkpoint + human gate

Write `operator-checkpoint` with `impact_usd` estimate and ranked siblings. Stop on `submission_alert.json` — never auto-post externally.

## Gotchas

- Oracle getter signatures vary by feed — confirm ABI on fork
- TVS sweep uses `balanceOf` or `totalSupply` proxy; not full TVL oracle
- Catalogue analogue findings remain exempt from balance verifier