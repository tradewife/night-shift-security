# Night Shift Security — Self-Sustaining Bounty Model

NSS produces rigorous findings; this document describes how realized bounty income compounds into runway, infra, and your yield engine.

## Loop

```
Recon → Validate (grade 3–4) → Bounty score → Submit (human gate) → Payout → Allocate
```

- **Research engine:** Night Shift Security (this repo) — gates unchanged, scoring is additive.
- **Yield engine:** Built separately; consumes `bounty_candidates.jsonl` yield signals.
- **Human gate:** No autonomous Immunefi/Cantina submission (`hermes/SOUL.md`, `submission_alert.json`).

## Profit allocation

Default split on **net bounty payout** (after platform fees / taxes set aside separately):

| Bucket | % | Purpose |
|--------|---|---------|
| **Runway** | 55% | Living expenses, focused research time |
| **Infra** | 25% | x402 RPC credits, archive nodes, Hermes hosting, validator hardware |
| **Yield engine** | 20% | Capital for separate autonomous treasury / monitoring stack |

### Triggers (rebalance quarterly or on payout)

| Condition | Action |
|-----------|--------|
| Runway < 8 weeks | 70% runway / 20% infra / 10% yield until buffer restored |
| Runway ≥ 12 weeks **and** infra funded 3 months ahead | 45% runway / 25% infra / 30% yield |
| Payout < $5k | 80% runway / 20% infra / 0% yield |
| Payout ≥ $50k | Hold 10% infra reserve off-top, then default split on remainder |

Until first payout: **zero burn** operating mode. Do not pre-fund yield engine from runway.

## Operating mode (near-zero burn)

| Activity | Cost profile |
|----------|--------------|
| Shoestring scans | Zero RPC (`scan --platform all`) |
| Validator replay | x402 free tier (`solana/x402-proxy/`) |
| **Primary cron** | `nss-hipif-chain` daily 04:00 — full bounty-depth chain |
| Deterministic fallback | `nss-hipif-chain-run.py` — no OAuth, same depth profile |
| Submit strategy | Fewer, higher-confidence packs (`submission_recommendation: submit_now`) |

Deprecated standalone crons (`nss-bounty-loop`, `nss-investigate-queue`) are absorbed into HIPIF.

## Scoring outputs

| Artifact | Path |
|----------|------|
| Ranked candidates | `data/security_results/bounty/bounty_candidates.jsonl` |
| Submissions + scores | `data/security_results/bounty/submissions.json` |
| Unified screen | `data/security_results/bounty_scan/latest.json` |
| Loop state | `data/security_results/loop/state.json` |

Commands: `BOUNTY_RUN.md` §6 (scoring), §10 (bounty loop), §12 (bounty-depth).

## Current status (2026-06-14)

- **0 payouts** — 0 `submit_ready` findings; gates working as designed
- Latest bounty-depth run: ~54 min, 131 Wormhole fork repros, no submittable novel exploit
- Next: KLend measured delta, Wormhole CPCV grade 3+ (see `AUDIT.md`)