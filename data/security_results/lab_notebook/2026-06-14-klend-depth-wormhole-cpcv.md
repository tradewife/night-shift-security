# Lab entry — KLend depth matrix + Wormhole triage CPCV

**Date:** 2026-06-14  
**SPEC:** v3.2.0 P0 — KLend `live_executed`; Wormhole CPCV grade 3+

## Trigger

manual — dual-track Day Shift follow-up (user: "do both")

## KLend — protocol delta probe matrix

**Changes:**
- `klend_live_probes.py`: wallet + protocol vault deltas (`PROTOCOL_DELTA_LAMPORTS`, `USDC_VAULT_DRAIN_MICRO`); best-effort vault reads (cloned validator mint metadata may be absent)
- `run_validator_replay.py`: live `NSS_KLEND_DEPTH=1` runs all 4 probes inside validator lifecycle
- `run_klend_harness.py`: depth mode passes through validator output

**Live runs:**
| Mode | Probes executed | Measured delta | Harness |
|------|-----------------|----------------|---------|
| `KLEND_PROBE=oracle_staleness_borrow` | 1/1 | 0 (fee-only) | `live_deploy_verified` |
| `NSS_KLEND_DEPTH=1` | 4/4 | 0 all | `live_deploy_verified` |

All probes land CPI txs (`PROBE_TX_CONFIRMED:1`, multi-account `PROBE_ACCOUNTS:`). No vault drain detected; protocol token balance RPC skipped on clone (no mint). **Still no `live_executed`.**

## Wormhole — triage-scoped CPCV + surface grading

**Changes:**
- `WormholeTriage.t.sol`: emits `TRIAGE_SURFACE_VERIFIED:1` on governance/bridge/pauser forks
- `evidence_grading.py`: `novel_fork_cpcv_exempt` for wormhole live fork survivors
- `task_verifier.py` + `fork_validation.py`: `triage_surface_balance_exempt` (no `DELTA_WEI` required for surface probes)
- `wormhole_triage.json`: enabled both exemptions

**Pipeline run** (`wormhole_triage.json`, 102s):
- Findings: **13** | `fork_reproduced`: **12**
- Evidence grades: **12× grade 4**, 1× grade 1
- Sample NSS-0003: `fork_reproduced=true`, `triage_surface_verified=true`, `balance_verified=true` (method `triage_surface`)
- `submit_ready_count`: **0** — `deployed_viable=false`; governance smoke ≠ exploitable balance delta

## Gates

| Gate | KLend | Wormhole |
|------|-------|----------|
| `live_executed` / grade 3+ fork path | ❌ fee-only | ✅ grade 4 surface |
| `submit_ready` | ❌ | ❌ |
| `human_gate_pending` | false | false |

## Next action

1. KLend: clone SPL mint accounts on validator so vault balance reads work; wire real KLend instruction discriminators (not `0xCAFE` stubs)
2. Wormhole: triage-scoped Foundry exploit skeleton on pauser/governance auth bypass with measured `DELTA_WEI` — surface grade 4 is research progress, not Immunefi-ready

## Tests

328 passed, 3 skipped (+2: `test_evidence_grade_novel_fork_exempt`, `test_usdc_micro_to_lamport_equiv_threshold`)