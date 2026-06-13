# Lab notebook — Live KLend validator + Wormhole triage expansion

**Date:** 2026-06-13

## Live KLend validator (Block A complete)

```bash
set -a && source .env && set +a
NSS_KLEND_FIXTURE=0 SOLANA_EXPLOIT_ID=kamino-klend python solana/run_klend_harness.py
```

**Result:** `SOLANA_VALIDATOR_PASS:1` — cloned KLend + KVault + oracle on local validator (Alchemy RPC). `SLOT_CURRENT:0` (fresh ledger; programs verified).

Pipeline with live harness (`kamino_klend.json`, rediscovery off): 35 findings, **NSS-0003** novel — `solana_validator`, `balance_verified`, grade **1** (CPCV/PBO still blocks 3+).

## Wormhole scoped expansion

- New: `triage/wormhole_proposals.py`, `nss-write-wormhole-triage-proposals.py`
- **15 proposals** from triage score ≥5 (`wormhole-triage-20260613-071755.json`)
- Fixed `target_config.resolve_target_states` — recon `max_bounty_usd` no longer breaks `ContractState`
- Pipeline: `wormhole_shoestring.json` + `--proposals latest.json` → **13 findings**

## Novel gate (combined)

```bash
novel score --input kamino_klend_findings.json --input wormhole_triage_findings.json
```

**44 novel**, **0 submit_ready** — Kate gate: continue hunt.

## Tests

283 passed, 3 skipped

## Next

- CPCV grade 3+ on novel KLend (PBO / template exploit count)
- Wormhole fork replay on core/token_bridge (not Nomad catalogue only)
- Hermes `hypothesis-expansion` with triage `ranked_file` context for Night Shift