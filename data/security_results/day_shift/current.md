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
