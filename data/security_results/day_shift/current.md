# Session plan — current

**Status: active (2026-07-09). ONDO-API-INTERNAL-WITHDRAW-001 reality-gated. Not submit-ready. High withdrawn.**

## Reality gate

Measured A→B deposit withdraw + B credit is **likely expected custody** (A spends A’s funds; B’s deposit address is credited). That alone is **not** a strong Cantina finding.

| Field | Value |
|-------|--------|
| ID | ONDO-API-INTERNAL-WITHDRAW-001 |
| State | **`requires_impact_proof`** |
| Severity | **none** (High withdrawn) |
| `submit_ready` | **false** |
| External post | **blocked** |

### Not enough without further proof

- Peer force-credit of attacker-owned funds alone
- OpenAPI `internal_withdrawal_address` enum alone

### Would re-open only if measured

1. Material harm to B beyond receiving funds  
2. Ledger/accounting inconsistency  
3. Zero / self-deposit / protocol-wallet → stuck, double-credit, or loss  
4. Documented security/compliance control (not just enum)  
5. Double credit, wrong party, fee/limit bypass, protocol loss  

### Optional residual (needs ≥1.01 USDC each)

- Live withdraw to **own deposit**  
- Live withdraw to **zero**  

If those also look expected: kill as `killed_product_inconsistency` or keep `informational_only` schema note.

### Killed / closed elsewhere

- ATCLOSE killed  
- NET-LABEL fund-impact killed  

### Workspace

- `submission-draft/ONDO-API-INTERNAL-WITHDRAW-001/REALITY_GATE.md`  
- Prior High `report.md` is research-only, not for submit  

### Loop-15 incident note (2026-07-10)

- API origin (`api.ondoperps.xyz`) began returning **HTTP 404** on `/` and **HTTP 521 Origin Down** intermittently on `/v1/balance`, `/v1/api_keys`, etc. App frontend (`app.ondoperps.xyz`) and root (`ondoperps.xyz`) remain 200 throughout.
- Live re-auth via `POST /v1/auth/erc-4361/login/get_challenge` returns `error_code: unsupported_chain` for **every** chain value tested (1, 101, 8453, 42161, 137, 10, sonics, sei, monad, solana, ethereum-mainnet, eip155:* variants), for both our funded wallet and a known-good EOA (`0xd8dA…6045`). This blocks any cookie-funded live mutation test that depends on a fresh JWT.
- All session-bound live tests (subaccount IDOR, address-book SIWE-less delete, cheap withdraw pivot) cannot be exercised until Ondo's auth backend recovers and accepts a clear chain identifier. No new candidate can move to `submit_ready` without that token.
- Static-only verification of repo invariants remains possible; no engine-level honest-zero claims will be made against the live auth/app surface while 521/404 sweep is active.
