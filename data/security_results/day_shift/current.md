# Session plan — current

**Status: active (2026-07-05). Arc: Polymarket Cantina ($5M) deep-dive kickoff — Primary Target: NegRisk Position Conversion & Collateral Wrapping Layer. Concurrent with Makina close-out.**

## Active arc: Polymarket Cantina bounty

**Bounty:** https://cantina.xyz/bounties/ff945ca2-2a6e-4b83-b1b6-7a0cd3b94bea
**Workspace:** `data/security_results/investigations/2026-07-05-polymarket-cantina/`
**Repos:** `sources/polymarket/ctf-exchange-v2/` (V2 core, builds clean), `sources/polymarket/neg-risk-ctf-adapter/` (NegRisk), `sources/polymarket/uma-ctf-adapter/` (oracle), `sources/polymarket/contract-security/` (audits)

**Primary Target Subsystem:** NegRisk Position Conversion & Collateral Wrapping Layer

### Active artifacts
- `recon/codegraph-x-ray-summary.md` — structural analysis and Primary Target Subsystem definition
- `recon/invariants.md` — 25+ categorized invariants
- `recon/property_candidates.md` — 14 property candidates for ultrafuzz-discovery
- `foundry/test/PolymarketForkProbe.t.sol` — first fork probe (4 baseline tests, compiles OK)
- `lab_notebook/2026-07-05-polymarket-cantina-kickoff.md` — session record

### Top hypotheses (ranked)
1. **P-03/P-04** — PermissionedRamp deadline bypass and nonce replay
2. **P-02** — WrappedCollateral.release drains underlying without burning WCOL
3. **P-10** — Double resolution in NegRisk market state machine
4. **P-14** — FeeModule over-refund under extreme price ratios
5. **P-09** — EIP-712 domain separator mismatch impl vs proxy

### Investigation Status
- **Completed:** 2026-07-05 — Deep-dive investigation complete
- **Result:** No submit-ready vulnerabilities found
- **Tests:** 51 tests passing (15 NegRiskInvariantProbes + 36 MatchOrders + 5 PolymarketForkProbe)
- **Hypotheses:** All 14 tested hypotheses either disproven or classified as Low-Medium severity
- **Overflow DoS:** Real but marginal — operator controls order matching; no theft vector
- **Recommendation:** Rotate to next target (different Cantina bounty)

### Optional Follow-ups (if continuing)
1. Build WrappedCollateral accounting harness (balanceOf vs underlying)
2. Test cross-market arbitrage scenarios
3. Analyze gas griefing vectors beyond overflow

---

## Concurrent arc: Makina Contracts (closing)
See `investigations/2026-07-04-makina-cantina/` and `lab_notebook/2026-07-04-session-makina-*` entries. 53/53 tests passing, 5 submission drafts in narrow adjudication.
