## STRAT-S16 — Exhaustive Lombard Hard-First Persistent Looping Orchestration Spec

**Version**: v6.51.18-lombard-r1-r6-strat-s16-rigor-reopened

**Predecessor**: v6.51.17 STRAT-S15 (closed acceptable tier, 6 gaps: R3 5→2 strands silent drop, RSI unwritten, R4 no forensic log, N5 no substrate-precondition assertion, 18 vs 27 skills, no delivered_vs_promised tracking)

**Primary Target Subsystem** (unchanged): `release_or_mint/lock_or_burn` ↔ `mailbox.handle_message` ↔ `bridge.gmp_receive` ↔ `consortium` ↔ `bascule/bascule_gmp`

### Key Reinforcements (6 items):

1. **Spec Promised → Delivered gate**: each round writes `delivered_vs_promised.json`. Silent drops forbidden; round-level `engineering_blocker` reclassification used instead.
2. **Substrate-precondition assertion**: N6 extends N5 by asserting the path actually wrote Handled byte before the rollback (proves substrate was exercised).
3. **Zero-survivor forensic log**: R4 must produce forensic log even on no survivors — capturing candidate space searched, kill classifications, and corpus consulted.
4. **RSI ledger mandatory per closure**: `recursive-improvement` writes `improvement_ledger.jsonl` entry every round, even on zero survivors.
5. **Full 27-skill inventory check** at session start (20 NSS research + 7 plumbing). Per-round ladder opens with `codegraph-x-ray` + `ultrafuzz-discovery` and closes with `recursive-improvement` + `lab-notebook`.
6. **R7 spec-compliance audit**: after R6 closure, audits all rounds' `delivered_vs_promised` against spec commitments.

### Round Structure (R1-R7):

- **R1**: N5 preserved + N6 substrate-precondition assertion (new). 2 strands. Validator substrate.
- **R2**: R7 actions `engineering_blocker` preserved. R8 retry with `crucible tmin`. PROP-CR-008 same-PDA collision Rust probe added. 2 strands.
- **R3**: 5 strands × ≥3 fresh-context trials = 15/15 strictly enforced: (1) PROP-CR-007 mid-session rotation, (2) PROP-TP-002 destination_caller, (3) PROP-TP-003 multi-decimal, (4) PROP-MBOX-005/006 fee race, (5) PROP-EVM-MBOX-005 cross-layer refund. If incomplete, round-level `engineering_blocker` with inherited strands.
- **R4**: Forensics on survivors. Zero-survivor forensic log mandatory.
- **R5**: Bounty-loop + RSI ledger write (mandatory) + lab-notebook.
- **R6**: Closure adjudication — Best (≥5 HZ, qualifies) / Acceptable (≥3 HZ, deliv_vs_prom all good) / Last Resort (dim-returns with ledger).
- **R7**: Spec-compliance audit across R1-R6.

### Hard Rules:
1. No silent skip — each round opens with codegraph-x-ray + ultrafuzz-discovery; closes with lab-notebook + recursive-improvement
2. engine_level_honest_zero reserved for engine limits; validator/Crucible backed uses validator_backed_honest_zero/crucible_honest_zero
3. 3+ fresh-context attempts per property
4. Failure preservation + crucible tmin before adjudication
5. Substrate precondition assertion in every validator replay
6. submit_ready invariant (0 unless Best tier)
7. Round-level engineering_blocker reclassification honest and documented

### Evidence artifacts per round:
- R1: evidence/strat-s16-r1-validator-path-assert.log
- R2: evidence/strat-s16-r2-crucible-tmin.log, programs/consortium/src/utils/same_pda_collision_probe.rs
- R3: evidence/strat-s16-r3-(clean|eb)-adjudication.log, sources/lombard-finance/repo/tests/ccip.ts (N7, N8)
- R4: evidence/strat-s16-r4-zero-survivor-forensic-log.json
- R5: improvement_ledger.jsonl entry, lab-notebook entry
- R6: summary.json, runs.jsonl, SPEC.md, CHANGELOG.md
- R7: evidence/strat-s16-r7-compliance-audit.json