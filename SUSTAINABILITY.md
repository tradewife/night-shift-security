# Night Shift Security — Self-Sustaining Bounty Model

NSS produces rigorous findings; this document describes how realized bounty income compounds into runway, infra, and your yield engine.

## Loop

```
Recon → Validate (grade 3–4) → Bounty score → Submit (human gate) → Payout → Allocate
```

- **Research engine:** Night Shift Security (this repo) — gates unchanged, scoring is additive.
- **Yield engine:** You build separately; consumes `bounty_candidates.jsonl` yield signals.
- **Human gate:** No autonomous Immunefi/Cantina submission (Hermes SOUL).

## Profit allocation

Default split on **net bounty payout** (after platform fees / taxes set aside separately):

| Bucket | % | Purpose |
|--------|---|---------|
| **Runway** | 55% | Living expenses, focused research time |
| **Infra** | 25% | x402 RPC credits, archive nodes, Hermes hosting, validator hardware slices |
| **Yield engine** | 20% | Capital for your separate autonomous treasury / monitoring stack |

### Triggers (rebalance quarterly or on payout)

| Condition | Action |
|-----------|--------|
| Runway &lt; 8 weeks | 70% runway / 20% infra / 10% yield until buffer restored |
| Runway ≥ 12 weeks **and** infra funded 3 months ahead | 45% runway / 25% infra / 30% yield |
| Payout &lt; $5k | 80% runway / 20% infra / 0% yield (defer yield until meaningful capital) |
| Payout ≥ $50k | Hold 10% infra reserve off-top, then apply default split on remainder |

Until first payout: **zero burn** operating mode (shoestring scans, x402 free tier). Do not pre-fund yield engine from runway.

## Operating mode (near-zero burn)

- Shoestring scans: zero RPC (`scan --platform all`)
- Validator replay: x402 free tier (`solana/x402-proxy/`)
- Hermes cron: `nss-bounty-loop` daily (primary); weekly Kamino coordinator; no duplicate Day Shift assays
- Submit **fewer, higher-confidence** packs (`submission_recommendation: submit_now`)

## Scoring outputs

| Artifact | Path |
|----------|------|
| Ranked candidates | `data/security_results/bounty/bounty_candidates.jsonl` |
| Submissions + scores | `data/security_results/bounty/submissions.json` |
| Unified screen | `data/security_results/bounty_scan/latest.json` |

See `BOUNTY_RUN.md` §9 for commands.