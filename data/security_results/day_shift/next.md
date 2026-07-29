# Next session queue

**v6.64.1 closed.** Polymarket session 4 closed: continuation cross-layer probe confirmation — 22/22 existing tests pass, no new unprivileged Critical/High/Medium theft path found. `submit_ready=0`. Polymarket arc fully exhausted across all 4 sessions.

## Priority queue

### 1. Rotate to alternate (RECOMMENDED — Polymarket arc exhausted)
| Rank | Target | Action |
|------|--------|--------|
| 1a | 1inch PROP-023 | Mainnet NFT LOP usage scan → human gate → submission-reporting if accepted |
| 1b | Kamino Scope MEDIUM | Live feed map + bankrun stale-AUM profit PoC |
| 1c | marginfi T22 | Residual fee deposit/withdraw/borrow/liq |
| 1d | Flash Trade | Solana perp markets — structure recon + invariant hunt (MCP tools available) |

### 2. Polymarket — only if scope update or deployed contract change
- PA-09..PA-14 (V1 only): CtfAdapter redeem + split/merge round-trip + NegRisk reportOutcome + indexSet collision + FeeModule cumulative fee + CollateralToken guard.
- **Skip all:** PA-01..08 (vendor + honest-zero), PB-08 (unreachable), V2 combinatorial rounding (informational), BRIDGE_ROLE synthetic Other (admin-gated), Router dead code (unreachable).

### Explicitly do not re-open
- Polymarket PA-01..08 honest-zero (vendor + sessions 2-4)
- Polymarket PB-08 unreachable on 0.8.34
- Makina X-001 / G-004 / X-004 residual eligibility kills
- BitGo / Kiln OOS human-gate DO_NOT_SUBMIT
- Invalid/dup: Silo #83293, Origin #82884, OnRe #82764, Superform
- Critical free-mint honest-zeros already closed (lombard, 1inch core, kamino Priority-0, etc.)

## Local artifacts (not pushed)
- `sources/polymarket/ctf-exchange-v2/src/test/V2CombinatorialInvariant.t.sol` (9 tests, 9/9 PASS)
- `data/security_results/investigations/2026-07-29-polymarket-cantina/`
- `data/security_results/lab_notebook/2026-07-30-polymarket-cantina-session4-continuation.md`
