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
- First re-auth via `POST /v1/auth/erc-4361/login/get_challenge` returned `error_code: unsupported_chain` for **every** chain value tested when body used snake_case (`wallet_address`, `chain_id`), for both our funded wallet and a known-good EOA (`0xd8dA…6045`).
- Root cause: docs body uses **camelCase** — `walletAddress` + `chainId: '1'`. Switching landed a fresh JWT (accountId `5372363397153609076`).
- Loop-15 IDOR probes all closed negative: sub-account header IDOR rejected (`subaccounts_not_enabled`); cross-account order fields reduced to either own-account submit or 401; address-book JWT-only delete works (no SIWE enforced server-side, separate finding surfaced below).
- **New finding: ONDO-API-ADDRBOOK-SCOPE-001** — API key with `scopes: []` (no scopes) can read / edit (label-only) / delete `/v1/wallet/address_book`, while `/v1/withdraw` (`transfer`), `/v1/perps/orders` (`trade`), and `/v1/api_keys/*` (`not_allowed`) all correctly require their respective scopes. **Escalation gauntlet closed negative** (2026-07-10): PUT is strict-update only (cannot change destination addresses), withdraw body has no label/ID reference (decoupled), public `ApiKeyScope` is `["trade","transfer"]` only (`address_book` is not a public scope name), and delete-all DoS doesn't block the withdrawal pipeline. Severity demoted to **Informational / Low**. Documented in `findings/ONDO-API-ADDRBOOK-SCOPE-001.md`. **No `submit_ready`.** No external post pending human gate.

If new operator review goes ahead, the next gates are: re-deposit ≥ 1.01 USDC to enable further on-chain pivot test for ONDO-API-INTERNAL-WITHDRAW-001, and Ping-Ondo to widen scope enforcement on address-book writes.
