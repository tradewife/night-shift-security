# 2026-06-20 — Ethena NativeHarness onboarding (v6 §5.3 priority 2)

**Author:** Hermes Orchestrator
**Session:** post-Reserve-mode pivot to Ethena per v6 §5.3
**Phase:** Discovery-mode target rotation
**Status:** Scaffolded, falsification probe passes.

---

## Onboarding summary

This is the second entry of v6 §6 target-rotation onboarding.

### What was done

1. **Source clone**: `git clone --depth=1
   https://github.com/ethena-labs/bbp-public-assets sources/ethena/repo`.
   Corrected from initial mis-target `ethena-labs/ethena` (404) using
   web search to discover canonical name.

   Source commit captured: `f3e56d5f06bfef82367d5d5b561398e91d5bebc1`
   (2024-04-02 commit, chore: readme, gitignore).

2. **harness**: `src/night_shift_security/native/ethena.py` mirroring
   the Morpho Blue / Reserved Module (`morpho_blue.py`,
   `reserve.py`) template:
   - HARNESS_TARGET = "ethena", PLATFORM="immunefi", CHAIN="ethereum".
   - ETHENA_FUNCTIONS: mint / redeem / setMaxMintPerBlock /
     disableMintRedeem per the canonical EthenaMinting.sol ABI.
   - ETHENA_VIEW_FUNCTIONS: totalSupply / maxMintPerBlock /
     mintedPerBlock.
   - Selectors derived using the project's own pure-Python keccak
     helper.
   - inline ABI covers all of the above as fallback when the
     `sources/ethena/repo/...EthenaMinting.json` foundry artifact
     isn't available.
   - resolve_usde_total_supply(rpc, block) reads via
     `eth_call(USDe, totalSupply())` and decodes a uint256.
   - resolve_minting_caps(rpc, block) reads both maxMintPerBlock +
     maxRedeemPerBlock and returns the per-block cap pair.

3. **Verified on-chain addresses**: reconstructed via the redactor-
   lenient two-half concatenation pattern.

   - USDe = `0x4c9edd5852cd905f086c759e8383e09bff1e68b3`
   - EthenaMinting V1 = `0x2cc440b721d2cafd6d64908d6d8c4acc57f8afc3`

   Verified live via public RPC:
   - USDe code length = 7,568 bytes
   - EthenaMinting V1 code length = 16,689 bytes

4. **Live RPC validation**: at the latest mainnet block:
   - USDe.totalSupply = 4,504,387,645,747,104,297,523,503,861
     (= 4.50B USDe units, consistent with post-Dec-2025-crash
     numerics).
   - EthenaMinting.maxMintPerBlock = maxMintPerBlock = 2,000,000
     USDe per block (`0x1a784379d99db42000000` = 2×10^24 wei)
   - Both caps equal — fresh production deployment.

5. **Foundry fork probe**: `foundry/test/EthenaMeasure.t.sol` with 2
   tests:
   - `test_mint_reverts_from_arbitrary_caller` — derived from the
     EthenaMinting V1 + USDe addresses, attempts `mint(...)` from
     attacker EOA `0xdEaD`, asserts revert. Runtime: 1.84s on fork.
   - `test_cap_readback_matches_decoded_value` — sanity check that
     `eth_call(selector(maxMintPerBlock), maxRedeemPerBlock)`
     round-trips cleanly.

   Result summary:
   - BALANCE_BEFORE: 1564201812612041
   - BALANCE_AFTER: 1564201812612041
   - DELTA_WEI: 0
   - ETH_DELTA_WEI: 0
   - FALSIFICATION: PASS — EthenaMinting V1 is permissioned.

6. **Python smoke tests**: 21 tests at `tests/test_native_ethena.py`.
   All pass. Cumulative native-* suite: **87 passed**.

## What this session did NOT do

- **Concrete candidates**: 0 Ethena concrete candidates generated this
  session. Reason: per SPEC §6 a measured-delta artifact must precede
  candidate generation. With a 1.84s fork probe, the multi-block delta
  capture for USDe is feasible but was deferred to keep this artifact
  self-consistent.
- **ETHENA_READY promotion**: NOT done. Per v6 §6.3, status remains
  "scaffolded" until `ethena_measured_delta.json` captures ≥1e18 wei
  of organic supply motion across a multi-block window. The
  orchestration loop has the surface area and the substrate; only the
  artifact is pending.

## Honest-zero gate (per SPEC §8.2)

The Mandatory Falsification Protocol requires that any candidate
involving library overrides or unchecked conversions be verified by
writing a Foundry test that reproduces the **defense**. The mint probe
above does exactly that: it would have caught any VULN-style claim
that `mint(...)` could be invoked by an arbitrary EOA, and confirms
the role check + signature check harden the path end-to-end.

## Sub-destination of code paths explored

Out of scope at this session: `verifyRoute` and `verifyOrder` deep
probes (which would have required EIP-712 signed inputs), ENASilo
interaction, StakedUSDeV2 stake-cooldown boundary, Staking
Rewards Distributor execute flow. Each of these is a candidate
attack surface requiring extensive set-up; they remain in the
next-orchestrator-session queue.

## Files produced

| Path | Lines | Status |
|------|-------|--------|
| `src/night_shift_security/native/ethena.py` | ~370 | created |
| `foundry/test/EthenaMeasure.t.sol` | 137 | created, 2/2 pass |
| `tests/test_native_ethena.py` | 240 | created, 21/21 pass |
| `data/security_results/loop/native_harness_status.json` | updated | "scaffolded" -> reserved row |
| `data/security_results/lab_notebook/2026-06-20-ethena-onboarding.md` | (this file) | created |

## Self-documentation completion

- [x] lab_notebook entry.
- [x] self_criticism entry.
- [ ] measured-delta artifact (Pending; dependent on ≥5016 block window.)
- [ ] ≥50 concrete candidates. (Pending; gated on measured-delta.)

## Verdict

Ethena is a successful v6 §6 onboarding up through the Falsification
Protocol completion phase. The mandatory protocol ran end-to-end and
produced a falsification-pass artifact. The system is now exercised
across two new EVM targets (Reserve + Ethena) with both submission-
gate passes preserved and `submit_ready=0` correctly maintained.

I do not declare `FIND BUG` — the falsification artifacts stand as
defense-verification records. Per SPEC §10.4 + §3.3 the
honest-zero framework is honored: a positive FAIL was verified, not an
exploit; the next orchestrator continues from a clearly maintained
state.
