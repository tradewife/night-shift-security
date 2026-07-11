# Next session queue

**Fresh recon session (2026-07-11):** Comparative accountId normalization, hidden-endpoint mining from app JS (13 paths found), empty-scope key HMAC READ tests (own data accessible, mutations blocked), WS API-key login (rejected — JWT only), subaccount creation endpoint active despite `disableSubaccounts: true`, referral code generation works (hidden endpoint), invite validation feature-disabled. All alive surface exhausted — no new CHM candidate. Continue hunting or transition per SPEC §4.4 (MarginFi v2).

## Priority 0

- Do **not** submit ONDO-API-INTERNAL-WITHDRAW-001 as High/Critical.
- Do **not** treat peer deposit credit as a vulnerability without new impact proof.
- Do **not** escalate empty-scope READ as cross-account (HMAC identity-bound).
- Do **not** escalate referral generation without redemption path.

## Priority 1 — Subaccount creation confirmation (highest ceiling)

1. Wait for rate-limit cooldown, retry single POST `/v1/subaccounts` probe with `label` + discover correct `subaccountType` field name (tried `subaccountType`, `type`, `accountType`, all hit rate limit).
2. If creation succeeds: check if subaccount can trade/perps despite parent's `disableSubaccounts: true`.
3. If subaccount bypasses feature flag: document as security-control bypass (Low-Medium).
4. If creation always fails with wrong schema: kill as unconfigurable endpoint residue.

## Priority 2 — ADDRBOOK residual (no extra USDC required)

1. SIWE complete: re-add one withdrawal address (operator wallet sign).
2. Confirm withdraw path reaches amount/fee gate (not book gate).
3. Empty-scope HMAC DELETE that book entry.
4. Confirm withdraw → `withdrawal_address_not_found` (availability DoS).
5. Confirm empty-scope still cannot create attacker destination.
6. If proven: keep **Low** only; still not `submit_ready` unless program wants informational report.

## Priority 3 — INTERNAL-WITHDRAW residual (needs re-fund ≥1.01 USDC)

Only after book entry exists:

1. Withdraw to **own** deposit address.
2. Withdraw to **zero** (if book allows SIWE-add of zero — may reject).

If neither shows stuck funds / double credit / loss → kill as product inconsistency or informational schema note.

## Priority 4 — attestor policy (highest on-chain score path)

Authenticated/developer attestation-server probe for:

- route/asset/vault binding on signed quotes
- attestation_price vs Pyth equality / halt policy during depeg

Result either kills RCI or promotes to submission-draft with measured delta.

## Priority 5 — Fresh surfaces (explored, deferred)

- **Hidden endpoints**: All return HTML (client-side routes), not REST JSON — skip.
- **WS API-key login**: Rejected (server disconnects) — JWT login only. Skip.
- **GET ?accountId= override**: Ignored (caller-scoped). Skip.
- **Referral/invite**: Code generation works but invite validation disabled. Skip.
- **Empty-scope key READ**: Own account only, not cross-account. Skip.

## Transition consideration

If Ondo Perps live API is fully exhausted (all surfaces probed, 0 unauthorized_success, no CHM candidate across all waves), recommend transitioning to next target per SPEC §4.4 (MarginFi v2). The on-chain audit also returned SOUND — no user-exploitable HIGH/CRITICAL. Residuals tracked above can be revisited with SIWE re-auth or if Ondo enables new features (WS private channels, invite code).
