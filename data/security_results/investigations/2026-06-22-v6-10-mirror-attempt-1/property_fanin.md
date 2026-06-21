# v6.10 KLend-flash Property Fan-in

selector: kamino KLend source (`sources/kamino/klend/programs/klend/src/`) plus deployed IDL (`target/idl/klend.json`).

| ID | Property | Category | Hand-tested in v6.9? | In validator scope for v6.10 |
|----|----------|---------|-----------------------|------------------------------|
| PROP-001 | After `flashBorrow` + `flashRepay` within tx N, vault balance is conserved mod flash fee | Conservation (K-2c) | partial (flash-only no repay) | YES - mirror attempt 1 |
| PROP-002 | Vault balance never decreases below zero pre-feevault collection | Conservation | NO | YES |
| PROP-003 | `fee_vault` delta equals protocol fee minus referrer cut (P-FEE) | Fee accounting | NO | YES |
| PROP-004 | Two `flashBorrow` calls in the same tx are rejected if state mutates between (P-MULTI) | Order/state flow | partial | YES - dex interleavings |
| PROP-005 | Twisted ix dispatch: portable ix_sysvar presence required inside flash callback | Sysvar/oracle checks | NO | YES (KLend's `validate_ixes_exclusive` analogue) |
| PROP-006 | `flashBorrow` reverts with `BorrowTooSmall` for amount below minimum | Math precision | YES (attempt 1, control) | YES |
| PROP-007 | `flashBorrow` reverts with insufficient liquidity when vault empty | Liquidity accounting | YES (attempt 2, control) | YES |
| PROP-008 | `flashRepay` requires `user_transfer_authority` to be a transaction signer | Authority | YES (attempt 3, control) | YES |
| PROP-009 | `flashBorrow` rejects when target `user_destination` is not owned by signer | Account constraints | NO | YES |
| PROP-010 | Token-2022 reserve path: transfer-fee is not double-counted on repay | Token-2022 exposure | NO | DEFERRED (mirror uses spl-token only) |
| PROP-011 | Re-deposit of repaid principal + fee does not reduce `fee_vault` | Re-deposit interaction | NO | YES |
| PROP-012 | Liquidation routing between `flashBorrow` callback and external liquidate cannot borrow `obligation` value | Settlement isolation | NO | DEFERRED (mirrors oracle stub) |

kill criteria and testing prep above; mirror attempt 1 starts at PROP-001..PROP-009.
