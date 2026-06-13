# Lab notebook — Wormhole triage + Block C + KLend depth

**Date:** 2026-06-13

## Step 1 — Wormhole repo triage

- Cloned `sources/wormhole/repo` (sparse: `solana/`, `ethereum/`, depth 1)
- `triage files`: 121 files ≥4 / 202 total
- `triage wormhole-map --repo`: **149** discovered IDs merged into `sources/wormhole/recon.json`
- `triage patches`: 1 security-shaped commit (encoding fix for binary git objects)

Top-ranked paths: `solana/modules/token_bridge/*`, `ethereum/contracts/*`.

## Step 2 — Block C novel gate

- New: `orchestration/novel_gate.py`, CLI `novel score`
- Report: `data/security_results/novel/human_gate.json`
- Kamino KLend run (`kamino_klend.json`): **38 novel**, **0 submit_ready**
- Kate action: continue hunt — no external post without grade ≥4 + gates

Best novel KLend finding **NSS-0003**: `catalog_analogue=false`, `reproduction_tier=solana_validator`, `balance_verified=true`, grade 1 (CPCV not at 3+).

## Step 3 — KLend harness depth

- `solana/klend_probes.py` — 4 invariant probes (oracle staleness, flash loop, reserve isolation, liquidation)
- `NSS_KLEND_DEPTH=1` runs all probes in fixture CI
- `reality_check`: `solana_klend_harness` + balance verified → `solana_validator` tier
- `kamino_klend.json`: rediscovery disabled (no mango catalogue tag on novel path)

## Tests

278 passed, 5 skipped (+4 new)

## Open

- CPCV pass needed for grade 3+ on novel KLend candidates
- Live validator path (`NSS_KLEND_FIXTURE=0` + RPC) for deployed replay
- Wormhole: scoped `hypothesis-expansion` on triage files ≥4

## Gotchas

- Wormhole clone lives at `sources/wormhole/repo` (gitignored)
- NSS-0001 still has legacy `rediscovered_exploit_id` from prior store merge — NSS-0003+ are clean novel