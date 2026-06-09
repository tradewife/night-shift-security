# Bounty Run Guide — Zero-Budget Night Shift Security

Exact command sequences for Immunefi-ready research runs without paid API spend.

## Prerequisites

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd foundry && ./setup.sh && forge test
cd ../solana && ./setup.sh
```

## 1. Default CI / zero-cost baseline (LLM off)

Parametric hypothesis expansion only — no API keys required.

```bash
.venv/bin/python -m night_shift_security.cli.main run
.venv/bin/python -m pytest   # 157+ tests
```

Config: `src/night_shift_security/config/default.json` (`llm_expansion.enabled: false`).

## 2. Grok / Hermes OAuth (preferred quality, still $0)

Uses existing Grok CLI OAuth session (`~/.grok/auth.json`) or `XAI_API_KEY` when set.

```bash
# Optional explicit key (overrides OAuth)
export XAI_API_KEY="xai-..."

.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/grok.json run
```

Credential resolution order: `config.api_key` → `XAI_API_KEY` → Grok OAuth → Hermes OAuth.

## 3. Local Ollama (fully offline LLM)

```bash
ollama pull llama3.1:8b
ollama serve   # default http://localhost:11434

.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/ollama.json run
```

Requires `pip install -e ".[llm]"` for LiteLLM.

## 4. Live-target harness (scoped protocol run)

Point the engine at a single catalog anchor with fork/validator replay:

```bash
# Solend governance anchor (fixture CI path)
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/target_run.json run

# Other bundled targets (edit config_path or use inline target block):
#   src/night_shift_security/config/targets/solend-whale-2022.json
#   src/night_shift_security/config/targets/cashio-2022.json
#   src/night_shift_security/config/targets/euler-finance-2023.json
```

Enable in any config:

```json
"target": {
  "enabled": true,
  "config_path": "targets/cashio-2022.json"
}
```

## 5. Immunefi submission packs

After a pipeline run, export or re-export bounty artifacts:

```bash
RUN_JSON=data/security_results/2026-06-08/findings.json

# Standard bounty JSON + Immunefi markdown/repro packs (grade >= 3)
.venv/bin/python -m night_shift_security.cli.main bounty \
  --input "$RUN_JSON" --immunefi

# Immunefi packs only
.venv/bin/python -m night_shift_security.cli.main immunefi \
  --input "$RUN_JSON" --min-evidence-grade 3
```

Outputs:

| Path | Contents |
|------|----------|
| `data/security_results/bounty/submissions.json` | Structured bounty submissions |
| `data/security_results/bounty/immunefi/manifest.json` | Pack index |
| `data/security_results/bounty/immunefi/NSS-*.md` | Immunefi-style report |
| `data/security_results/bounty/immunefi/NSS-*_repro.{sh,sol}` | Reproduction script template |
| `data/security_results/knowledge/findings_store.jsonl` | Lineage + gate outcomes |

## 6. Shoestring submission (zero RPC — grant-pending)

Polish a single Level 4 pack using fixture replay only. No paid RPC, no validator clone.

```bash
# Full scoped run (Crema anchor, fork validation off)
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/shoestring.json run

# Or export from an existing run JSON
RUN_JSON=data/security_results/2026-06-08/findings.json
.venv/bin/python -m night_shift_security.cli.main submission --input "$RUN_JSON"
```

Outputs under `data/security_results/bounty/shoestring/<exploit-id>/`:

| File | Purpose |
|------|---------|
| `README.md` | Triage summary + zero-cost repro instructions |
| `NSS-*.md` | Immunefi-style report (catalog-grounded) |
| `NSS-*_repro.sh` | Runnable fixture script (no RPC) |
| `../manifest.json` | Selected finding metadata |

Verify reproduction (free):

```bash
./data/security_results/bounty/shoestring/crema-finance-2022/NSS-*_repro.sh
```

Swap target in `shoestring.json` → `targets/solend-whale-2022.json` or `cashio-2022.json`.

## 7. Immunefi scan → investigate queue (zero RPC)

Scan ranks **all 12 curated programs**; top targets get full pipeline runs (Kamino only if scan ranks it).

```bash
# Lightweight scan (all curated Solana programs)
.venv/bin/python -m night_shift_security.cli.main scan --ecosystem solana --min-bounty 250000

# Preview who gets investigated next
.venv/bin/python -m night_shift_security.cli.main investigate --dry-run --top 2 --ecosystem solana

# Full deep-dive on top 2 from latest scan (--proposals is global, before subcommand)
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  investigate --top 2 --ecosystem solana
```

Hermes cron `nss-investigate-queue` automates: scan → delegate expansion → investigate top N.

## 7b. Immunefi bounty scan (zero RPC)

Probe curated live Immunefi programs against catalog analogues — no mainnet, no spend.

```bash
# List curated Solana programs (213 total on Immunefi; 12 curated in registry)
.venv/bin/python -m night_shift_security.cli.main scan --list --ecosystem solana

# Run engine scan (all curated programs)
.venv/bin/python -m night_shift_security.cli.main scan

# Solana-only, min $250k max bounty
.venv/bin/python -m night_shift_security.cli.main scan --ecosystem solana --min-bounty 250000
```

Reports: `data/security_results/immunefi_scan/latest.json` + `latest.md`

Top Solana targets as of 2026-06-09: **Kamino** ($1.5M), **Raydium** ($505k), **Orca** ($500k), **Marinade** ($250k).

### Kamino shoestring run (highest-priority live target)

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json run
```

Uses `targets/kamino.json` — KLend program + mango-markets-2022 catalogue analogue for zero-RPC fixture replay. Outputs shoestring pack under `bounty/shoestring/kamino/`.

## 8. Grant-demo strict reproduction (when RPC budget lands)

**EVM fork** (Euler, Nomad):

```bash
export ETHEREUM_RPC_URL=<your-mainnet-rpc>
cd foundry && forge test --match-contract Fork
```

**Solana validator clone** (Solend, Cashio):

```bash
export SOLANA_MAINNET_RPC_URL=<your-mainnet-rpc>
export SOLANA_USE_VALIDATOR=1
SOLANA_EXPLOIT_ID=solend-whale-2022 ./solana/run_validator_test.sh
```

## Evidence grades (what bounty triage cares about)

| Level | Label | Signal |
|-------|-------|--------|
| 3 | reproduced | `fork_reproduced` or `solana_reproduced` |
| 4 | root_cause_artifacts | Level 3 + invariant violations + reproduction steps + impact |

Immunefi pack export defaults to `min_evidence_grade: 3`. Shoestring mode defaults to `4`.

## 9. Hermes autonomous runs (outer loop)

NSS uses a dedicated Hermes profile `night-shift` for scheduled orchestration. Hypothesis expansion runs via `delegate_task` subagents (Grok OAuth); the Python pipeline ingests proposals through `llm_expansion.provider: external`.

### Install profile

```bash
./hermes/install-profile.sh
hermes --profile night-shift doctor
hermes gateway install   # optional: enable cron scheduler
```

Prerequisite: Grok OAuth at `~/.grok/auth.json`.

### Manual agent session

```bash
cd /home/kt/projects/rtp/night-shift-security
hermes --profile night-shift
# Follow hypothesis-expansion → night-shift-run skills in hermes/skills/
```

### Kamino run with external proposals

```bash
# After Hermes writes data/security_results/hermes_proposals/latest.json:
.venv/bin/python -m night_shift_security.cli.main \
  --config src/night_shift_security/config/kamino_shoestring.json \
  --proposals data/security_results/hermes_proposals/latest.json \
  run
```

### Cron jobs (local delivery)

See `hermes/cron/jobs.example.yaml`. Example:

```bash
hermes --profile night-shift cron create "every 6h" \
  --no-agent --script nss-health.sh --name nss-health \
  --workdir /home/kt/projects/rtp/night-shift-security --deliver local

hermes --profile night-shift cron create "0 3 * * 3" \
  "Kamino shoestring: hypothesis-expansion then night-shift-run per skills" \
  --skill hypothesis-expansion --skill night-shift-run --name nss-kamino-shoestring \
  --workdir /home/kt/projects/rtp/night-shift-security --deliver local
```

LiteLLM in-pipeline expansion (`grok.json`) remains for manual/ad-hoc runs. Hermes cron uses the external proposals bridge only.

---

*STFU and Build. Brutal validation over hype.*