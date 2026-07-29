# Next session queue

**v6.64.0 closed.** Polymarket session 3 closed: V2 source recovered via Sourcify + 7+ layer audit regression with no unprivileged Critical/High/Medium theft path. `submit_ready=0`. Track A + Track B both exhausted on this run.

## Priority queue

### 1. Polymarket deep edge probing (only if operator wishes more Polymarket coverage)
- **AutoRedeemer multi-position batch under collateral balance diff replay.**
- **BaseMigrationMixin non-binary legacy payout math (dust quant).**
- **CombinatorialModule `combinatorialCollateralReturn` arbitrary selector interaction with conditional additivity.**
- **NegRiskModule `_finalizeNegriskResolution` rejects non-binary edge cases (out of scope if `_storeResult` enforces binary).**
- **PA-09..PA-14 (V1 only):** CtfAdapter redeem + split/merge round-trip + NegRisk reportOutcome + indexSet collision + FeeModule cumulative fee + CollateralToken guard.
- **Skip:** PA-01..05 (vendor 27/27 PASS), PA-06..08 (12/12 honest-zero session 2), PB-08 (1/1 unreachable), all V2 combinatorial rounding dust (informational), BRIDGE_ROLE synthetic Other (admin-gated).
- **Where:** `sources/polymarket/polymarket-v2/` (29 V2 .sol files, local-only) + `sources/polymarket/ctf-exchange-v2` + `sources/polymarket/neg-risk-ctf-adapter`.

### 2. Rotate to alternate (RECOMMENDED — Polymarket arc exhausted)
| Rank | Target | Action |
|------|--------|--------|
| 2a | 1inch PROP-023 | Mainnet NFT LOP usage scan → human gate → submission-reporting if accepted |
| 2b | Kamino Scope MEDIUM | Live feed map + bankrun stale-AUM profit PoC |
| 2c | marginfi T22 | Residual fee deposit/withdraw/borrow/liq |

### 3. Alternate promotions (lower priority)
| Rank | Target | Action |
|------|--------|--------|
| 3a | 1inch PROP-023 | Mainnet NFT LOP usage scan → human gate → submission-reporting if accepted |
| 3b | Kamino Scope MEDIUM | Live feed map + bankrun stale-AUM profit PoC |
| 3c | marginfi T22 | Residual fee deposit/withdraw/borrow/liq |

### Explicitly do not re-open
- Polymarket PA-01..08 honest-zero (vendor + session 2)
- Polymarket PB-08 unreachable on 0.8.34 (unless V2 Exchange impl differs)
- Makina X-001 / G-004 / X-004 residual eligibility kills
- Polymarket 2026-07-05 disproven P-02/P-05/P-09/P-10 as primary; standalone overflow DoS
- BitGo / Kiln OOS human-gate DO_NOT_SUBMIT without new unprivileged angle
- Invalid/dup: Silo #83293, Origin #82884, OnRe #82764, Superform
- Critical free-mint honest-zeros already closed (lombard, 1inch core, kamino Priority-0, etc.)

## Local artifacts (not pushed)
- `data/security_results/investigations/2026-07-29-residual-severity-sweep/`
- `data/security_results/investigations/2026-07-29-polymarket-cantina/`
- `sources/polymarket/ctf-exchange-v2/src/test/MatchMintMergeSurplus.t.sol` (13 tests, 13/13 PASS)
- `sources/polymarket/polymarket-v2/` (29 V2 .sol files, Sourcify-recovered)
- `data/security_results/lab_notebook/2026-07-29-polymarket-cantina-session1-scope-fanin.md`
- `data/security_results/lab_notebook/2026-07-29-polymarket-cantina-session2-pa06-pa08-honest-zero.md`
- `data/security_results/lab_notebook/2026-07-29-polymarket-cantina-session3-v2-source-unblock-honest-zero.md`
