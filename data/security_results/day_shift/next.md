# Session plan — next

**Status: queued after 2026-07-09 ONDO-ATCLOSE human gate**

## Ondo Perps Cantina — ATCLOSE killed; RCI open (v6.56.1)

- **ONDO-ATCLOSE-001:** killed at human gate (Decision D). Close/re-init of same attestation id is mechanical fact; impact fails because remint needs a **fresh** valid secp signature and old quotes expire before close is allowed.
- **Do not submit ATCLOSE.** Do not re-promote to Critical without same-signature value movement or durable rate/accounting bypass.
- **Still open:**
  1. `ONDO-RCI-ROUTE-001` — route not in quote digest; authenticated attestor/API probe required.
  2. `ONDO-RCI-PRICE-001` — 0.98 depeg-route delta measured locally; need policy evidence that attestor signs below-par during depeg.
- **submit_ready:** false (queue remains 0 for external posts).
- **Artifacts (kept-local):** `data/security_results/investigations/2026-07-08-ondo-perps-cantina/` (scope_gate, false_positive_checks, validation_summary, night-loop/human-gate, loop-12).

## Reserve Protocol Cantina — CLOSED HONEST-ZERO (v6.55)

- Full skill chain + live mainnet fork. 10/10 PASS. `submit_ready` unchanged (0).
- Do not reopen without new scope.

## Metric OMM Sherlock #1279 — CLOSED HONEST-ZERO (v6.54)

- L-29 confirmed but withheld (prior ACK). Do not reopen without exact-audit-tree access.

## Euler v2 — SCOPE-BLOCKED (v6.53.1)

- FoT desync out of scope under weird-tokens exclusion. Do not reopen without scope changes.

## Priority candidates

1. **Ondo authenticated attestor probe** (operator-approved) for RCI-ROUTE / RCI-PRICE only
2. Next operator-selected Cantina/Immunefi slug if Ondo policy probe kills both RCI candidates
3. Drift Token-2022 spot path local validator
4. Resolve OnRe human-gate queue item when operator prioritizes

## Carry-forward

- Superform submitted 2026-07-01 — await triage
- Weekly: platform sync all
- `submit_ready` remains 0 until a candidate passes human gate + submission-reporting
