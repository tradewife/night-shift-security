# Lab notebook — Credible harness gate + live KLend + Wormhole triage

**Date:** 2026-06-13

## 1. Live KLend depth

- `HARNESS_MODE:fixture` — synthetic deltas (CI only)
- `HARNESS_MODE:live_deploy_verified` — programs cloned, **no** fake `DELTA_LAMPORTS`
- `HARNESS_MODE:live_executed` — only when probe tx produces measured delta (not wired yet)
- `kamino_klend.json`: `klend_require_live: true`

Live run:

```bash
set -a && source .env && set +a
NSS_KLEND_FIXTURE=0 python solana/run_klend_harness.py
# → live_deploy_verified, PROBE_EXECUTED:0
```

Pipeline (live): NSS-0001 grade **1**, `harness_mode=live_deploy_verified`, `solana_reproduced=false`

## 2. Submission gate tightened

- `is_credible_klend_harness_evidence()` — blocks fixture + deploy-only from `submit_ready`
- `qualifies_for_submission()` + `finding_balance_verified()` enforce credible reproduction
- Novel gate status: `hold_synthetic_harness`

**Combined novel score: 45 novel, 0 submit_ready** (correct — no false positives)

## 3. Wormhole triage → code

- `wormhole_triage.json` + 15 proposals from `nss-write-wormhole-triage-proposals.py`
- `rediscovery: false` — no Nomad catalogue tagging
- Live fork: `wormhole-live-core` / `token_bridge`, `catalog_analogue=false`
- 13 findings; grade 1 (bytecode smoke + triage hypotheses — not submittable)

## Tests

289 passed, 3 skipped

## Next

- Wire KLend CPI probe txs in `klend_live_probes.py` for `live_executed`
- Wormhole: code review on triage-ranked `token_bridge` / `core` files → manual PoC path