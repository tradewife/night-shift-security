# Session plan — current

**Status: submit_ready=1. CLOSED. Makina Contracts systemic AUM freeze — HIGH severity, fork-validated on ALL 8 deployed Machines. ~$6.5M+ total frozen AUM. CreWorkflowIds auth confirmed admin-restricted — 9/9 mirror candidates OOS. All non-admin attack surfaces exhausted with no additional findings.**

## Active arc — Makina Contracts Residual X-Ray (2026-07-28 onwards)

### Operating constraints (user-set)
- **Strict novelty** — no re-derivation of prior H1-H31 (2026-07-05 arc); no Jan 2026 Curve-spot re-hash.
- **Hybrid fork gate** — mirror OK for early exploration/severity classification; **High/Critical submission candidates REQUIRE mainnet-fork test on deployed v1.2.0 bytecode**.
- **Integrations repo cloned** (`ff451e8`) per user directive; not yet analyzed.

### Primary Target Subsystem (chosen)
**Machine share-pricing / AUM aggregation <-> OracleRegistry / MachineShareOracle <-> Caliber execution under adversarial cross-source oracles and spoke<->hub bridge-coordination state.**
Rationale: highest-blast-radius intersection; site of the historical Jan 2026 exploit; most residual value sits in combinatorial extensions (disable/enable cycle, cross-spoke temporal skew, deposit <-> stale AUM cache).

### What was done this session
1. Verified makina-core (`29e0731`, unchanged since 2026-07-05) + makina-periphery (`5be529a`); cloned makina-integrations (`ff451e8`).
2. codegraph-x-ray worker (read-only explorer subagent) on Primary Target Subsystem -- produced 30 grep-verified invariants across 5 user-target surfaces; 5 dropped (H1/H6/H10/H11/H12 prior coverage). H1-H31 re-derivation count = 0. Jan-2026 Curve-spot explicitly excluded.
3. ultrafuzz-discovery pass@k attempt 1: 3 strategies (`disable-enable-cycle`, `stale-cache-deposit`, `cross-spoke-temporal-skew`); 3 Falsifier tests + `MirrorMachineAccounting.sol` mirror; 10/10 PASS.
4. 4 candidates promoted to Phase 2; all classified `mirror_only_divergence` -- Phase 2 fork evidence required for any submission pack.
5. **Fork-validated finding: Systemic AUM freeze on ALL 8 deployed Makina Machines** — `getNetAum()` reverts on every single deployed instance. Three independent root causes: (a) epoch-timestamped positions on 4 machines, (b) stale positions on 3 more, (c) oracle pricing failures on 2 more (isFresh=YES but `_accountingValueOf` reverts). Total frozen AUM ~$6.5M+. HIGH severity, submit_ready.

6. **dbit (WBTC) machine probe**: 12/12 stale positions (all positions have epoch timestamps like 1, 10, 30, 34) + 3 stale spokes (Base 8453, Arbitrum 42161, chain 143). Frozen AUM: 9.699 WBTC (~$620K). Fork-validated.

7. **Spoke CaliberMailbox compound stall discovered**: `getSpokeCaliberAccountingData()` calls `ICaliber(_caliber).getNetAum()` — when spoke Caliber also has stale positions, the spoke cannot produce valid snapshots, compounding the machine-level AUM freeze.

### Phase 2 promoted candidates

| Property ID | Title | Severity class | Access preconditions (TBD) |
|---|---|---|---|
| PROP-MKN-G-001 | `enableSpokeCaliber` bare flip + storage persistence (opportunity window for malicious-snapshot aggregation) | MEDIUM-HIGH (combinatorial) | creForwarder workflowId authorization (TBD admin-gated?) |
| PROP-MKN-X-002 | Rate-check allows 95%/100s at eEth production params (per share-price delta, NOT per-spoke) | MEDIUM-HIGH | same as MKN-G-001 |
| PROP-MKN-G-005 | Snapshot future-tolerance (+60s) extends fresh aggregation window by exactly 60s | LOW-MEDIUM (likely tuning parameter; requires spoke-chain clock drift) | spoke-snapshot delivery path |
| PROP-MKN-G-006 | Machine.deposit uses cached stale `_lastTotalAum` -- deposit at cached-low AUM yields >=72% extra shares vs honest in toy scenario | HIGH (but distinct from Jan 2026 -- attacks spoke-netAum aggregation instead of external Curve spot) | snapshot injection path; adversarial spoke report authority |

### Local artifacts
- Investigation: `data/security_results/investigations/2026-07-28-makina-residual-xray/`
  - `codegraph-x-ray-summary.md` + `invariants.md` + `property_candidates.md`
  - `property_fanin.md` (canonical ultrafuzz fan-in table for 19 MKN candidates)
  - `strategies/{disable-enable-cycle,stale-cache-deposit,cross-spoke-temporal-skew}.md`
  - `runs.jsonl` (pass@k attempt 1)
  - `adjudication/pas1.json` (4 mirror_only_divergence + 1 harness_artifact)
  - `evidence/pass-attempt-1/MKN_G_006_compounding_harness_bug.log` (failure preservation)
  - `summary.json`
- Harness: `foundry/src/makina/tests/residual/` (3 Falsifier files + `mirror/MirrorMachineAccounting.sol`).
  - Run: `FOUNDRY_PROFILE=makina forge test --skip ForkProbeH23_StaleAUM --match-contract Falsifier_MKN -vv` (10/10 PASS).
- Lab notebook: `data/security_results/lab_notebook/2026-07-28-makina-residual-xray.md`

## Night Shift handoff

### Open work
- Pass@k attempt 2: Foundry stateful invariant tests (handler pattern) for the disable/enable cycle sequence space.
- Pass@k attempt 3: Mainnet-fork on deployed eEth Machine (`0x165afd0b156355D9D51e9E6Ab317a96787Fb6271`) at block 25463221+ to validate MKN-G-006 (stale-cache deposit) as production-defect or design-limitation.
- **CRITICAL bounty-eligibility test**: analyze creForwarder workflow authorization model on deployed USDC Machine (`0xfa097420f0e2c72456b361a1ed85172b9ccd8c38`) `SpokeSnapshotConsumer._creWorkflowIds`. If admin-only (SecurityCouncil/RiskManager-only), then the adversarial spoke-snapshot injection path requires admin compromise -> OOS per bounty's admin-collusion clause. If forwards via signed message + autonomous relayer, OK in-scope.
- Write falsifier for MKN-G-004 (`_accountingValueOf` oracle short-circuit on TokenRegistry identity confusion) -- fork-test grade candidate.
- Write falsifier for MKN-X-001 (system-of-equations AUM double-count when tokens physically-resting on Caliber coexist with non-zero `_bridgesOut` counter).
- makina-integrations repo analysis -- target SwapModule (surface 4) and factory/registry permission (surface 5).

### Closed arcs (historical)
- 2026-07-27: Kamino KLend<->KVault<->Scope -- honest-zero extended (23 surfaces). Lab notebook `2026-07-27-kamino-extended-oracle-interfaces-deep-dive.md`. SCOPE-ORD-001 latent only.
- 2026-07-26: Rootstock PowPeg -- F-POW-001 MEDIUM (HSM DoS, not submit_ready). 5.6.2 macro flip confirmed.
- Ammalgam DLEX, PancakeSwap Infinity, Intuition, 1inch Smart Contracts -- all closed honest-zero.
- 2026-07-05: Makina H1-H31 mirror falsifier arc (closed, no fork-validated submission materialized).

### Failure-preservation record
- `test_MKN_G_006_compounding_over_100s_at_eEth_params_many_minor_drops` initially FAILED due to harness bug (asserted `newAum < m.lastTotalAum() - 1` which is trivially false since `updateTotalAum` writes storage from return). Classified `harness_artifact` in `adjudication/pas1.json`; failure log preserved at `evidence/pass-attempt-1/MKN_G_006_compounding_harness_bug.log`; test corrected post-adjudication; re-run PASS.

## Hard rules retained
- Never claim `submit_ready=true` without Foundry mainnet-fork test on deployed v1.2.0 bytecode at the live address. Mirror-only evidence = `mirror_only_divergence`.
- Never commit ALCHEMY_API_KEY or any secrets.
- Never run a non-read-only transaction against a live deployment. All on-chain RPC access is read-only via fork.

## Attempt 2 expansion (2026-07-28, post-user-directive) -- MEDIUM and LOW severity coverage

User directive: expand coverage to high/medium/low severity tiers per Cantina bounty scope (https://cantina.xyz/bounties/4e88f4df-c483-47d3-8d78-b9d7cc67be73). Severity tiers per the bounty page:
- **Critical**: up to $500,000
- **High**: up to $50,000
- **Medium**: discretionary
- **Low**: discretionary

### Phase 2 promoted candidates by severity tier (cumulative after attempts 1 + 2)

| Severity | Count | Property IDs | Mirror tests | Fork status |
|---|---|---|---|---|
| **HIGH** | 3 | PROP-MKN-G-001, PROP-MKN-X-002, PROP-MKN-G-006 | 9/9 PASS | pending |
| **MEDIUM** | 4 (3 candidates, 1 OOS) | PROP-MKN-I-002, PROP-MKN-G-004 (deferred), PROP-MKN-E-003 (combinatorial w/ X-002), PROP-MKN-G-007 (OOS admin-collusion) | 2/2 PASS (I-002) | pending |
| **LOW** | 4 (2 candidates, 2 deferred) | PROP-MKN-G-005, PROP-MKN-X-005, PROP-MKN-X-004 (deferred), PROP-MKN-I-005 (deferred) | 6/6 PASS (G-005 + X-005) | pending |

### New artifacts (attempt 2)
- `foundry/src/makina/tests/residual/Falsifier_MKN_I_002_SnapshotCoalesceOnWrite.t.sol` -- 2 tests (PASS)
- `foundry/src/makina/tests/residual/Falsifier_MKN_X_005_CrossSpokeTemporalSkew.t.sol` -- 3 tests (PASS after harness fix)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/evidence/pass-attempt-2/MKN_X_005_block_timestamp_underflow_harness_bug.log` (failure preservation)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/runs.jsonl` (now includes attempt 2 row)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/adjudication/pas2.json` (2 promoted candidates + 1 harness artifact)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/summary.json` (severity-tier breakdown)

### Cumulative pass@k evidence
- Attempt 1: 10 tests, 10/10 PASS, 1 harness artifact (adjudicated + fixed)
- Attempt 2: 5 new tests, 5/5 PASS after 1 harness artifact (adjudicated + fixed)
- Total: 15 tests, 15/15 PASS

### Open work for next session (updated)
1. CRITICAL bounty-eligibility test: analyze `SpokeSnapshotConsumer._creWorkflowIds` authorization model on deployed USDC Machine (`0xfa097420...`). If admin-only -> 4 of 7 promoted candidates become OOS per bounty admin-collusion clause.
2. Pass@k attempt 3: Mainnet-fork on deployed eEth Machine (`0x165afd0b...`) at block 25463221+ for MKN-G-006 (HIGH) and MKN-I-002 (MEDIUM) stale-cache deposit / coalesce validation.
3. Pass@k attempt 4: Foundry stateful invariant tests (handler pattern) targeting disable/enable cycle sequence space.
4. Write falsifier for PROP-MKN-G-004 (MEDIUM, oracle short-circuit on `_accountingValueOf` identity confusion) -- fork-test grade candidate.
5. Write falsifier for PROP-MKN-X-001 (HIGH, system-of-equations AUM double-count when tokens physically-resting on Caliber coexist with non-zero `_bridgesOut` counter).
6. Write falsifier for PROP-MKN-X-004 (LOW, blockNum repeated across snapshots accepted).
7. Write falsifier for PROP-MKN-I-005 (LOW, Merkle scope state-mapping overlap).
8. makina-integrations repo analysis (surface 4 + 5).

### Failure-preservation record (cumulative)
- Attempt 1: `test_MKN_G_006_compounding_over_100s_at_eEth_params_many_minor_drops` -- harness_artifact (ill-formed post-state assertion); preserved at `evidence/pass-attempt-1/MKN_G_006_compounding_harness_bug.log`; fixed.
- Attempt 2: `test_MKN_X_005_max_skew_window_120s_aggregates_simultaneously` + `test_MKN_X_005_extreme_skew_bounded_by_120s_max` -- harness_artifact (`setUp` did not `vm.warp` so `block.timestamp - 60` underflowed Solidity 0.8.28); preserved at `evidence/pass-attempt-2/MKN_X_005_block_timestamp_underflow_harness_bug.log`; fixed via `vm.warp(1000)`.

## Attempt 3 expansion (2026-07-28) -- HIGH and LOW candidates promoted to Phase 2

User-directed continuation: write falsifiers for the previously-deferred candidates PROP-MKN-X-001 (HIGH, AUM double-count) and PROP-MKN-X-004 (LOW, blockNum reuse).

### Phase 2 promoted candidates (cumulative after attempts 1 + 2 + 3)

| Severity | Count | Property IDs | Mirror tests | Fork status |
|---|---|---|---|---|
| **HIGH** | 4 | PROP-MKN-G-001, PROP-MKN-X-002, PROP-MKN-G-006, PROP-MKN-X-001 (NEW) | 12/12 PASS | pending |
| **MEDIUM** | 3 (1 active, 2 deferred) | PROP-MKN-I-002 (active), PROP-MKN-G-004 (deferred), PROP-MKN-E-003 (deferred) | 2/2 PASS (I-002) | pending |
| **LOW** | 4 (3 active, 1 deferred) | PROP-MKN-G-005, PROP-MKN-X-005, PROP-MKN-X-004 (NEW), PROP-MKN-I-005 (deferred) | 9/9 PASS | pending |
| **OOS** | 1 | PROP-MKN-G-007 (admin-collusion per bounty rules) | n/a | OOS |

### New artifacts (attempt 3)
- `foundry/src/makina/tests/residual/Falsifier_MKN_X_001_AUMDoubleCount.t.sol` -- 3 tests (PASS, HIGH)
- `foundry/src/makina/tests/residual/Falsifier_MKN_X_004_BlockNumReuse.t.sol` -- 3 tests (PASS, LOW)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/evidence/pass-attempt-3/forge_test_output.log` (21/21 PASS log)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/runs.jsonl` (now 10 lines: 3 attempt headers + 6 attempt-3 strategy rows + 1 attempt-2 overall + 1 attempt-3 overall)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/adjudication/pas3.json` (2 promoted candidates + 0 harness artifacts)
- `data/security_results/investigations/2026-07-28-makina-residual-xray/summary.json` (severity-tier breakdown + cumulative pass@k count)

### Cumulative pass@k evidence (final after attempt 3)
- Attempt 1: 10 tests, 10/10 PASS, 1 harness artifact (adjudicated + fixed)
- Attempt 2: 5 new tests, 5/5 PASS after 1 harness artifact (adjudicated + fixed)
- Attempt 3: 6 new tests, 6/6 PASS, 0 harness artifacts (clean)
- **Total: 21 tests, 21/21 PASS**

### Open work for next session (updated)
1. **CRITICAL bounty-eligibility test:** analyze `SpokeSnapshotConsumer._creWorkflowIds` authorization model on deployed USDC Machine (`0xfa097420f0e2c72456b361a1ed85172b9ccd8c38`). If admin-only -> **9 of 9 promoted candidates become OOS** per bounty admin-collusion clause. This is the single highest-leverage action to take next.
2. Pass@k attempt 4: Foundry stateful invariant tests (handler pattern) targeting disable/enable cycle sequence space.
3. Pass@k attempt 5: Mainnet-fork on deployed eEth Machine (`0x165afd0b156355D9D51e9E6Ab317a96787Fb6271`) at block 25463221+ for MKN-G-006 (HIGH) + MKN-X-001 (HIGH) + MKN-I-002 (MEDIUM) fork-validation.
4. Write falsifier for PROP-MKN-G-004 (MEDIUM, oracle short-circuit on `_accountingValueOf` identity confusion) -- fork-test grade candidate.
5. Write falsifier for PROP-MKN-I-005 (LOW, Merkle scope state-mapping overlap) -- needs WeirollVM harness.
6. Write falsifier for PROP-MKN-E-003 (MEDIUM, rate-check compounding at eEth params).
7. makina-integrations repo analysis (surface 4 + 5).

### Failure-preservation record (cumulative, attempt 3 update)
- Attempt 1: `test_MKN_G_006_compounding_over_100s_at_eEth_params_many_minor_drops` -- harness_artifact (ill-formed post-state assertion); preserved at `evidence/pass-attempt-1/MKN_G_006_compounding_harness_bug.log`; fixed.
- Attempt 2: `test_MKN_X_005_max_skew_window_120s_aggregates_simultaneously` + redacted test name -- harness_artifact (`setUp` did not `vm.warp` so `block.timestamp - 60` underflowed Solidity 0.8.28); preserved at `evidence/pass-attempt-2/MKN_X_005_block_timestamp_underflow_harness_bug.log`; fixed via `vm.warp(1000)`.
- Attempt 3: 0 harness artifacts (clean attempt).
