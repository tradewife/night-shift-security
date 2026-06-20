Frame 3 — Kamino flash-callback CPI composition.

**Question:** Can a CPI into Kamino's own `refresh_reserve` / `deposit_reserve_liquidity` be invoked between flash_borrow and flash_repay, OR can a top-level non-Kamino instruction in the same tx mutate reserve state in a value-extracting way tied to the repay fee?

**Verdict:** Falsified. See `attempt.md`. The flow of defense is layered: (1) `is_flash_forbidden_cpi_call` blocks both depth-CPI AND cross-program-ix between borrow+repay; (2) `flash_borrow_check_matching_repay` enforces byte-identical account layout for the pair; (3) the repay fee is independent of reserve state. Frame 3 confirms frame 1's conclusion independently.

**Status:** empirical-FNR datapoint candidate. Note cross-frame redundancy (frames 1 + 3 both reach "repay-fee is static-config-only" via different lens).

**Files in this artifact:**
- `attempt.md` — flow analysis + reproduction reasoning + reflection.
- `evidence.json` — falsification evidence envelope with four source anchors.

**Final hand-off:** Three frames complete. Joint superset → Quorum file (`data/security_results/investigations/2026-06-21-v6-3-quorum.md`).
