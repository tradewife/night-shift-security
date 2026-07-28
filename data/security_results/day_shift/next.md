# Next session queue

**submit_ready=1. Makina session CLOSED with 1 HIGH severity finding.** Systemic AUM freeze on ALL 8 deployed Machines (dusd, deth, dmg, dqaeeth, intMkroywstETH, intMkSrRoyUSDC, usdSHFmk, dbit). Fork-validated. ~$6.5M+ total frozen AUM. CreWorkflowIds auth confirmed admin-restricted (AccessManaged restricted modifier) — 9 mirror candidates OOS. All non-admin attack surfaces exhausted. Move to next target per platform sync schedule.

Lab notebook: `data/security_results/lab_notebook/2026-07-28_makina_systemic_aum_freeze.md`
Evidence: `foundry/src/makina/tests/residual/AuthorizedCallerAUMFrozen.t.sol`

## Open work — Makina Contracts (priority order)

### Pass@k attempt 2 — stateful sequence fuzzing
Use Foundry invariant tests with handler pattern, target the `disable -> snapshot injection -> enable -> updateTotalAum` sequence space. Reuses the existing `foundry/src/makina/tests/residual/mirror/MirrorMachineAccounting.sol`. Recommended handler surface:
- `handleDisableSpokeCaliber(uint256 chainId)`
- `handleEnableSpokeCaliber(uint256 chainId)`
- `handleDeliverSnapshot(uint256 chainId, uint256 netAumBias, uint256 tsBias)`
- `handleUpdateTotalAum(bool sharePriceCheck)`
Invariant: `abs(totalAum_sequence - totalAum_honest) <= maxSharePriceChangeRate * elapsedTime * supply` is enforced; if AUM moves above the rate-cap exception-factoring honest oracle swing, the invariant is violated.

### Pass@k attempt 3 — mainnet-fork (CRITICAL)
- Target: deployed eEth Machine `0x165afd0b156355D9D51e9E6Ab317a96787Fb6271`.
- Block: 25463221 (verified by prior 2026-07-05 arc).
- Scenario: snapshot injection via creForwarder mock authorized path (MockCreForwarder) -> deposit with cached-low `_lastTotalAum` -> snapshot restoration -> deposit/or-redeem sandwich profit measurement.
- Confirms MKN-G-006 as production-defect or design-limitation.

### CRITICAL bounty-eligibility test
Analyze creForwarder workflow authorization model on the deployed USDC Machine (`0xfa097420f0e2c72456b361a1ed85172b9ccd8c38`):
- `SpokeSnapshotConsumer._creWorkflowIds` enumerable set.
- Who can call `addCreWorkflowId` (in production)? If SecurityCouncil/RiskManager-only via `restricted` modifier, the adversarial spoke-snapshot injection path requires admin compromise -> OOS per bounty's admin-collusion clause.
- If workflowId creation is publicly achievable via CRE-relayer sign-off chain-of-trust, OK in-scope.
- This is the kill criterion for PROP-MKN-G-001 / PROP-MKN-X-002 / PROP-MKN-G-006 -- three of the four Phase 2 candidates depend on this access path being achievable without admin compromise.

### Additional falsifiers (next surface coverage)
- PROP-MKN-G-004 (`_accountingValueOf` oracle short-circuit on TokenRegistry identity confusion): write falsifier exercising `_decodeAndMapBridgeAmounts` -> `getLocalToken(foreignToken, chainId)` returning `accountingToken` address while the foreign token is a different-decimals wrapper. Fork-test grade.
- PROP-MKN-X-001 (system-of-equations AUM double-count): write falsifier constructing a mock spoke CaliberMailbox where tokens physically rest on Caliber AND `_bridgesOut[token]` is non-zero with the same value. Verify hub `_getTotalAum` double-counts.
- PROP-MKN-I-006 (Caliber.rec executive asymmetric in recovery mode): generate a fork-test grade mirror replicating the `if (isPositionIncrease && recoveryMode) revert` check in `caliber/Caliber.sol:765-771`. Confirm `isPositionIncrease=false` position can be MANAGED while hub is in recovery.

### Integrations repo analysis
The `makina-integrations` clone (`ff451e8`) is unanalyzed. Target:
- SwapModule integration patterns (surface 4) -- external protocol interaction edge cases.
- Factory / HubPeripheryFactory / DirectDepositor deployment paths (surface 5) -- confirm whether malicious spoke deployment can be appended to a Machine after deployment (MKN-X-006 candidate evidence).

## Closed arcs

| Arc | Result | Date |
|-----|--------|------|
| Makina H1-H31 mirror (2026-07-05 arc) | Mirror VIOLATIONS identified, no fork validation | 2026-07-05 |
| Kamino KLend<->KVault<->Scope | Honest-zero extended (v6.62 Phase 2 4d-chess-seq) | 2026-07-27 |
| Rootstock PowPeg | F-POW-001 MEDIUM (HSM DoS, not submit_ready) | 2026-07-26 |
| Ammalgam DLEX | Honest-zero (4d-chess-sequential) | 2026-07-13 |
| PancakeSwap Infinity | Honest-zero (live BSC fork) | 2026-07-13 |
| Intuition | Honest-zero (7-session 4d-chess-seq) | 2026-07-15 |
| 1inch Smart Contracts | Honest-zero (10-session pass@k) | 2026-07-16 |

### Latent only (no session time unless trigger found)

- SCOPE-ORD-001 (needs exp>19 production path -- none known)
- KLEND-T22-001 (OOS privileged PD -- keep as hardening note in SPEC.md)

## Updated — Attempt 2 expansion (MEDIUM/LOW severity)

Per user directive (2026-07-28), expanded coverage to all Cantina severity tiers. 4 MEDIUM candidates (one OOS admin-collusion) + 4 LOW candidates (2 deferred) promoted. 2 active MEDIUM/LOW candidates have mirror tests passing; need fork validation.

### Next-session priorities (revised)
1. CRITICAL: analyze `SpokeSnapshotConsumer._creWorkflowIds` authorization model on deployed USDC Machine (`0xfa097420...`). If admin-only, then MKN-G-001/X-002/G-006/I-002 all become OOS per bounty admin-collusion clause.
2. Mainnet-fork on deployed eEth Machine (`0x165afd0b...`) at block 25463221+ for the 2 fork-test grade candidates with HIGH impact: MKN-G-006 (stale-cache deposit) + MKN-I-002 (snapshot coalesce-on-write).
3. Mainnet-fork on deployed USDC Machine (`0xfa097420...`) for MKN-G-005 (LOW, snapshot future-tolerance) and MKN-X-005 (LOW, cross-spoke skew) -- these are likely tuning-class rather than exploits, but worth confirming.
4. Foundry stateful invariant tests (handler pattern) targeting disable/enable cycle sequence space.
5. Write falsifiers for the deferred candidates: PROP-MKN-G-004 (MEDIUM, oracle short-circuit), PROP-MKN-X-004 (LOW, blockNum reuse), PROP-MKN-I-005 (LOW, Merkle scope overlap), PROP-MKN-X-001 (HIGH, AUM double-count), PROP-MKN-E-003 (MEDIUM, rate compounding).
6. makina-integrations repo analysis.

## Updated — Attempt 3 promotion of X-001 (HIGH) + X-004 (LOW)

Per user autonomous-loop continuation (2026-07-28), wrote falsifiers for the deferred candidates:
- PROP-MKN-X-001 (HIGH, AUM double-count under multi-spoke + idle + hubCaliber with rate-check-induced cache staleness): 3/3 PASS
- PROP-MKN-X-004 (LOW, blockNum field not validated for uniqueness): 3/3 PASS

Cumulative: 21/21 PASS across 7 test suites, 2 harness artifacts preserved + adjudicated + fixed, 0 harness artifacts in attempt 3 (clean).

### Next-session priorities (revised after attempt 3)
1. **CRITICAL bounty-eligibility test:** analyze `SpokeSnapshotConsumer._creWorkflowIds` authorization model on deployed USDC Machine (`0xfa097420f0e2c72456b361a1ed85172b9ccd8c38`). If admin-only -> 9 of 9 promoted candidates become OOS per bounty admin-collusion clause. **Single highest-leverage action.**
2. Pass@k attempt 4: Foundry stateful invariant tests (handler pattern) targeting disable/enable cycle sequence space.
3. Pass@k attempt 5: Mainnet-fork on deployed eEth Machine (`0x165afd0b156355D9D51e9E6Ab317a96787Fb6271`) at block 25463221+ for MKN-G-006 (HIGH) + MKN-X-001 (HIGH) + MKN-I-002 (MEDIUM) fork-validation.
4. Write falsifier for PROP-MKN-G-004 (MEDIUM, oracle short-circuit on `_accountingValueOf` identity confusion).
5. Write falsifier for PROP-MKN-I-005 (LOW, Merkle scope state-mapping overlap) -- needs WeirollVM harness.
6. Write falsifier for PROP-MKN-E-003 (MEDIUM, rate-check compounding at eEth params).
7. makina-integrations repo analysis (surface 4 + 5).
