# Night Shift Security — Technical Specification

**Version:** 6.0.0-draft
**Date:** 2026-06-20
**Author:** Next-agent (post-extensive-audit handoff)
**Status:** Pivot from source-code-audit to **target-rotation + less-audited-program onboarding** strategy. v5 substrate preserved; v6 adds autonomous target discovery, self-documentation, and less-audited-program integration.

---

## 0. Why this version exists

After v5 shipped with `submit_ready=0` after auditing 8+ well-defended DeFi protocols (KLend, Uniswap v4, Aave v3, Raydium, Wormhole, Orca, Jito, Morpho) and finding VULN-001 to be a false positive, the deterministic path of "audit well-audited code, find bug" has reached a hard ceiling. The 8 protocols are all audited by OtterSec, Kudelski, Neodyme, Trail of Bits, Spearbit, and other top firms. Novel bug discovery against these targets requires either:
1. New, less-audited targets (the **target-rotation strategy**)
2. A self-evolving discovery loop that can adapt as targets are added
3. Better integration with the bounty platforms' public bug lists

v6 introduces:
- **Target rotation**: Automated detection of saturated targets, automatic onboarding of fresh targets from Immunefi/Cantina
- **Self-evolving loop**: The system identifies its own blind spots and proposes new target categories
- **Self-documentation**: Every run produces a lab-notebook entry; the system maintains a living "what we tried, what worked" document
- **Less-audited priority**: Prioritize programs that are listed on Immunefi/Cantina but have fewer public audit reports

The v5 NativeHarness substrate is preserved — every new target must pass through the same NativeHarness + measured-delta gate before becoming `ready`. The synthetic substrate is still retired. Trust boundary (gates, `metadata.trusted=false`, `submission_alert.json` human gate) is preserved.

---

## 1. Executive Summary

v6 is a pivot from "audit more code, find bug" to "rotate to less-audited code, find bug" with full self-documentation.

The system is currently strongest at:
- Rejecting weak or synthetic findings (gates work)
- Building real on-chain harnesses (Foundry + Solana tests)
- Proving measured deltas on deployed state
- Documenting everything in the lab notebook
- Preserving the trust boundary

The system is currently weakest at:
- Finding submittable bugs in well-audited protocols (VULN-001 FALSIFIED, all paths defended)
- Rotating to new, less-audited targets automatically
- Adapting its own discovery strategy based on what hasn't worked
- Quantifying which attack surfaces have been exhausted

v6 explicitly addresses these gaps via:
- **Target rotation engine** that detects saturation and prioritizes fresh targets
- **Self-documentation** that records what was tried, what was found, and what remains
- **Less-audited priority** scoring: programs with fewer public audit reports rank higher
- **Adversarial self-criticism**: the system maintains a list of attack surfaces it HASN'T tried

---

## 2. Non-Negotiable Trust Boundary (UNCHANGED from v3.x, v4, v5)

These rules remain unchanged. They are the foundation of the system.

1. LLM, agent, and delegate output is untrusted by default.
2. `validate_hypothesis()` or its v5+ schema successor must gate all external proposals.
3. Python validation, evidence grading, credible harness checks, task verifier, and `qualifies_for_submission()` remain authoritative.
4. No autonomous external submission.
5. `submission_alert.json` remains a local human gate only.
6. Catalogue replay, triage-only forks, fixtures, and fee-only CPI deltas must never become `submit_ready`.
7. Every run must leave reproducible artifacts and a lab notebook entry.
8. Solodit and AuditVault findings are historical analogue intelligence only; they never satisfy evidence, reproduction, deployed viability, or submission gates.
9. **NEW in v6**: VULN-style claims must be falsified against upstream library implementations (SafeCast, etc.) BEFORE being recorded as a live vulnerability. Any claim that depends on unchecked integer conversion must be verified by reading the actual library function.

---

## 3. Lessons Learned from v5 Audit Cycle (2026-06-18 to 2026-06-20)

This section documents every major finding from the v5 audit cycle so the next agent does not repeat the work.

### 3.1 Programs audited and outcomes

| Program | Source | Bounty | Outcome | Key finding |
|---------|--------|--------|---------|-------------|
| **Kamino (KLend)** | `sources/kamino/klend/` | $1.5M | No bug found | Price validation bounded by obligation refresh intersection; flash loans are transaction-level; `next_protocol_fee` uses `wrapping_add` but practically infeasible |
| **Uniswap v4** | `sources/uniswap_v4/repo/` | $15.5M | VULN-001 **FALSIFIED** | `mint()` unchecked `amount.toInt128()` — REVERTED by `SafeCast.toInt128(uint256)` at SafeCast.sol:56-59; `using SafeCast for *;` means unchecked block does NOT disable library reverts |
| **Uniswap v4 hooks** | Same | $15.5M | No bug found | `afterSwap` extraction bounded by `swapDelta - hookDelta` (Hooks.sol:312) — design feature, not bug |
| **Aave v3** | `sources/aave_v3/repo/` | (was $250k) | No bug found | Flash loan callback properly designed; `executeBorrow` properly validated; isolation mode properly bounded |
| **Raydium CLMM** | `sources/raydium/repo/` | $505K | No bug found | Tick array bitmap properly bounded; AMM math is standard Uniswap V3 |
| **Wormhole** | `sources/wormhole/repo/` | (was $1M) | No bug found | Already-completed VAA replay shows zero delta; authorized replay is non-submittable |
| **Orca Whirlpools** | `sources/orca/repo/` | $500K | No bug found | `next_protocol_fee.wrapping_add(delta)` is a theoretical issue but practically infeasible; vault balance not affected |
| **Jito** | `sources/jito/repo/` | $2.0M | N/A | Infrastructure (validator history), not DeFi |
| **Morpho Blue** | `sources/morpho/repo/` | $2.5M | N/A | `harness_built`, not `ready`; USDC/WETH market has no positions |

### 3.2 Critical lesson: library override pattern

**Pattern discovered:** Many "vulnerabilities" that look like unchecked integer overflows are actually protected by upstream library overrides. Before claiming any vulnerability based on an unchecked block, **ALWAYS** verify the actual library function called by the unchecked conversion.

Example: `PoolManager.mint()` at PoolManager.sol:326 has `amount.toInt128()` in an `unchecked` block. But `PoolManager.sol:81` has `using SafeCast for *;` and `SafeCast.toInt128(uint256)` at SafeCast.sol:56-59 explicitly reverts for `x >= 1 << 127`. The unchecked block does NOT disable the library's explicit revert.

**Required verification step for any unchecked-conversion claim:**
1. Find the `using <Library> for *;` declaration in the calling contract
2. Find the actual library function for the conversion
3. Read the library function to confirm whether it has explicit revert
4. Write a Foundry test that calls the actual library function and confirms the revert

### 3.3 Why well-audited protocols are exhausted

All 8 audited protocols have been audited by:
- **OtterSec** (Orca Whirlpools, Kamino KLend)
- **Kudelski Security** (Orca Whirlpools)
- **Neodyme** (Kamino KLend, Aave v3)
- **Trail of Bits** (Uniswap v4, Aave v3)
- **Spearbit** (Uniswap v4, Aave v3, Wormhole)
- **Trail of Bits / Zellic / Certora** (various)

**The probability of finding a novel, submittable bug in these protocols is very low.** Future effort should focus on:
1. Programs that are on Immunefi/Cantina but have fewer or no public audit reports
2. Programs that have been recently upgraded (new attack surface)
3. Programs that have a specific, narrow bug class (e.g., specific oracle manipulation, specific callback reentrancy)

### 3.4 Top active bounties as of 2026-06-20 (NOT in our repos)

| Program | Bounty | Audit history | Recommended priority |
|---------|--------|---------------|---------------------|
| **Reserve Protocol** | $10M (Cantina) | Multiple audits | HIGH — $10M is the biggest single bug bounty not in our repos |
| **Polymarket** | $5M (Cantina) | Multiple audits | MEDIUM — well-audited but novel conditional token attack surface |
| **Coinbase** | $5M (Cantina) | Internal | HIGH — exchange code often has unique vulnerability classes |
| **Ethena** | $3M (Immunefi) | Multiple audits | MEDIUM — synthetic dollar with complex mechanism |
| **Pendle** | $2M (Cantina) | Multiple audits | MEDIUM — yield trading with complex PT/YT mechanics |
| **dYdX** | $1M (Cantina) | Multiple audits | LOW — Cosmos, not Solana/EVM familiar |
| **SSV Network** | $250K | New | HIGH — newer, less audited |
| **ENS** | $250K | Mature | LOW — very well audited |
| **DeXe Protocol** | $500K | New | HIGH — newer, less audited |
| **Zest Protocol V2** | $100K | New | MEDIUM — Stacks (unfamiliar) |

### 3.5 VULN-001 falsification details (for future reference)

**Claim:** `PoolManager.mint()` at PoolManager.sol:322-329 has an unchecked `amount.toInt128()` at line 326 that allows minting unlimited ERC6909 claim tokens for free.

**Falsification:**
- `PoolManager.sol:81` has `using SafeCast for *;`
- `SafeCast.sol:56-59`:
  ```solidity
  function toInt128(uint256 x) internal pure returns (int128) {
      if (x >= 1 << 127) SafeCastOverflow.selector.revertWith();
      return int128(int256(x));
  }
  ```
- For `x = 2^128 = 340282366920938463463374607431768211456 >= 2^127`, the function reverts.
- 7 Foundry tests in `foundry/test/UniV4MintOverflowFalsification.t.sol` confirm:
  - `mint(self, USDC_TOKEN_ID, 2^128)` reverts
  - `mint(self, USDC_TOKEN_ID, type(int128).max + 1)` reverts
  - `mint(self, USDC_TOKEN_ID, type(uint128).max)` reverts
  - No claim tokens are minted after revert
- The `unchecked` block does NOT disable the SafeCast library's explicit revert

**Lesson for future agents:** Always verify the actual library function before claiming an unchecked-conversion vulnerability.

---

## 4. v6 Architecture: Self-Evolving Autonomous Discovery Loop

v6 is organized around a single, continuous loop that the system runs every cycle. Each cycle:

1. **Assess** — which targets are saturated, which are under-explored
2. **Onboard** — add a new target from Immunefi/Cantina if needed
3. **Hunt** — run the v5 NativeHarness + measured-delta process on the selected target
4. **Reflect** — record what was tried, what was found, and what remains
5. **Adapt** — update the discovery strategy based on lessons learned

This loop runs continuously. The system is always either:
- Building a harness for a new target
- Running exploits on an existing target
- Reflecting on what hasn't worked
- Adapting its strategy

### 4.1 Target rotation engine

The system maintains a `target_status` registry in `data/security_results/loop/native_harness_status.json`. For each target:

```json
{
  "target_slug": "string",
  "status": "missing|mapped|harness_built|ready|saturated",
  "bounty_usd": 0,
  "audit_firm_count": 0,
  "last_hunt_date": "ISO date",
  "hunt_attempts": 0,
  "findings_generated": 0,
  "submittable_findings": 0,
  "attack_surfaces_exhausted": ["list of surfaces tried"],
  "next_action": "string"
}
```

**Rotation algorithm:**
- If `status == "saturated"` for > 14 days: move to "exhausted", deprioritize
- If `status == "ready"` but no measured-delta improvement in 30 days: deprioritize
- If `status == "missing"` or `"mapped"`: prioritize building harness
- New targets from `platform sync` are added with `status = "missing"` and `priority_score = bounty_usd / (audit_firm_count + 1)`

**Priority score formula:**
```
priority_score = bounty_usd / (audit_firm_count + 1)
```

This prioritizes high-bounty, less-audited programs. A $10M program audited by 3 firms scores: 10,000,000 / 4 = 2,500,000. A $1M program with no audits scores: 1,000,000 / 1 = 1,000,000. A $10M program with 10 audits scores: 10,000,000 / 11 = 909,090.

**Target rotation cadence:**
- Weekly: `platform sync` to fetch new listings
- Bi-weekly: re-rank targets by priority score
- Monthly: archive targets that have been saturated for >30 days

### 4.2 Self-documentation requirements

Every run must produce:

1. **Lab notebook entry** in `data/security_results/lab_notebook/YYYY-MM-DD-*.md`
   - What target was investigated
   - What attack surfaces were tried
   - What was found (including negative results)
   - What remains unexplored
   - Lessons learned

2. **Target status update** in `data/security_results/loop/native_harness_status.json`
   - Update `last_hunt_date`, `hunt_attempts`, `findings_generated`
   - Add to `attack_surfaces_exhausted` if applicable
   - Update `next_action`

3. **Strategy reflection** in `data/security_results/reflection/YYYY-MM-DD-*.md`
   - What didn't work and why
   - What new approach to try next
   - Which targets to deprioritize

4. **Adversarial self-criticism** in `data/security_results/self_criticism/`
   - The system maintains a list of attack surfaces it has NOT tried
   - This list is updated after every run
   - New attack surfaces are proposed based on what has been found

### 4.3 Self-evolving strategy

The system adapts its discovery strategy based on:

1. **What has worked**: positive measured deltas, successful harnesses
2. **What hasn't worked**: all the attacks tried that produced no bug
3. **What's untried**: attack surfaces not yet explored
4. **What's new**: recently added targets, recently published CVEs

**Adaptation rules:**
- If a target has been saturated for >30 days with no measured-delta, deprioritize
- If a specific attack class (e.g., "flash loan oracle manipulation") has been tried on 3+ targets with no result, try a different class
- If the system is consistently finding "design features" rather than bugs, look for integration or configuration vulnerabilities
- If the system finds a false positive (like VULN-001), document the lesson and update the verification protocol

### 4.4 Less-audited program priority

The system should prioritize programs based on:

```python
def priority_score(bounty_usd, audit_firm_count, days_since_listed, is_solana):
    base = bounty_usd / (audit_firm_count + 1)
    freshness = 1.0 / max(1, days_since_listed / 30)  # newer = higher
    solana_bonus = 1.5 if is_solana else 1.0  # prefer Solana per system design
    return base * freshness * solana_bonus
```

**Recommended priority targets (v6 kickoff):**
1. **Reserve Protocol** ($10M, Cantina) — HIGH PRIORITY
2. **Coinbase** ($5M, Cantina) — HIGH PRIORITY
3. **Ethena** ($3M, Immunefi) — MEDIUM PRIORITY
4. **SSV Network** ($250K, Immunefi) — NEW, less audited

### 4.5 Target onboarding pipeline

For each new target:

1. **Clone source**: `git clone <repo> sources/<target>/repo`
2. **Build NativeHarness**: `src/night_shift_security/native/<target>.py`
3. **Run semantic map**: `python -m night_shift_security.cli.main semantic map --slug <target>`
4. **Build Foundry harness**: `foundry/test/<Target>Measure.t.sol`
5. **Capture measured delta**: `data/security_results/impact/<target>_measured_delta.json`
6. **Promote to ready**: `python -m night_shift_security.cli.main native mark --slug <target> --status ready`

Every step must be reproducible and documented in the lab notebook.

---

## 5. v6 Target Pipeline: Specific Programs to Onboard

The following programs should be onboarded in v6, in priority order:

### 5.1 Reserve Protocol ($10M, Cantina) — PRIORITY 1

**Why:** Largest single bug bounty not in our repos. Reserve Protocol is a DeFi stablecoin system with RTokens, Collateral, and a complex interaction between them.

**Onboarding steps:**
1. Clone `https://github.com/reserve-protocol/protocol` to `sources/reserve/repo`
2. Build `src/night_shift_security/native/reserve.py` with program IDs, selectors, ABI
3. Build `foundry/test/ReserveMeasure.t.sol` for measured delta capture
4. Target attack surfaces:
   - RToken minting/burning (asset-to-rtoken ratio manipulation)
   - Collateral basket validation
   - Insurance staker interactions
   - Revenue distribution (cumulative revenue, default delay)
5. Build `data/security_results/impact/reserve_measured_delta.json` with positive measured delta
6. Promote to `ready`

**Expected outcome:** Complex DeFi system with many possible vulnerability classes. Reserve Protocol has had audits from multiple firms, so finding a novel bug will be hard, but $10M bounty justifies the effort.

### 5.2 Coinbase ($5M, Cantina) — PRIORITY 2

**Why:** Large bounty, exchange code (unique vulnerability classes).

**Onboarding steps:**
1. Clone relevant Coinbase contracts (need to identify which ones are in scope)
2. Build `src/night_shift_security/native/coinbase.py`
3. Target attack surfaces: order book, matching engine, settlement, fee calculation
4. Build measured-delta harness

**Risk:** Coinbase has extensive internal security teams. Novel bug discovery is very hard.

### 5.3 Ethena ($3M, Immunefi) — PRIORITY 3

**Why:** Synthetic dollar protocol with complex mechanism (USDe). Newer than Aave, less audited.

**Onboarding steps:**
1. Clone `https://github.com/ethena-labs/ethena` to `sources/ethena/repo`
2. Build `src/night_shift_security/native/ethena.py`
3. Target attack surfaces: USDe minting, ETH collateral management, delta hedging
4. Build measured-delta harness

**Expected outcome:** Synthetic dollar protocols have unique vulnerability classes (e.g., depeg attacks, collateral management bugs).

### 5.4 SSV Network ($250K, Immunefi) — PRIORITY 4

**Why:** Newer, less audited. Ethereum staking infrastructure.

**Onboarding steps:**
1. Clone SSV contracts
2. Build harness
3. Target attack surfaces: validator registration, signature aggregation, reward distribution

### 5.5 Pendle ($2M, Cantina) — PRIORITY 5

**Why:** Yield trading with complex PT/YT mechanics. Has had bugs before.

**Onboarding steps:**
1. Clone Pendle contracts
2. Build harness
3. Target attack surfaces: PT/YT minting, yield redemption, expired market handling

### 5.6 DeXe Protocol ($500K, Immunefi) — PRIORITY 6

**Why:** Newer, less audited. Complex DeFi protocol.

**Onboarding steps:**
1. Clone DeXe contracts
2. Build harness
3. Target attack surfaces: trading, liquidity pools, governance

---

## 6. Onboarding Process (Detailed)

For each new target, follow this exact process:

### 6.1 Source clone

```bash
cd /home/kt/projects/rtp/night-shift-security
git clone <repo_url> sources/<target>/repo
# Pin commit for reproducibility
cd sources/<target>/repo
git log -1 --format="%H" > ../source_commit.txt
```

### 6.2 NativeHarness skeleton

Create `src/night_shift_security/native/<target>.py` with:

```python
"""<Target> NativeHarness — <description> (Cantina/Immunefi $X)."""
from __future__ import annotations
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Program IDs (verify against sources/<target>/repo/deployments/)
PROGRAM_IDS = {
    "main": "0x...",
}

# Top instructions (from ABI/IDL)
TOP_INSTRUCTIONS: tuple[str, ...] = (
    "function1",
    "function2",
)

# Discriminators and ABIs
def selectors() -> dict[str, str]: ...
def signatures() -> dict[str, list[str]]: ...
def load_abi(repo_path: Path) -> list[dict[str, Any]]: ...
def resolve_accounts(market_hint: str, rpc_url: str) -> AccountResolution: ...
```

### 6.3 Foundry harness

Create `foundry/test/<Target>Measure.t.sol` with:
- `test_<attack_surface>_records_delta` that reads pre/post state and emits a measured delta
- `test_<attack_surface>_exploit` that tries to demonstrate a vulnerability

### 6.4 Measured delta capture

Run the harness on a forked mainnet, capture results in:
`data/security_results/impact/<target>_measured_delta.json`

### 6.5 Promotion gate

A target can be marked `ready` only when:
1. NativeHarness module is complete
2. Foundry harness exists and passes
3. Measured delta is positive (`measured_impact: true`)
4. At least 50 concrete candidates in `concrete_candidates.jsonl`
5. `source_commit` is recorded

### 6.6 Self-documentation

For each new target, create a lab notebook entry:
`data/security_results/lab_notebook/YYYY-MM-DD-<target>-onboarding.md`

With:
- What was cloned
- What the harness covers
- What the measured delta is
- What attack surfaces are identified
- What remains to be explored

---

## 7. Attack Surface Tracking

The system maintains a running list of attack surfaces tried per target. This prevents duplicate effort and helps identify gaps.

### 7.1 Universal attack surface checklist

For every new target, the system should try:

1. **Price manipulation** — oracle price injection, stale reads, multi-block manipulation
2. **Flash loan attacks** — single-tx exploits using borrowed funds
3. **Reentrancy** — cross-function and cross-contract reentrancy
4. **Integer overflow/underflow** — in arithmetic, in state updates, in callback returns
5. **Access control** — missing signer checks, missing owner checks, role escalation
6. **Initialization** — uninitialized proxies, missing init checks
7. **Callback** — unchecked return values, reentrancy via callbacks
8. **Signature replay** — ecrecover without nonce, signature malleability
9. **Front-running** — mempool manipulation, sandwich attacks
10. **Governance** — proposal manipulation, voting power attacks
11. **Token integration** — fee-on-transfer, rebasing tokens, weird ERC20s
12. **Liquidation** — bonus manipulation, debt ceiling bypass
13. **Reward distribution** — rounding errors, emission manipulation
14. **Time manipulation** — timestamp dependence, block.timestamp issues

### 7.2 Surface exhaustion tracking

When all 14 surfaces have been tried for a target with no submittable finding, the target is "surface-exhausted" and should be deprioritized.

---

## 8. Self-Criticism System

The system maintains a running log of:
1. **What hasn't worked** — attack surfaces that produced no bug
2. **What's untried** — attack surfaces not yet explored
3. **What assumptions might be wrong** — false positive candidates to re-verify

This is stored in `data/security_results/self_criticism/`.

### 8.1 False positive verification protocol

For any candidate that claims an integer overflow, reentrancy, or access control vulnerability:

1. **Library override check**: Does the calling contract use a library that has explicit reverts? (e.g., `using SafeCast for *;`)
2. **Reentrancy guard check**: Is there a reentrancy guard or lock?
3. **Access control check**: Is there a role check or signer verification?
4. **Bounded math check**: Is the arithmetic in a `checked` block?

If any of these protections exist, the candidate MUST be re-verified against the actual implementation BEFORE being recorded as a live vulnerability.

### 8.2 Mandatory falsification tests for unchecked-conversion claims

For any claim that depends on an `unchecked` integer conversion:

1. Write a Foundry test that calls the actual library function (e.g., `SafeCast.toInt128(uint256)`) with the overflow value
2. Verify that the test reverts with the expected error
3. Only if the test confirms the overflow is possible, record the finding

---

## 9. v6 Cron Configuration

The v5 cron is `nss-hipif-chain`, daily at 04:00. In v6, this cron is augmented with:

### 9.1 Weekly: target sync

```bash
# Run weekly to discover new targets
python -m night_shift_security.cli.main platform sync --all
python -m night_shift_security.cli.main platform diff
```

### 9.2 Bi-weekly: target rotation

```bash
# Re-rank targets by priority score
python -m night_shift_security.cli.main native rank --by bounty_per_audit
# Archive saturated targets
python -m night_shift_security.cli.main native archive --status saturated --older-than 30d
```

### 9.3 Daily: hunt loop

The existing `nss-hipif-chain` continues to run daily, but with the new target rotation:
- It picks the highest-priority unsaturated target
- It runs the v5 NativeHarness + measured-delta process
- It produces a lab notebook entry

### 9.4 Monthly: strategy reflection

```bash
# Run monthly to adapt the strategy
python -m night_shift_security.cli.main reflection generate
```

This produces a `data/security_results/reflection/YYYY-MM-DD.md` file with:
- What worked this month
- What didn't work
- What new approaches to try
- What targets to deprioritize

---

## 10. Concrete Next Steps for the Agent Picking Up This Spec

### 10.1 Immediate (first session)

1. **Read** `data/security_results/loop/native_harness_status.json` to see current target status
2. **Read** the most recent 5 lab notebook entries to understand the current state
3. **Read** `data/security_results/self_criticism/` (if exists) to see what's been tried
4. **Run** `python -m night_shift_security.cli.main platform sync --all` to see the latest target listings
5. **Decide**: which target to onboard first? Use the priority formula from §4.4

### 10.2 First week

1. **Onboard** the highest-priority new target (recommended: Reserve Protocol)
2. **Build** the NativeHarness module
3. **Build** the Foundry harness
4. **Capture** a measured delta (positive or honest zero)
5. **Document** in the lab notebook

### 10.3 First month

1. **Onboard** 2-3 new targets
2. **Run** the hunt loop on each new target
3. **Identify** attack surfaces that have been tried on existing targets
4. **Document** what hasn't worked and why
5. **Adapt** the strategy based on lessons learned

### 10.4 Hard rules (NEVER violate)

1. **NEVER loosen** `validate_hypothesis()`, `qualifies_for_submission()`, evidence grading, or any gate
2. **NEVER submit** a finding without Kate's human gate approval
3. **NEVER claim** an unchecked-conversion vulnerability without verifying the actual library function
4. **NEVER skip** the falsification test for integer overflow claims
5. **NEVER deprioritize** a target just because it's hard — try multiple attack surfaces first
6. **NEVER accept** a false positive as a "design feature" without re-verifying

---

## 11. What to Do If You Find a Bug

When (not if) the system finds a genuine, submittable bug:

1. **STOP** all other work
2. **VERIFY** the bug with multiple independent tests
3. **DOCUMENT** the bug in detail in the lab notebook
4. **GENERATE** the measured-delta evidence file
5. **PASS** through `qualifies_for_submission()`
6. **GENERATE** `submission_alert.json` with `status=submit_ready`
7. **NOTIFY** Kate for human gate approval
8. **DO NOT** submit externally without Kate's explicit approval

---

## 12. v6 Completion Criteria

v6 is complete when:

1. **G1**: ≥8 targets at `status=ready` in `native_harness_status.json`, ≥4 of them Solana
2. **G2**: Every `ready` target has a positive measured delta
3. **G3**: Every `ready` target has ≥50 concrete candidates
4. **G4**: Cron rotates to new targets automatically (no manual intervention needed)
5. **G5**: At least 1 finding passes `qualifies_for_submission()` with `impact_oracle.measured=true` and Kate's human gate approval
6. **G6**: System maintains a self-documentation trail of what was tried and what was learned
7. **G7**: At least 1 new target onboarded in v6 (from the §5 list)

---

## 13. References

- `AGENTS.md` — agent onboarding and workflow
- `data/security_results/lab_notebook/` — history of all runs (recent v6 entries: `2026-06-20-*.md`)
- `data/security_results/self_criticism/` — what hasn't worked (recent: `2026-06-20-what-hasnt-worked.md`, `2026-06-20-post-reserve-self-criticism.md`, `2026-06-20-orchestrator-handoff-self-criticism.md`)
- `data/security_results/reflection/` — strategy adaptations (recent: `2026-06-20-post-reserve-onboarding-reflection.md`, `2026-06-20-orchestrator-handoff-reflection.md`)
- `foundry/test/UniV4MintOverflowFalsification.t.sol` — VULN-001 falsification (must read)
- `foundry/test/ReserveFalsificationProbe1.t.sol` — Reserve Mandatory Falsification Protocol §8.2 (PASS)
- `foundry/test/EthenaMeasure.t.sol` — Ethena Mandatory Falsification Protocol §8.2 (PASS)
- `tests/test_uniswap_v4_hook_probe.py` — Uniswap v4 hook tests
- `tests/test_native_reserve.py` — NativeHarness smoke tests for Reserve
- `tests/test_native_ethena.py` — NativeHarness smoke tests for Ethena

> **Note (2026-06-20):** the v4.2-era root docs `AUDIT.md`, `BOUNTY_RUN.md`, `SPEC_V5_COMPLETION.md`, and `SYSTEM_AUDIT_2026-06-18.md` were retired. Their substantive content is preserved in the §3 (Strengths/Gaps) + §14 (Version History) sections of this SPEC and the per-version entries of `CHANGELOG.md`. Historical `lab_notebook/` entries still reference those filenames and serve as the immutable record of the pre-v6 reasoning.

---

## 14. Version History

- **v3.x**: Original platform with synthetic param-grid engine
- **v4.0**: Added semantic discovery layer, concrete candidate schema
- **v4.1**: Added self-interrogation gate
- **v4.2**: Added Solodit corpus, AuditVault corpus, agent proposal lane
- **v5.0.0-draft**: Pivoted to NativeHarness substrate (UniV4 hooks, measured delta oracle)
- **v5.0.0-shipped**: Phase 6 cron unpause with 2 ready targets
- **v5.0.0-audit-cycle**: Audited 8 protocols, found VULN-001 (falsified), no submittable bugs
- **v6.0.0-draft**: Target rotation + less-audited-program onboarding + self-evolving loop
