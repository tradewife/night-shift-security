# Night Shift Security — Operator Cookbook

**Version:** v4.0.0  
**Updated:** 2026-06-15  

Use this file for commands. Use `SPEC.md` for the technical contract and `AUDIT.md` for current gaps.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Load local secrets/RPC when running live depth:

```bash
set -a && source .env && set +a
```

## Tests

Sandbox-safe broad run:

```bash
.venv/bin/python -m pytest -k 'not api_serves_endpoints and not api_paginated_endpoint and not api_auth_rejects_without_key'
```

Focused v4/night-chain checks:

```bash
.venv/bin/python -m pytest \
  tests/test_cantina_scan.py \
  tests/test_bounty_loop.py \
  tests/test_recursive_improvement.py \
  tests/test_hipif.py
```

## Primary Night Chain

Production cron path on this machine:

```text
Hermes profile: nightsoul
Job: nss-hipif-chain
Schedule: daily 04:00
Mode: no-agent
Script: nss-hipif-chain.sh
```

Manual full run:

```bash
set -a && source .env && set +a
export NSS_HIPIF_BOUNTY_DEPTH=1
export NSS_KLEND_FIXTURE=0
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init --phase full
```

Expected runtime: roughly 60-150+ minutes. Latest verified v4 full run took 4820s and completed 13/13 folds with `gate_ok=true`, `submit_ready=false`.

Verify gate:

```bash
.venv/bin/python -m night_shift_security.cli.main hipif status
.venv/bin/python -m night_shift_security.cli.main hipif gate
```

## NightSoul Cron

Install/update profile assets:

```bash
./hermes/install-profile.sh
./hermes/install-nightsoul-overlay.sh
hermes --profile nightsoul doctor
```

Check active jobs:

```bash
hermes --profile nightsoul cron list
```

The primary job must show:

```text
Mode: no-agent (script stdout delivered directly)
Script: nss-hipif-chain.sh
```

If needed, enforce it:

```bash
hermes --profile nightsoul cron edit 343324bfcbb2 \
  --no-agent --clear-skills --script nss-hipif-chain.sh \
  --workdir /home/kt/projects/rtp/night-shift-security
```

## HIPIF Defaults

| Variable | Default |
|----------|---------|
| `NSS_HIPIF_MODE` | deterministic |
| `NSS_HIPIF_BOUNTY_DEPTH` | 1 |
| `NSS_KLEND_FIXTURE` | 0 |
| `NSS_HIPIF_TRIALS_WORMHOLE` | 12 |
| `NSS_HIPIF_WORMHOLE_BRIDGE_TRIALS` | 4 |
| `NSS_HIPIF_TRIALS_KAMINO` | 5 |
| `NSS_HIPIF_CANTINA_SLATES` | uniswap,reserve-protocol,euler,polymarket,coinbase,morpho,pendle,okx,paxos |
| `NSS_HIPIF_CANTINA_TRIALS` | 3 |
| `NSS_HIPIF_HUNT_SLUGS` | kamino,wormhole,morpho,euler,ethena,jito |
| `NSS_HIPIF_HUNT_TRIALS` | 3 |
| `NSS_HIPIF_REFINE_TOP` | 3 |
| `NSS_HIPIF_COORD_CYCLES` | 2 |

dYdX is tracked in the Cantina registry but excluded from default slates until a Cosmos SDK/CometBFT harness exists.

## Single Bounty Loop

Refresh and run one target:

```bash
.venv/bin/python -m night_shift_security.cli.main scan --platform all --min-bounty 250000
.venv/bin/python -m night_shift_security.cli.main bounty loop --target wormhole --iterations 1 --trials 3
```

With proposals, global flags go before the subcommand:

```bash
.venv/bin/python -m night_shift_security.cli.main \
  --proposals data/security_results/hermes_proposals/latest.json \
  bounty loop --target wormhole --iterations 1 --trials 3
```

## Semantic Recon

Wormhole:

```bash
.venv/bin/python -m night_shift_security.cli.main semantic map \
  --slug wormhole --repo sources/wormhole/repo --kind bridge
```

Candidate store:

```bash
data/security_results/knowledge/concrete_candidates.jsonl
```

Generated PoC path:

```bash
.venv/bin/python -m night_shift_security.cli.main poc generate --candidate-id <candidate_id>
.venv/bin/python -m night_shift_security.cli.main poc verify --candidate-id <candidate_id>
```

Generated verifiers are fail-closed until real bindings and measured deltas exist.

## Recursive Improvement

Run manually:

```bash
.venv/bin/python -m night_shift_security.cli.main improve
```

Artifacts:

| Artifact | Purpose |
|----------|---------|
| `data/security_results/knowledge/findings_store.jsonl` | Recorded findings and lineage |
| `data/security_results/knowledge/improvement_ledger.jsonl` | RSI actions |
| `data/security_results/loop/refinement_hints.json` | Top next refinement target |
| `data/security_results/loop/state.json` | cooldowns, saturation, scan boosts, queue |
| `data/security_results/knowledge/failure_signatures.jsonl` | Failure-trace RSI |

RSI is active even when `submit_ready=false`; null submissions still produce findings, fingerprints, queue entries, cooldowns, and scan boosts.

## Platform Intel

```bash
.venv/bin/python -m night_shift_security.cli.main platform sync --all
.venv/bin/python -m night_shift_security.cli.main platform diff
```

Curated current Cantina registry includes Uniswap, Reserve, Euler, Polymarket, Coinbase, Morpho, Pendle, dYdX, Paxos, OKX, and lower-bounty targets.

## Submission Gate

External submission is never autonomous.

`submit_ready` requires:

- `qualifies_for_submission() == true`
- evidence grade >= 4
- deployed viable
- non-catalogue
- credible reproduction
- concrete candidate binding
- source commit and selector/discriminator
- candidate-specific reproduction artifact
- measured non-fee impact

If `data/security_results/loop/submission_alert.json` appears, stop and use `operator-submit` / human review.
