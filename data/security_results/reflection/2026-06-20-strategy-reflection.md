# Strategy Reflection — 2026-06-20

## What Worked

1. **NativeHarness substrate** — every target gets an ABI/IDL-bound harness, real measured delta, and concrete candidates. This is solid and should be preserved.

2. **Foundry tests for falsification** — VULN-001 was successfully FALSIFIED by writing a Foundry test that calls the actual `SafeCast.toInt128(uint256)` function. The 7 falsification tests are a model for how to verify unchecked-conversion claims.

3. **Measured delta oracle** — every target has a measured delta capture in `data/security_results/impact/`. This is the core of the v5 substrate and must be preserved.

4. **Lab notebook** — every run produces a lab notebook entry. This provides a complete audit trail of what was tried and what was found.

5. **Trust boundary** — all gates (`validate_hypothesis()`, `qualifies_for_submission()`, evidence grading) remain intact. The system correctly rejected VULN-001 when verified against the actual library.

6. **PoolManager $56.9M USDC** — confirmed via live `balanceOf` call. High-value target surface exists.

## What Didn't Work

1. **Auditing well-defended protocols** — All 8 audited protocols (KLend, UniV4, Aave v3, Raydium, Wormhole, Orca, Jito, Morpho) are audited by top firms (OtterSec, Kudelski, Neodyme, Trail of Bits, Spearbit). Novel bug discovery is very hard.

2. **Initial VULN-001 claim** — claimed `PoolManager.mint()` unchecked overflow was exploitable. FALSIFIED by SafeCast. Lesson: always verify the actual library function before claiming an unchecked-conversion vulnerability.

3. **Cross-protocol integration attacks** — initial attempts at Uniswap v4 hook + Aave v3 flash loan integration did not find a novel attack path.

4. **False-positive measured-delta artifact** — the `uniswap_v4_hook_probe_measured_delta.json` file was created with VULN-001 claim, then DELETED when the claim was falsified. Lesson: never create measured-delta artifacts for claims that aren't fully verified.

## Key Insight

**The ceiling has been reached for well-audited protocols.** Continuing to audit the same 8 protocols will not produce a submittable bug. The system needs to:
1. Onboard NEW, less-audited targets
2. Focus on programs with fewer public audit reports
3. Try attack classes not yet explored (configuration errors, integration bugs, governance attacks)

## What to Change (v6)

### 1. Target rotation strategy

Instead of spending months on each well-audited target, v6 should:
- Rotate to new targets every 2-4 weeks
- Prioritize less-audited programs (`bounty_usd / (audit_firm_count + 1)`)
- Archive saturated targets after 30 days
- Maintain a self-documentation trail of what was tried

### 2. Self-evolving loop

The system should:
- Identify its own blind spots (attack surfaces not tried, target categories missed)
- Adapt its strategy based on what hasn't worked
- Propose new attack categories based on recent CVEs in adjacent protocols
- Maintain a "what hasn't worked" log (see `self_criticism/`)

### 3. Less-audited priority

Specific programs to onboard (in priority order):
1. **Reserve Protocol** ($10M Cantina) — complex RToken mechanism
2. **Coinbase** ($5M Cantina) — exchange code
3. **Ethena** ($3M Immunefi) — synthetic dollar
4. **SSV Network** ($250K Immunefi) — newer, less audited
5. **Pendle** ($2M Cantina) — complex PT/YT mechanics
6. **DeXe Protocol** ($500K Immunefi) — newer

### 4. Mandatory falsification protocol

For any candidate that claims an integer overflow, reentrancy, or access control vulnerability:
1. Verify the actual library function (e.g., `SafeCast.toInt128(uint256)`)
2. Write a Foundry test that confirms the overflow is possible
3. Only if the test confirms, record the finding

This prevents future false positives like VULN-001.

## What to Preserve (v5 substrate)

1. **All gates** — `validate_hypothesis()`, `qualifies_for_submission()`, evidence grading, credible harness
2. **NativeHarness pattern** — every target gets an ABI/IDL-bound harness
3. **Measured delta oracle** — every target has a positive measured delta
4. **Trust boundary** — LLM output is `metadata.trusted=false`, human gate for submission
5. **Foundry + Solana test infrastructure** — 747 tests pass
6. **Lab notebook** — every run produces an entry

## Recommended Next Steps for the Next Agent

1. **Read** the new SPEC.md (v6)
2. **Read** `data/security_results/self_criticism/2026-06-20-what-hasnt-worked.md`
3. **Read** the most recent 5 lab notebook entries
4. **Run** `python -m night_shift_security.cli.main platform sync --all` to see latest targets
5. **Decide** which new target to onboard first (recommended: Reserve Protocol)
6. **Onboard** the target using the process in SPEC.md §6
7. **Build** the NativeHarness and Foundry harness
8. **Capture** a measured delta (positive or honest zero)
9. **Document** in the lab notebook
10. **Update** the self-criticism document with what was tried and what was found

## Hard Rules (NEVER violate)

1. **NEVER loosen** any gate
2. **NEVER submit** without Kate's approval
3. **NEVER claim** unchecked-conversion vulnerability without falsification test
4. **NEVER skip** the falsification protocol
5. **NEVER deprioritize** a target just because it's hard
6. **NEVER accept** a false positive as "design feature" without re-verification

## Success Metrics for v6

1. **At least 1 new target onboarded** with positive measured delta
2. **Self-documentation maintained** — every run produces a lab notebook entry
3. **Self-criticism updated** — every run updates what hasn't worked
4. **Strategy reflection** — monthly reflection of what to change
5. **Target rotation** — automatic detection of saturated targets, onboarding of fresh ones
