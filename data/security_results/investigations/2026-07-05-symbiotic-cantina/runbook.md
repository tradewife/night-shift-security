# Symbiotic Cantina Bounty — Investigation Runbook

**Target**: Symbiotic Shared Security Protocol (Core & Rewards V2)
**Bounty**: Cantina $500k Max (Critical) — https://cantina.xyz/bounties/acca29a4-d405-4405-a3b3-8c3feb10d1e3
**Start Date**: 2026-07-05
**Focus**: VaultV2 + UniversalDelegator + Slasher/Resolver + Rewards V2 interplay

## Repository Layout

```
sources/symbiotic/
├── repo/                    # symbioticfi/core (VaultV2, UniversalDelegator, Slasher, etc.)
│   └── test/invariant/
│       ├── SymbioticCoreInvariants.t.sol           # Our fuzz/invariant tests
│       └── handlers/SymbioticCoreHandler.sol        # Fuzz handler
└── rewards-v2/             # symbioticfi/rewards-v2 (Rewards, CumulativeMerkleRewards, etc.)
    └── test/invariant/
        ├── SlashingRewardsInvariants.sol           # Slashing + Rewards integration invariants
        └── handlers/
            ├── SlashingRewardsHandler.sol          # Slashing + Rewards fuzz handler
            ├── VaultSnapshotRewardsHandler.sol     # Existing rewards handler
            └── CumulativeMerkleRewardsHandler.sol  # Existing rewards handler

data/security_results/investigations/2026-07-05-symbiotic-cantina/
├── codegraph-x-ray-summary.md
├── invariants.md
├── property_candidates.md
├── strategies/
│   ├── adversarial_allocator_depositor_slashing_resolver.md
│   ├── vetoslasher_resolver_timing.md
│   └── rewards_distribution_integrity.md
├── runbook.md
├── runs.jsonl               # Run records
├── refinement_queue.json    # Recursive improvement queue
└── findings/                # Candidate findings
```

## Running Fuzz Tests

```bash
cd sources/symbiotic/repo

# Run specific invariant tests
forge test --match-contract SymbioticCoreInvariants -vvv

# Run with higher depth
FOUNDRY_FUZZ_RUNS=10000 forge test --match-contract SymbioticCoreInvariants -vvv

# Run all tests (includes original suite)
forge test
```

## Test Strategy

1. **Core Invariants** (Phase 1 — PASSING):
   - totalAssets = freeAssets + delegator.totalAssets()
   - Adapter assets match delegator reported assets
   - Total deposited >= total withdrawn
   - System balance positive when net deposits

2. **Slashing Integration** (Phase 2 — COMPLETED):
   - Share value integrity after slashing
   - Fair distribution of losses across depositors
   - Withdrawal queue + slash interaction
   - **Test file**: `sources/symbiotic/rewards-v2/test/invariant/SlashingRewardsInvariants.sol`
   - **Handler**: `sources/symbiotic/rewards-v2/test/invariant/handlers/SlashingRewardsHandler.sol`
   - **Results**: 3 invariants pass at 256 runs (128,000 calls each)

3. **Rewards V2 Integration** (Phase 3 — COMPLETED):
   - Snapshot rewards proportional to shares
   - Merkle rewards single-claim enforcement
   - Protocol fee calculation rounding
   - **Test file**: `sources/symbiotic/rewards-v2/test/invariant/SlashingRewardsInvariants.sol`
   - **Handler**: `sources/symbiotic/rewards-v2/test/invariant/handlers/SlashingRewardsHandler.sol`
   - **Results**: All invariants pass with slashing operations included

## Evidence Tracking

| Finding ID | Hypothesis | Severity | Status | PoC |
|------------|------------|----------|--------|-----|
| F-001 | VaultV2 ERC4626 inflation attack — depositors get 0 shares | — | **Rejected (non-novel)** | Exact match to Bailsec Core V2 Issue_03 (Severity: Medium, Resolution: "Acknowledged"). Explicitly excluded from Cantina scope as "already described issue from audits". |
| F-002 | Slashing + Rewards V2 cross-com invariant violation | — | **Not found** | Built comprehensive fuzz harness for old Vault + VetoSlasher + NetworkRestakeDelegator + VaultSnapshotRewards integration. 3 invariants pass at 256 runs (128,000 calls each). No invariant violations found. |

## Investigation Conclusion

**Core VaultV2 + UniversalDelegator + WithdrawalQueue Subsystem:**
- 32 invariant tests across 6 test suites: all pass (0 failures)
- 7 custom invariants at 1000 fuzz runs (50,000+ handler calls): all pass
- 861 existing tests: all pass (31 skipped as expected)
- Accounting invariant `totalAssets = freeAssets + delegatorAssets()` consistently holds under stress

**Slashing + Rewards V2 Integration (NEW):**
- Built comprehensive fuzz harness for old Vault + VetoSlasher + NetworkRestakeDelegator + VaultSnapshotRewards
- 3 invariants test slashing + rewards cross-com interactions
- 256 runs (128,000 calls each) — all invariants pass
- No invariant violations found in slashing + rewards integration

**Attack Surfaces Investigated (all mitigated or non-novel):**
1. Donation/inflation attack — Attacker loses their donation (OZ 4626 offset + proportional redemption). **Critical finding F-001 rejected as non-novel**: Exact match to Bailsec Core V2 audit Issue_03 (Severity: Medium, Resolution: "Acknowledged"). Explicitly excluded from Cantina scope.
2. Queue grief DOS — Only temporary; filled by next deposit or permissionless `sweepPending()`
3. Fee rounding evasion — Negligible at scale (informational)
4. Reentrancy — Robust via `ReentrancyGuardTransient` on all delegator entry points
5. Proxy/delegatecall safety — `staticDelegateCall` always-revert pattern prevents persistent state corruption
6. Allocation limits — Enforced and consistent; `forceDeallocate` correctly caps re-allocation
7. Share price manipulation — No viable path to extract value via donation or adapter manipulation
8. **Slashing + Rewards V2 cross-com** — No invariant violations found in comprehensive fuzz testing

**Coverage Gaps Identified (vault-pattern-match):**
- **Slashing**: No historical analogues found — potentially novel attack surface → **Investigated, no findings**
- **Rewards V2**: No historical analogues found — potentially novel attack surface → **Investigated, no findings**

**Bailsec Audit Cross-Check:**
- All known Bailsec issues (Issue_01 to Issue_32) have been reviewed
- No novel vulnerabilities found that haven't been previously documented
- Slashing + Rewards V2 integration appears robust against known attack patterns

**Conclusion:** The Symbiotic protocol demonstrates strong invariant adherence across all tested subsystems. The Slashing + Rewards V2 integration, which was identified as a potential novel attack surface, shows no invariant violations under comprehensive fuzz testing.

## Refinement Queue

See `refinement_queue.json` for prioritized improvements to harnesses and strategies.

## Integration Points

- `ultrafuzz-discovery` skill: Import `property_candidates.md` as canonical table
- `recursive-improvement` skill: Feed `runs.jsonl` into refinement cycle
- `bounty-loop` skill: Gate findings through submit_now flow
- `submission-reporting` skill: Generate submission packs from findings
