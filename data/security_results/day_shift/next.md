# Next session queue

**v6.63.0 closed.** Polymarket session 2 closed: PA-06..08 honest-zero (12/12 PASS), PB-08 unreachable (1/1 PASS). `submit_ready=0` for new work.

## Priority queue

### 1. Polymarket Track A residual adapter probes (Recommended if continuing Polymarket)
- **What:** PA-09 (CtfAdapter redeem only resolved vector x balances; unresolved revert), PA-10 (split/merge round-trips PMCT within dust bound), PA-11 (NegRisk reportOutcome oracle-only), PA-12 (NegRisk convert indexSet collision), PA-13 (FeeModule cumulative fee <= order maxFee), PA-14 (CollateralToken guard)
- **Skip:** PA-01..05 (vendor **27/27 PASS**), PA-06..08 (12/12 honest-zero this session), PB-08 (1/1 unreachable)
- **Where:** `sources/polymarket/ctf-exchange-v2` + `sources/polymarket/neg-risk-ctf-adapter`
- **Rule:** pass@k ≥3; submit only human-gate PASS

### 2. Polymarket Track B — V2 source unlock
- **Blocker:** private `polymarket-v2` / deposit-wallet / ctf-auto-redeem / perpetuals-contract
- **On unlock:** PB-01 migration alias polarity regression, PB-02 vault credit, PB-04 combinatorial NO rounding
- **Live:** proxies + EIP-1967 impls in `scope.md`

### 3. Alternate promotions (if Polymarket blocked)
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
- `data/security_results/lab_notebook/2026-07-29-polymarket-cantina-session1-scope-fanin.md`
- `data/security_results/lab_notebook/2026-07-29-polymarket-cantina-session2-pa06-pa08-honest-zero.md`
