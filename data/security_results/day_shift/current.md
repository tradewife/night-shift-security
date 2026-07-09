# Session plan — current

**Status: active (2026-07-09). Ondo Perps Cantina — ATCLOSE killed; NET-LABEL fund-impact killed by live ETH dust credit. `submit_ready=false`.**

## Active arc: Ondo Perps Cantina ($1.5M CRITICAL, v6.56.2)

**Campaign:** Cantina bounty — in-scope **API/web** deposit+auth after on-chain ATCLOSE kill  
**Primary scope:** `api.ondoperps.xyz` / `app.ondoperps.xyz` / `ondoperps.xyz`  
**GM Solana (secondary / case-by-case):** `sources/ondo-global-markets-solana/repo` @ `d1d011ea...`, program `XzTT4XB8m7sLD2xi6snefSasaswsKCxx5Tifjondogm`  
**Workspace (kept-local):** `data/security_results/investigations/2026-07-08-ondo-perps-cantina/`

### Candidate board

| Candidate | State | Score | Submit Ready | Notes |
|-----------|-------|------:|--------------|-------|
| ONDO-ATCLOSE-001 | **killed** | 1 | false | Decision D: remint needs fresh attestor sig |
| ONDO-API-NET-LABEL-001 | **killed** (fund-impact) | 1 | false | Live 1 USDC ETH deposit **credited**; provision `chain=avax-c-chain` is label-only |
| ONDO-API-SOL-DEPOSIT-001 | candidate (weak) | 2 | false | Solana `5aBcN` stubs; disabled/non-primary path — Low/hygiene at best |
| ONDO-RCI-ROUTE-001 | requires_policy_evidence | 3 | false | Attestor route binding |
| ONDO-RCI-PRICE-001 | requires_policy_evidence | 3 | false | Attestor depeg policy |
| ONDO-GM-001 | bounded | 2 | false | Dust residual USDon |

### Funded experiment (2026-07-09) — NET-LABEL

- Funder: `0x74cEDF4b543694331dAF391ace4b9C7ad0d84c33`
- Account: `5372363397153609076`
- Provision `network=ethereum` → label `avax-c-chain`, deposit `0x805Cd6DB9421fe7f20Ce5fe0E89097dB9f1B9c9c`
- Tx: `0xe96780334f051ec2f58420f73e592787352a59270bfb6ceb983c3931efdcdc23` (1 USDC on **eth-mainnet**)
- Deposit `chainId=eth-mainnet` → pending → **confirmed**; `walletBalance=1`
- **Do not submit NET-LABEL as High/Critical.**

### Residual balances (operator)

- Ondo account: **1 USDC** withdrawable
- Funder wallet: ~0.307 USDC + ~0.0012 ETH

### Next

1. Continue low-volume in-scope API/app hunt for real Critical/High (not Solana stubs).
2. Optional: withdraw 1 USDC from Ondo account back to funder.
3. Optional: attestor policy probe for RCI (operator sign-off).
4. Do not re-open ATCLOSE or NET-LABEL fund-loss without new evidence.

### Night Shift handoff

- Cron: skip ATCLOSE re-proof; skip NET-LABEL re-proof of ETH credit.
- Open: new Primary Target Subsystem angles on trading/API; RCI only with attestor access.
- `submit_ready` remains false for Critical queue.
