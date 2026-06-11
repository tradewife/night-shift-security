# Lab notebook — Day Shift bootstrap + Mango validator

**Date:** 2026-06-11  
**Trigger:** Day Shift session (plan approved)  
**Same vs prior:** New operating model; Mango was failing (wrong program id); now strict-pass with siblings Solend/Cashio.

## Shipped — Day Shift ops

- `hermes/DAY_SOUL.md`, skill `day-shift-cycle`
- `data/security_results/day_shift/` (current, next, archive)
- `data/security_results/intel/watchlist.yaml`, `latest.md`
- `AGENTS.md` Day vs Night split; lab-notebook + coordinator handoff Gotchas

## Mango validator fix

**Root cause:** Wrong program pubkey in catalog/profile (`...ATcrPZ96ZFFn7VGk4`).  
**Correct (mango-v4 `declare_id!`):** `4MangoMjqJ2firMokCjjGgoK8d4MXcrgL7XJaL3w6fVg`

| Exploit | SOLANA_VALIDATOR_PASS | SLOT_TARGET | IMPACT_USD |
|---------|----------------------|-------------|------------|
| mango-markets-2022 | 1 | 152000000 | 110M |

All three validator-backed anchors now green via x402 `http://127.0.0.1:18989`.

## Audit

Pass — pytest green with live validator tests; trust boundary unchanged; handoff written in `day_shift/next.md`.

## Night Shift handoff

- Skip re-running solend/cashio/mango validator harness
- OK: Kamino coordinator, immunefi scan, cross-target investigate per scan queue

## Next session

See `data/security_results/day_shift/next.md` — Immunefi submission **draft** (human gate on public post).