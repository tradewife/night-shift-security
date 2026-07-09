# Session plan — current

**Status: active (2026-07-09). Ondo Perps Cantina — `ONDO-ATCLOSE-001` human-gate killed (Decision D). RCI route/price candidates still require authenticated attestor policy evidence. `submit_ready=false`.**

## Active arc: Ondo Perps Cantina ($1.5M CRITICAL, v6.56.1)

**Campaign:** Cantina bounty — hard-first on TEE/off-chain attestation to on-chain GM collateral mint/redeem integration  
**Live source:** `sources/ondo-global-markets-solana/repo` at `d1d011ea3008afe6131ce69a46bc53e954503eb8`  
**Program:** `XzTT4XB8m7sLD2xi6snefSasaswsKCxx5Tifjondogm`  
**Workspace (kept-local, gitignored):** `data/security_results/investigations/2026-07-08-ondo-perps-cantina/`

### Human-gate outcome (2026-07-09)

| Candidate | State | Score | Submit Ready | Notes |
|-----------|-------|------:|--------------|-------|
| ONDO-ATCLOSE-001 | **killed** | 1 | false | Decision D: close zeros PDA / same-id re-init is real, but remint needs **fresh** attestor sig; old sig → 6012; early close → 6026; same-id == fresh-id economics |
| ONDO-RCI-ROUTE-001 | requires_policy_evidence | 3 | false | Quote digest omits settlement route; needs authenticated attestor probe |
| ONDO-RCI-PRICE-001 | requires_policy_evidence | 3 | false | Pyth 0.98 depeg-route delta measured on-chain; needs attestor price policy probe |
| ONDO-GM-001 | bounded / low impact | 2 | false | Dust-bounded USDon residual |

**Do not submit ONDO-ATCLOSE-001.** No full `report.md` package; only `submission-draft/ONDO-ATCLOSE-001/NOT_SUBMITTED.md` plus FP artifacts (kept-local).

### FP gauntlet (executable)

- FP-1 same old signature after close → fail `AttestationExpired` 6012  
- FP-3 close before 30s → fail `AttestationTooNew` 6026  
- FP-6 fresh-id at 0.98 → same delta as Loop 12 same-id remint  
- Crucible: `atclose_false_positive_gauntlet` + `close_then_remint_replay` pass

### Next

1. Authenticated attestation-server / API probe for route binding (RCI-ROUTE) and depeg price policy (RCI-PRICE).
2. If policy is tight → kill RCI candidates; if loose → severity-gate and only then draft submission.
3. Do not re-open ATCLOSE as Critical without same-signature replay or independent accounting bypass.

### Night Shift handoff

- Cron OK to skip re-proving close/remint mechanics for ATCLOSE.
- Cron skip: do not promote ATCLOSE from killed without new evidence.
- Open for next session: authenticated attestor probe only (operator sign-off).

## Completed arc: Reserve Protocol Cantina ($10M CRITICAL, v6.55)

Engine-level honest-zero. 10/10 tests PASS. `submit_ready` unchanged (0). Do not reopen without new scope.

## Completed arc: Metric OMM Sherlock Contest #1279 (v6.54)

Honest-zero + L-29 ACK-withhold. `submit_ready` unchanged (0). Do not reopen without exact-audit-tree access.

## Completed arc: Euler v2 Cantina (v6.53.1)

FoT accounting desync scope-blocked. Do not reopen without scope changes.
