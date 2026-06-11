# Lab entry — 2026-06-11

## Trigger
Day Shift session: `2026-06-11-immunefi-draft` (manual)

## Investigated
- Anchor: **mango-markets-2022** — strict validator replay → Immunefi draft pack
- Script: `hermes/scripts/nss-grant-demo-submission.py`
- Export: `data/security_results/bounty/immunefi/NSS-0001.{md,json,_repro.sh}`

## Engine outcome
- Findings: 1 | max grade: 4 (root_cause_artifacts) | catalog analogue
- `solana_reproduced`: true | method: `solana_validator`
- Impact: $110M | severity: Critical
- manifest `pack_count`: 1

## Same vs different
**Different** from prior Night Shift runs: first **grant-demo Immunefi export** wired through catalog seed + validator + shoestring regrade (fixes grade-1 export gap). Repro script now documents x402 proxy default (`127.0.0.1:18989`).

## Pack review (Block C)
- Markdown: complete sections (severity, vector, steps, mitigations, lab vs deployed)
- JSON: metadata + severity_justification present
- Repro: `NSS-0001_repro.sh` sets `SOLANA_EXPLOIT_ID`, `SOLANA_USE_VALIDATOR`, default x402 RPC URL
- Human gate: **no external Immunefi post** — internal draft only

## Night Shift handoff
- Cron OK: Kamino coordinator; immunefi scan; cross-target investigate (Raydium/Orca/Marinade)
- Cron skip: validator replay for solend/cashio/mango anchors (strict-pass 2026-06-11)
- Open questions for Kate: confirm Mango vs Solend/Cashio for first **external** submission

## Gotchas
- `immunefi_packs: 0` if shoestring regrade omitted — script must call `shoestring_evidence_grade_candidate` after validator pass
- x402 proxy must be running before validator clone (`solana/x402-proxy/start.sh`)