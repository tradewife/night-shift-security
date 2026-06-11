# Lab entry — 2026-06-11

## Trigger
Day Shift session: `2026-06-11-submit-path`

## Submit path decision
- **Primary (Immunefi):** Kamino — $1.5M max, live KLend target, mango-class oracle analogue framed as **live-target risk** (not mango rediscovery).
- **Parallel (Cantina):** Euler — $7.5M max, `euler-finance-2023` catalogue anchor; fork probe blocked on archive RPC.

## Kamino pack
- Regenerated: `data/security_results/bounty/shoestring/kamino/` (NSS-0001)
- Live-target framing in export: title `flash_loan_oracle — Kamino`, Live Target Context section, KLend program ID
- Bounty score (shoestring track): readiness ~0.25, payout proxy ~$56k, recommendation `hold` (catalogue analogue + fixture tier)
- Human gate before external Immunefi post

## Euler Cantina fork probe
- Config: `euler_cantina.json` + `targets/euler-cantina.json`
- Pipeline: 17 findings, `fork_confirmed: 17`, **`fork_reproduced: 0`** (catalog fallback)
- Forge `ForkHistorical` at block 16_825_925: **failed** on public RPCs (no historical state; archive node required)
- Internal pack: `data/security_results/euler_cantina/bounty/shoestring/euler/` (NSS-0004, euler-finance-2023 reentrancy)

## Allocation (#3)
- `SUSTAINABILITY.md` updated: 55% runway / 25% infra / 20% yield engine + rebalance triggers

## Same vs different
**Different** from bounty-scoring session: submit-path chosen, Kamino pack reframed, Euler Cantina config + fork attempt documented, allocation model concrete.

## Gotchas
- Public Ethereum RPCs lack archive state at Euler exploit block — need paid/archive `ETHEREUM_RPC_URL` for `fork_reproduced`
- `findings_from_run_json` now preserves `live_target` from run JSON (required for correct shoestring slug)
- Bounty scoring uses shoestring effective grade for `solana_fixture` tier (pipeline grade 1 → shoestring 4)

## Night Shift handoff
- Cron OK: unified bounty scan; Raydium/Orca investigate; immunefi scan refresh
- Cron skip: Kamino coordinator (9 missions retired); Kamino shoestring re-export (Day Shift done)
- Open questions for Kate: approve Kamino internal draft for Immunefi post; source archive RPC for Euler fork upgrade