---
name: night-shift-run
description: Use when running the full NSS security pipeline with Hermes expansion, triage, and optional git push after pytest.
---

# Night Shift Run (Orchestration)

End-to-end scoped run: semantic recon → target-pinned expansion → bounty loop → triage → optional commit.

## Standard v4 target run

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull --ff-only

# 1. Semantic recon when source is available
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug wormhole --repo sources/wormhole/repo --kind bridge

# 2. External expansion (delegate_task)
# Follow hypothesis-expansion skill → target-pinned hermes_proposals/latest.json

# 3. Target-pinned loop
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target wormhole --iterations 1

# 4. Triage latest findings.json under data/security_results/
# Summarize: evidence grade >= 3, reproduction_tier, catalog_analogue, submission_readiness
```

## Full-auto git (SOUL policy)

Only after `.venv/bin/python -m pytest` passes:

```bash
git add -A && git commit -m "nss: <summary> (SPEC v4.2.0)" && git push origin main
```

## Gotchas

- Without `latest.json`, omit `--proposals` for parametric-only run.
- v4.2 submit-ready requires concrete candidate binding, source commit, selector/discriminator, reproduction artifact, measured impact, and existing Python gates; self-interrogation and Solodit analogues are advisory signals only.
- Kamino uses live target harness plus KLend v2 instruction/account artifacts.
- Campaign id in config: `kamino-immunefi-2026-06` — pass to `knowledge --campaign`.
- **x402 RPC:** `solana/x402-proxy/start.sh` → `SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989`. Uses **dedicated** `solana/x402-proxy/.wallet/id.json` (never `~/.config/solana/id.json` / treasury). Needs devnet USDC for credit-drawdown; 1M free credits/mo per wallet. **Human approval required** before Hermes/cron uses wallet RPC (SOUL).
