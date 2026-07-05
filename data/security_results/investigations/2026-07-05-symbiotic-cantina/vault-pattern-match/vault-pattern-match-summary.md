# Vault Pattern Match Summary: Symbiotic Cantina

**Target**: Symbiotic Cantina — Core (VaultV2 + UniversalDelegator + Slasher + RewardsV2)

## Atlas Axes

- Inferred: `lending`, `staking`

## Scan Results

- Total AuditVault entries scanned: **2383**
- Hits above threshold (match_score >= 3): **459**
- After deduplication: **39**
- Final top hits: **20**

### Top 5 Hits

| Rank | Protocol | Bug Class | Severity | Match Score | Graph Anchor |
|------|----------|-----------|----------|-------------|--------------|
| 1 |  | Access Control | 0.0 | 7 | VaultV2._deposit |
| 2 | Origin | Access Control | 0.0 | 7 | Staking |
| 3 | Devve | Access Control | 0.0 | 7 | NetworkRestakeDelegator._stakeAt |
| 4 | BlueFin | Accounting | 0.0 | 7 | Share-price |
| 5 | Cod3x | Accounting | 0.0 | 7 | Vault |

### All 20 Ranked Hits

| Rank | Protocol | Bug Class | Severity | Score | Anchor |
|------|----------|-----------|----------|-------|--------|
| 1 |  | Access Control | 0.0 | 7 | VaultV2._deposit |
| 2 | Origin | Access Control | 0.0 | 7 | Staking |
| 3 | Devve | Access Control | 0.0 | 7 | NetworkRestakeDelegator._stakeAt |
| 4 | BlueFin | Accounting | 0.0 | 7 | Share-price |
| 5 | Cod3x | Accounting | 0.0 | 7 | Vault |
| 6 | Blueberry | Accounting | 0.0 | 7 | VaultV2._withdraw |
| 7 | Yield Basis | Accounting | 0.0 | 7 | VaultSnapshotRewards.claimVaultSnap |
| 8 | Elytra | Accounting | 0.0 | 7 | UniversalDelegator._sweepPending |
| 9 | Phi | Accounting | 0.0 | 5 | unanchored |
| 10 |  | Access Control | 0.0 | 5 | unanchored |
| 11 | Devve | Economic | 0.0 | 5 | unanchored |
| 12 | Covalent | State Desync | 0.0 | 5 | unanchored |
| 13 | Stakehouse Protocol | Reentrancy | 0.0 | 5 | unanchored |
| 14 | Audius | Access Control | 0.0 | 5 | BaseSlasher._slashableStake |
| 15 | Compound | Access Control | 0.0 | 5 | WithdrawalQueue.fill |
| 16 | Y2K | Economic | 0.0 | 5 | VaultV2._deposit |
| 17 | GMX | Accounting | 0.0 | 5 | UniversalDelegator.limitOf |
| 18 | Notional | Economic | 0.0 | 5 | VaultSnapshotRewards.claimVaultSnap |
| 19 | Smoothly | Access Control | 0.0 | 5 | VaultSnapshotRewards.claimVaultSnap |
| 20 | Party Protocol | Access Control | 0.0 | 5 | VetoSlasher.executeSlash |

### Coverage Gaps

Invariant categories with **zero** matching AuditVault patterns:

- **Slashing** — No structurally analogous historical finding in AuditVault corpus
- **Rewards** — No structurally analogous historical finding in AuditVault corpus

### Trust Boundary Reminder

> All hits are advisory pattern-match signals only. They are **not** validated hypotheses, **not** evidence of exploitability, and **do not** affect `qualifies_for_submission()`. Live reproduction is required before any hit can be promoted.
