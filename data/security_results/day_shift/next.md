# Next session queue

**KLEND-T22-001 provisional submit_ready (1). Human adjudication needed on framing vs Immunefi OOS.** SCOPE-ORD-001 remains latent. submit_ready=1.

> **Open arc (2026-07-27 — v6.62.0, Kamino cross-layer):**
> Primary Target Subsystem: KLend ↔ KVault ↔ Scope.
> **KLEND-T22-001** — PermanentDelegate allowlisted without validation. 21/30 T22 liquidity mints live with PD; 66 reserves drainable by 7 PD holders. Code-confirmed + mainnet inventory confirmed.
>
> Pending human adjudication:
> 1. Can the Immunefi OOS ("T22 issues without irrecoverable loss") be reframed given the irrecoverable drain path?
> 2. Is the consistent extension-checking pattern sufficient to classify as code defect vs. design choice?
> 3. Does the live mainnet inventory (70% of T22 mints affected) meet evidence threshold for submit_now?

## Priority 0 — KLEND-T22-001 adjudication

1. Human review of framing vs Immunefi OOS
2. PoC validation on test validator (deploy T22+PD mint, fund KLend reserve, PD drain demo)
3. Gist submission package assembly
4. Advance to submit_now if adjudication passes

## Priority 1 — SCOPE-ORD-001 escalation

1. Construct synthetic MultiplicationChain producing exp>19
2. Route through MostRecentOf → KLend price feed
3. Demonstrate divergence bypass on KLend liquidation path

## Already exhausted (skip re-run)

- Kamino pure flash fee H1/H3/H4 (v6.8)
- Kamino elevation group over-borrow (honest-zero)
- Kamino ticket soft reservation (honest-zero)
- Kamino farms CPI (honest-zero)
- 1inch sessions 1–10 honest-zero / residual classes
- Horizen RA core deep press (v6.59–v6.60.2)
- Rootstock 9 strategies source-oracle honest-zero extended (v6.61.1)
