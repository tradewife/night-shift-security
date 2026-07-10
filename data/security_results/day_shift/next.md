# Next session queue

**Wave-2 closure (2026-07-10):** `continue-hunt-triage-wave2` sealed `continue_hunt`.
All 8 wave-2 leads + LEAD-E1 killed (0 unauthorized_success). `submit_ready = false`.
No CHM pack. Mission open. Do not promote any wave-2 lead without new measured impact.

## Priority 0

- Do **not** submit ONDO-API-INTERNAL-WITHDRAW-001 as High/Critical.
- Do **not** treat peer deposit credit as a vulnerability without new impact proof.

## Priority 1 — ADDRBOOK residual (no extra USDC required)

1. SIWE complete: re-add one withdrawal address (operator wallet sign).
2. Confirm withdraw path reaches amount/fee gate (not book gate).
3. Empty-scope HMAC DELETE that book entry.
4. Confirm withdraw → `withdrawal_address_not_found` (availability DoS).
5. Confirm empty-scope still cannot create attacker destination.
6. If proven: keep **Low** only; still not `submit_ready` unless program wants informational report.

## Priority 2 — INTERNAL-WITHDRAW residual (needs re-fund ≥1.01 USDC)

Only after book entry exists:

1. Withdraw to **own** deposit address.
2. Withdraw to **zero** (if book allows SIWE-add of zero — may reject).

If neither shows stuck funds / double credit / loss → kill as product inconsistency or informational schema note.

## Priority 3 — attestor policy (highest on-chain score path)

Authenticated/developer attestation-server probe for:

- route/asset/vault binding on signed quotes
- attestation_price vs Pyth equality / halt policy during depeg

Result either kills RCI or promotes to submission-draft with measured delta.

## Priority 4 — other hard surfaces

- Fresh fund-risk angles on in-scope API/app only.
- Skip ATCLOSE / NET-LABEL fund-loss re-open.
