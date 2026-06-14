# Intel digest — 2026-06-14

- **SPEC v3.3.0 shipped:** platform sync (208 Immunefi + 52 Cantina), split export (`research` vs `submittable`), PoC bundler + IVSS
- **Full bounty-depth run:** ~93 min; Cantina reserve/coinbase/morpho/euler harness verified; `submit_ready: false`
- **KLend live:** 104 `solana_reproduced` — fee-only CPI; `live_executed` still blocked (P0-3)
- **Wormhole:** 69+60 fork repros; triage CPCV grade 4 = `research_surface` only, not submittable
- **Platform coverage:** ~18 Immunefi + 12 Cantina curated vs 208+52 live — `platform diff` for gaps
- **Cron:** `nss-hipif-chain` 04:00 primary; deterministic fallback `nss-hipif-chain-run.py --init`
- **Saturated (loop):** aave, coinbase, euler, kamino, marinade, morpho, orca, raydium, wormhole
- **Next:** KLend instruction depth; novel Wormhole economic delta; Kate gate unchanged