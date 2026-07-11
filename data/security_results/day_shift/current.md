# Session plan — current

**Status: active (2026-07-11). Fresh recon session: comparative accountId normalization, hidden-endpoint discovery from app JS, empty-scope key HMAC READ tests, WS API-key login, subaccount creation endpoint bypass, referral/invite surface probe. No new CHM candidate. `continue_hunt`, `submit_ready=false`, 0 unauthorized_success.**

## Wave-2 triage (continue-hunt-triage-wave2) — 2026-07-10

- All 8 wave-2 leads + LEAD-E1 hard-first probed with dual operator-owned sessions
  (prime / a1 / a2). `unauthorized_success_count = 0` → **all killed**.
- Verdicts: stale JWT revoked (`invalidate_jwt` enforced, 401 `auth_expired`); WS private
  channels `channel unsupported` (even own acct); CSV export returns own data; empty-scope
  key → 403 `key_doesnt_have_scope`; disabledFunctionality server-read-only; CF edge header
  trust correct; withdraw+book race serialized/blocked (0 funds moved).
- **Submission gates (VAL-SUBMIT-006) FAIL**: no Medium+ measured impact → `submit_ready = false`.
  Mission stays `continue_hunt` (VAL-CROSS-005/008/012). No pack, **no external post**.
- Near-miss ranking written: `adjudication/2026-07-10-wave2-triage-submit.md`. Top re-test
  targets: WS private channels (W2-A/B) if Ondo enables them; CSV export (W2-C) on format change.
- pytest `tests/test_native_ondo_gm.py`: **10 passed**.

## Final submission-pack triage (triage-submit-or-continue-hunt) — 2026-07-10

- Re-triaged **ALL** probe outputs (wave-1 deep-chm-probes + wave-2 continue-hunt +
  LEAD-E1 carry). Campaign-wide `unauthorized_success_count = 0`, `medium_plus_promoted = false`.
- Master gate matrix: `submission-pack/triage-gate-matrix.md` (VAL-SUBMIT-001..014,
  VAL-CROSS-001/003/004/005/008/010). Promotion gate **VAL-SUBMIT-006 FAILS** ⇒ `submit_ready = false`.
- Excluded priors K-1..K-8 **not** resurfaced as submit_ready (VAL-CROSS-003); no theory-only
  or reality-gated prior promoted (VAL-SUBMIT-005/013/014). **No external post** (VAL-SUBMIT-009).
- Ranked near-misses w/ triage payout re-score: `submission-pack/near-misses.md`.
- lead→probe→triage lineage map: `submission-pack/lineage-map.md` (VAL-CROSS-001).
- Continuum state file: `INVESTIGATION_STATUS.md` (`continue_hunt`, `submit_ready=false`).
- **Mission remains `continue_hunt`** (no CHM pack; VAL-SUBMIT-012 not met; VAL-CROSS-008 honored).
  Wave-2 continue-hunt features remain runnable via `data/security_results/investigations/.../next.md`.

## Reality gates (unchanged)

| ID | State | Notes |
|----|-------|-------|
| ONDO-API-INTERNAL-WITHDRAW-001 | `requires_impact_proof` | High withdrawn; peer deposit credit alone is not enough |
| ONDO-API-ADDRBOOK-SCOPE-001 | Informational / Low | Gauntlet closed; **loop-16 residual**: empty book now hard-blocks withdraw (`withdrawal_address_not_found`) — possible empty-scope delete DoS if re-proven after SIWE re-add |
| ONDO-RCI-ROUTE-001 / PRICE-001 | `requires_policy_evidence` | On-chain digest omits route/vault/program domain; needs attestor policy probe |
| ATCLOSE / NET-LABEL | killed | Do not re-open as fund-loss |

## Loop-16 (modular-analysis-skill)

- Skill present: `.agents/skills/modular-analysis-skill/SKILL.md`
- Native tests: 10 passed; static probe still dust-bounded
- Live API: JWT valid; balance `0.684255` USDC; withdraw destinations all rejected when book empty
- `bounty loop --target ondo_gm` → `unknown_forced_target` (not in scan queue)
- Artifacts: `night-loop/loop-16/*`, `findings/ONDO-API-ADDRBOOK-SCOPE-001-loop16-residual.md`
- Lab notebook: `lab_notebook/2026-07-10-ondo-perps-loop16-modular-analysis.md`

## Hard rules

- Do **not** submit INTERNAL-WITHDRAW as High/Critical without new impact proof
- Do **not** treat peer deposit credit as a vulnerability alone
- Do **not** promote ADDRBOOK residual above Low without SIWE re-add + empty-scope delete DoS measurement
- **Wave-2 is closed `continue_hunt`: no submit_ready, no CHM candidate. Do not reopen wave-2 leads without a concrete new impact angle.**
- No external post without human gate

## Fresh recon (2026-07-11) — app-JS hidden endpoints, empty-scope key READ, WS API-key auth, subaccount bypass

### App-JS hidden endpoint discovery

Mined `_app-7f0e4d06e12c2505.js` (1.7MB) for `/v1/` paths not in the published OpenAPI spec:

| Endpoint | Method | Result |
|----------|--------|--------|
| `/v1/subaccounts` | POST | **Active** — returns validation errors (`label required`, `invalid_subaccount_type`, `rate_limited`). **Inconsistent feature flag**: POST creation processes requests despite `disableSubaccounts: true`, while GET returns `subaccounts_not_enabled`. Field schema not fully discoverable via API probing alone — rate-limited before confirming creation. |
| `/v1/subaccounts` | GET | `subaccounts_not_enabled` (feature-flag blocked) |
| `/v1/referral_codes/generate` | POST | **Active** — returns real JSON with code, creator, created date. Works for funded account (returns code like `wqux57`). HTML for a1 (client-side routing). |
| `/v1/referral_codes` | GET | HTML (client-side route) |
| `/v1/invite_code/validate?code=X` | POST | `feature_disabled` — invite validation disabled server-side |
| `/v1/account/referral` | GET | HTML (client-side route) |
| `/v1/verify_eligibility` | GET | HTML (client-side route) |
| `/v1/agreement` | GET | HTML (client-side route) |
| `/v1/account/notifications` | GET | HTML (client-side route) |
| `/v1/perps/twap/orders/running` | GET | HTML (client-side route) |
| `/v1/perps/account/pledge` | POST | 404 `not_found` — endpoint exists but disabled |
| `/v1/perps/twap/orders` | POST | 405 Method not allowed |
| `/v1/account/referral` | GET | HTML (client-side route) |
| `/v1/script` | — | Unusual JS path, not tested |

### Empty-scope API key READ probes

Using HMAC-signed requests with `scopes:[]` key (`ondoKeyId_66587649d6939c7588f7d1df527c5efd`):

- **GET /v1/wallet/address_book**: 200 OK (own account data, empty addressBook) — empty-scope key CAN READ
- **GET /v1/account**: 200 OK (own account info) — no scope gate for READ
- **GET /v1/perps/balance**: 200 OK (own balance) — no scope gate for READ
- **GET /v1/api_keys**: 403 (scope enforcement ACTIVE for key listing)
- **POST /v1/perps/orders**: 403 (scope enforcement ACTIVE for mutations)

Verdict: Scope enforcement is **operation-dependent** — READ endpoints bypass scope checks (403 only on mutation). Not cross-account though (HMAC key binds to creator's identity).

### WS API-key login probe

- **JWT WS login**: Works — `loggedIn` response, `balancePerps` channel subscribes successfully.
- **API-key WS login**: Rejected — server closes connection after login attempt. Tested 5+ HMAC formats (string key, hex-decoded key, `ondo_perps_ws_login` domain, `ondo_perps_hmac` domain, `apiKey` field). All fail. WS only supports JWT auth.

### Comparative accountId normalization

- GET `/v1/perps/balance?accountId=<foreign_id>` under a1 JWT → returns a1's own balance (0.01), not a2's balance (0). **`?accountId=` GET param is ignored** — server resolves account from JWT identity.
- Earlier POST body `accountId` normalization confirmed: server overwrites to caller's own ID.

### Subaccount feature-flag bypass

- `disableSubaccounts: true` is set on **all** accounts (funded/a1/a2 all confirmed).
- GET `/v1/subaccounts` → `subaccounts_not_enabled` (flag enforced on listing).
- POST `/v1/subaccounts` proceeds through multi-stage validation (`label` → `subaccountType` → `rate_limited`) — **flag NOT enforced on creation endpoint**.
- If creation succeeds, subaccount would exist under parent with `disableSubaccounts: true`, creating a management blind spot (parent can't list what it created).

## Near-miss ranking (new)

| Lead | What | Severity | Status |
|------|------|----------|--------|
| ONDO-API-SUBACCOUNT-BYPASS-001 | POST /v1/subaccounts active despite disableSubaccounts flag | Low-Medium | Inconsistent feature flag enforcement; needs successful creation confirmation |
| ONDO-API-REFERRAL-CODE-001 | Referral generation works (hidden endpoint) | Low | Info: undocumented endpoint returns codes; no redemption path |
| ONDO-API-EMPTY-SCOPE-READ-001 | Empty-scope key reads own address book/account/balance | Informational | Own-account only; not cross-account |

## Hard rules (new findings)

- Do **not** treat empty-scope READ as cross-account (key is identity-bound).
- Do **not** escalate referral code generation without redemption path.
- Subaccount creation needs **successful creation confirmation** (not rate-limited) before severity estimate.

## Workspace

- `data/security_results/investigations/2026-07-08-ondo-perps-cantina/`
