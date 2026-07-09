# Next session queue

## Priority 0

- Do **not** submit ONDO-API-INTERNAL-WITHDRAW-001 as High/Critical.
- Do **not** treat peer deposit credit as a vulnerability without new impact proof.

## Priority 1 — only if pursuing residual impact

Needs re-fund ≥1.01 USDC withdrawable per test:

1. Withdraw to **own** deposit address → re-credit, stuck, double-credit, or clean reject?
2. Withdraw to **zero** → burn, reject, or refund?

If neither shows stuck funds / double credit / loss / accounting break → set candidate to `killed_product_inconsistency` or `informational_only`.

## Priority 2 — other hard surfaces

- Fresh fund-risk angles on in-scope API/app only.
- Skip ATCLOSE / NET-LABEL fund-loss re-open.
