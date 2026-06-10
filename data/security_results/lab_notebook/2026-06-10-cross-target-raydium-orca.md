# Lab entry — 2026-06-10 (cross-target)

## Trigger
manual: cross-target investigate after Kamino coordinator campaign (exclude Kamino)

## Scan queue (dry-run top 2, exclude kamino)
- raydium: grade 4, submission_ready, analogue=crema-finance-2022, max_bounty $505k
- orca: grade 4, submission_ready, analogue=crema-finance-2022, max_bounty $500k

## Investigated
- raydium: `data/security_results/investigations/raydium-investigate.json`, campaign `immunefi-raydium-2026-06`
- orca: `data/security_results/investigations/orca-investigate.json`, campaign `immunefi-orca-2026-06`
- proposals: `raydium-cross-20260610-144825.json` (4 variants, composability + flash_loan)

## Delegate proposals vs Kamino runs
- Cross-target proposals via `nss-write-scan-proposals.py --slug raydium`
- Templates: composability_risk + flash_loan_oracle (Crema analogue, not Mango)
- LLM expansion ingested: `llm_composability_risk_0_0` etc. in top candidates

## Engine outcome
| Target | Findings | Shoestring pack | Catalogue anchor |
|--------|----------|-----------------|------------------|
| raydium | 29 | `bounty/shoestring/raydium` NSS-0002 | crema-finance-2022 |
| orca | 29 | `bounty/shoestring/orca` NSS-0001 | crema-finance-2022 |

- solana_reproduced: 77 per run | deployed_viable: 0 | catalog_analogue: true
- Rediscovery: crema-finance-2022 among 5/19 gated hits per run

## Same vs different
**Different target** from Kamino (KLend/Mango analogue). Same engine path: shoestring fixture, Crema catalogue anchor, external proposals ingested. Top severity ~0.413 vs Kamino ~0.55 on oracle vectors.

## Next action
- Marinade (#4 scan, Solend analogue) for governance/treasury templates
- Optional: `coordinator init` per cross-target campaign for mission lifecycle
- Grant RPC: validator replay on crema-finance-2022 before any Raydium/Orca submission claim