# Lab entry — 2026-06-12

## Trigger
Day Shift: Kate declined Immunefi submit on Kamino catalogue analogue; continue novel-finding hunt.

## Scan refresh
- `scan --platform all --ecosystem solana`: top 4 engine-ready — kamino, raydium, orca, **marinade**
- Excluded saturated: kamino, raydium, orca

## Investigated
- **marinade**: `investigations/marinade-investigate.json`, campaign `immunefi-marinade-2026-06`
- Templates: `governance_capture`, `treasury_drain` (Solend whale catalogue analogue)
- 19 findings, solana_reproduced: 19, deployed_viable: 0

## Validator upgrade
- Solend strict replay via x402 → Marinade-framed pack `bounty/shoestring/marinade/` NSS-0001
- Readiness **0.33** (`polish_validator`) — still catalogue analogue, not novel

## Engine outcome
| Target | Findings | Best template | Anchor | Recommendation |
|--------|----------|---------------|--------|----------------|
| marinade (fixture) | 19 | treasury_drain | solend-whale-2022 | hold (~$8k proxy) |
| marinade (validator) | 1 | governance_capture | solend-whale-2022 | polish_validator (~$12k proxy) |

## Same vs different
**Different** attack surface from Kamino (governance/treasury vs oracle). **Same** methodology limitation: catalogue analogue, no deployed_viable on live program.

## Code
- `targets/marinade.json` added
- `write_report()` persists `live_target` + `campaign_id` in findings.json

## Night Shift handoff
- Cron OK: bounty scan refresh; investigate queue (exclude kamino/raydium/orca/marinade)
- Cron skip: Kamino/Marinade shoestring re-export (Day Shift done)
- Next: coordinator on new surface, Wormhole investigate, or KLend-specific (non-catalogue) research