# Night Shift Security — Self-Sustaining Bounty Model

NSS produces rigorous findings; this document describes how realized bounty income compounds into runway, infra, and your yield engine.

## Loop

```
Recon → Validate (grade 3–4) → Bounty score → Submit (human gate) → Payout → Allocate
```

- **Research engine:** Night Shift Security (this repo) — gates unchanged, scoring is additive.
- **Yield engine:** You build separately; consumes `bounty_candidates.jsonl` yield signals.
- **Human gate:** No autonomous Immunefi/Cantina submission (Hermes SOUL).

## Profit allocation (TBD after first payout)

| Bucket | Purpose | Placeholder % |
|--------|---------|---------------|
| Runway | Your time / living expenses | TBD |
| Infra | x402 RPC, Hermes hosting, validator slices | TBD |
| Yield engine | Autonomous treasury / monitoring capital | TBD |

Tune split when first payout lands. Conservative default until then: prioritize runway until 8–12 weeks buffer, then fund infra + yield engine.

## Operating mode (near-zero burn)

- Shoestring scans: zero RPC (`scan --platform all`)
- Validator replay: x402 free tier (`solana/x402-proxy/`)
- Hermes cron: scan + investigate queue (no duplicate Day Shift assays)
- Submit **fewer, higher-confidence** packs (`submission_recommendation: submit_now`)

## Scoring outputs

| Artifact | Path |
|----------|------|
| Ranked candidates | `data/security_results/bounty/bounty_candidates.jsonl` |
| Submissions + scores | `data/security_results/bounty/submissions.json` |
| Unified screen | `data/security_results/bounty_scan/latest.json` |

See `BOUNTY_RUN.md` §9 for commands.