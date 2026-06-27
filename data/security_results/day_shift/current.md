# Session plan — v6.29 Variational deep-dive

**Status: closed** (2026-06-28) — v6.29/session-32 Variational sidecar.
**Verdict:** **Bug confirmed — Severity downgraded from Critical to Medium.** The "permanent freeze" claim was falsified by Human Gate analysis. Provider-issued fresh withdrawal UUIDs can always recover funds.

## Summary

Onboarded a new EVM target (Variational, Arbitrum, Immunefi, $100k critical max) from on-chain source recovery + Foundry harness. 19 property tests all pass + fork-based bytecode verification. The `batchDepositUSDCAtomic` loop bug is REAL and deployed, but the impact is a recoverable accounting error, not a permanent freeze.

### Key findings

1. **H1: batchDepositUSDCAtomic creator over-deposit** — The deployed code (9108B runtime bytecode at `0x8db6c8b7...`, verified identical to compiled source) deposits `creatorPartyAmountRequested` N× for an N-item batch because it never resets the variable to 0 in the loop. **Confirmed — Medium.**

2. **"Permanent freeze" FALSIFIED** — The provider (PROVIDER_ROLE) can always issue fresh withdrawal UUIDs (any non-zero, unused uint128). Funds are recoverable. Pool remains solvent (claims = balance). The `uuid=0` dedup bypass is an engineering gap that makes provider cooperation necessary but does NOT cause permanent loss.

3. **Bytecode verification** — On-chain runtime = compiled runtime exactly (9108B each), identical function dispatcher. Only the Solc metadata CBOR hash differs. Proxy is custom (NOT EIP-1967), with `implementation()` returning `0x8db6c8b7`. Admin = `0x8e4d1Ad423E4f37600CdA314fD3d99629CeAEABF`.

4. **Human Gate verdict: DO NOT SUBMIT AS CRITICAL** — Under Immunefi rules: (a) "permanent freezing" does not apply (provider remediation exists), (b) "direct theft" does not apply (excess goes to solvent pool, not attacker), (c) centralization risk exclusion applies (all fund movement requires PROVIDER_ROLE). Recommended: Medium.

### Adversarial probe results

| Hypothesis | Result | Notes |
|---|---|---|
| H1: batchDepositUSDCAtomic creator over-deposit | **CONFIRMED — Medium** | Pool holds 40M instead of 35M (N=2, X=5M). Creator overcharged (N-1)×X. |
| PROP-VAR-006: uuid=0 bypass | Confirmed | `transfers_processed[0]` never written |
| PROP-VAR-014b: "permanent freeze" | **FALSIFIED** | Provider-issued fresh UUIDs always work for withdrawal |
| PROP-VAR-015: OLP routing without pool validation | Confirmed, documented | Provider-gated by design |
| PROP-VAR-001..030 property table | 30 properties mapped | Full coverage |

### Test results

**19/19 passed** (VariationalFalsifier), plus additional 57 non-variational. Total: **76 passed, 14 skipped, 0 failed**.

## Submission gate status

| Gate | Status |
|---|---|
| bug_exists | true |
| severity | **Critical→Medium (downgraded by Human Gate)** |
| submit_ready | **0** — do not submit as Critical |
| human_gate | **COMPLETE** — see `adjudication/H1_human_gate_report.json` |

## References

- `data/security_results/investigations/2026-06-28-v6-29-variational-sidecar/`
- `data/security_results/lab_notebook/2026-06-28-v6-29-variational-sidecar.md`
- `data/security_results/investigations/2026-06-28-v6-29-variational-sidecar/adjudication/H1_human_gate_report.json`
- `foundry/test/VariationalFalsifier.t.sol`
- `foundry/test/VariationalForkVerification.t.sol`
- `sources/variational/repo/source_manifest.json`
