# Session plan — current

**Status: active (2026-07-09). ONDO-API-AB-INTERNAL-001 impact proven live. Severity High. `submit_ready=true` with `human_gate`. Do not post externally.**

## Active arc: Ondo Perps Cantina

**Hot finding:** withdraw to **peer deposit address** succeeds on mainnet and **credits the peer**.

| Field | Value |
|-------|--------|
| ID | ONDO-API-AB-INTERNAL-001 |
| Severity | **High** (honest; not Critical — attacker spends own funds) |
| Tx | `0x8571bf8f55431e1265c7d48bc9cfaab12161e453172deb960313f256479850b7` |
| Attacker debit | 1.01 USDC (0.01 + $1 fee) from `5372363397153609076` |
| Victim credit | 0.01 USDC on `13954320701478500345` via deposit monitor |
| Peer deposit | `0xe6d3bc60bad02c0283b7e0df5659b8fb0d3d50dc` |
| OpenAPI intent | `internal_withdrawal_address` on AB complete + withdraw — **not enforced** |

### Package (local)

- `findings/ONDO-API-AB-INTERNAL-001.md`
- `submission-draft/ONDO-API-AB-INTERNAL-001/REPORT.md`
- `submission-draft/ONDO-API-AB-INTERNAL-001/NOT_SUBMITTED.md`
- Artifacts: `night-loop/loop-14/artifacts/probe_a1dep_{resume,impact}.json`, `impact_snapshot.json`

### Residual balances

- Funded Ondo: **~0.684 USDC**
- a1 Ondo: **0.01 USDC**
- Not enough for another 0.01+$1 fee test without top-up

### Candidate board

| Candidate | State | Submit | Notes |
|-----------|-------|--------|-------|
| ONDO-API-AB-INTERNAL-001 | **impact_proven_high** | human_gate | Peer deposit withdraw + credit |
| ONDO-ATCLOSE-001 | killed | false | |
| ONDO-API-NET-LABEL-001 | killed fund-impact | false | |
| ONDO-API-SOL-DEPOSIT-001 | weak | false | stubs |
| RCI / GM | policy / bounded | false | |

### Next

1. **Human:** review REPORT.md; approve/reject Cantina post; severity High vs Medium discussion ok.
2. Optional before submit: re-fund and test self-deposit + zero withdraw (strengthens package).
3. Do not re-open ATCLOSE / NET-LABEL fund-loss.
4. Stop external disclosure until gate clears.

### Night Shift handoff

- Cron: do not re-probe ATCLOSE/NET-LABEL; do not spam withdraws.
- Open: human gate on AB-INTERNAL-001 only.
