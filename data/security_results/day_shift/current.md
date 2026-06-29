# Session plan — v6.35 Monad UI Bounty deep-dive — honest-zero

**Status: closed** (2026-06-29) — v6.35 Monad Foundation UI Bounty (Cantina, Critical $100k/High $30k/Medium $5k).
Investigation of claim.monad.xyz airdrop claim portal — Privy-integrated auth layer.
3 autonomous discovery loops completed. 16 findings (1 High, 7 Medium, 3 Low, 2 Info).
0 submission-ready. Surface exhausted without authenticated access.

## Summary

Investigation workspace at `data/security_results/investigations/2026-06-29-v6-35-monad-ui-bounty/`.

### Key Discoveries

**F-011 (High):** Reflective CORS with credentials on ALL `auth.privy.io` endpoints — the OPTIONS preflight echoes any attacker Origin with `access-control-allow-credentials: true`. The `GET /api/v1/apps/:id` response also reflects the attacker's origin, making the full Privy app config readable cross-origin. Confirmed on both `auth.privy.io` and `privy.claim.monad.xyz`. Requires pairing with XSS for full exploitation.

**F-007 (Medium):** Complete Privy app configuration accessible at `auth.privy.io/api/v1/apps/{app_id}` without auth. Exposes: verification key (ECDSA P-256), OAuth providers (Twitter, Discord, Farcaster, Telegram), embedded wallet settings, allowed domains list, email auth configuration.

**F-012 (Medium):** Complete Privy REST API surface (~80 endpoints) discovered via Next.js build manifest. Includes user search by email/wallet/social, wallet management (export, transfer, RPC), key quorums, policies, and OpenAPI spec at `/v1/openapi.json` (publicly accessible).

**F-013 (Medium):** Second verification key + public JWKS endpoint at `/v1/apps/{app_id}/jwks.json`.

**F-006 (Medium):** Stale `www.claim.monad.xyz` in Privy allowed_domains (NXDOMAIN DNS, but Vercel edge handles with 307 redirect to `claim.monad.xyz`).

### Artifacts

- 87 canonical properties across 11 categories (A–K) in `property_fanin.md`
- 6 strategy files: STRAT-001 (auth bypass), STRAT-002 (eligibility), STRAT-003 (Privy), STRAT-004 (race), STRAT-005 (XSS), STRAT-006 (abuse chains)
- Playwright E2E test harness (7 test methods, CSP, CORS, storage, cookies)
- 10 abuse chain analyses across 4 categories

### What did NOT move

- **`submit_ready` unchanged**: still 1 (OnRe H1 from v6.13).
- **No NSS pipeline changes**: 0 changes.
- **Key blocker**: Claim period ended (2025-10-1 to 2025-11-3); all sensitive endpoints require app secret or authenticated session.

### Primary Artifacts

- `data/security_results/investigations/2026-06-29-v6-35-monad-ui-bounty/` (setup.md, property_fanin.md, strategies/*.md, evidence/*, summary.json)
- `data/security_results/lab_notebook/2026-06-29-v6-35-monad-ui-bounty-recon.md`
- `data/security_results/lab_notebook/2026-06-29-v6-35-monad-ui-bounty-loops.md`
- `data/security_results/lab_notebook/2026-06-29-v6-35-monad-ui-bounty-loop3.md`

## Submission gate status

| Gate | Status |
|------|--------|
| OnRe H1 (v6.13) | **submit_ready=1** (unchanged) |
| Silo reentrancy (v6.32) | **submission-ready, requires human gate** (unchanged) |
| Veda Token-2022 STRAT-01 (v6.33) | **Honest-zero for current production; live the moment a Token-2022 deposit asset is added to Veda** |
| Coinbase Cantina (v6.34) | **4 carry-forward hypotheses adjudicated honest-zero (unchanged)** |
| Monad UI Bounty (v6.35) | **16 findings, 0 submission-ready. Surface exhausted without auth. Closed.** |
| Overall `submit_ready` | **1**, unchanged |
