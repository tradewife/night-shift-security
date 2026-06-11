# Lab entry — 2026-06-11

## Trigger
Day Shift session: `2026-06-11-kamino-campaign` (resume)

## Scan queue (Immunefi shoestring)
- kamino: grade 4, submission_ready=true, analogue=mango-markets-2022 ($1.5M max bounty)
- raydium: grade 4, analogue=crema-finance-2022
- orca: grade 4, analogue=crema-finance-2022

## Investigated
- Kamino coordinator **cycle 9** — mission `393df7c3` (reentrancy second-pass, proposals `kamino-refinement-20260611-025356.json`)
- Grant-demo exports: `solend-whale-2022`, `cashio-2022` (validator + x402 proxy)

## Delegate proposals vs last run
- Reentrancy refinement: 2 variants (`llm_reentrancy_0_*` ingested)
- Rediscovery on cycle 9: `cream-finance-2021`, `euler-finance-2023` (reentrancy analogues)

## Engine outcome
- Cycle 9: 32 evaluated, 31 passed, 4 findings promoted, max pipeline grade 1, shoestring grade 4 on fixture
- Campaign totals: **9 missions**, 405 store records (post-cycle), deployed_viable 0
- Debrief: `escalate_to_validator` (fixture without deployed_viable)
- Pending missions: **0** — initial Kamino surface sweep complete

## Grant-demo validator packs (per-exploit JSON preserved)
| Exploit | Impact | Template | Grade |
|---------|--------|----------|-------|
| mango-markets-2022 | $110M | flash_loan_oracle | 4 (prior session) |
| solend-whale-2022 | $25M | governance_capture | 4 |
| cashio-2022 | $52M | access_control_escalation | 4 |

## Same vs different
**Different** from 2026-06-10 cycles 1–8: cycle 9 closed last pending reentrancy mission; grant-demo added Solend/Cashio validator exports. Kamino shoestring pack still mango analogue (NSS-0001 fixture).

## Gotchas
- Sequential `nss-grant-demo-submission.py` runs **overwrite** shared `bounty/immunefi/NSS-0001.*` — canonical per-anchor artifacts live under `grant_demo/<exploit-id>/findings.json`
- x402 proxy must be running (`solana/x402-proxy/start.sh`) — Solend export failed with proxy down

## Night Shift handoff
- Cron OK: Raydium/Orca cross-target investigate (Kamino catalogue saturated at shoestring); immunefi scan refresh
- Cron skip: Kamino coordinator refinement (9 missions retired); validator replay anchors (all three strict-pass)
- Open questions for Kate: external Immunefi submit anchor — Mango ($110M) vs Cashio ($52M) vs Solend ($25M)