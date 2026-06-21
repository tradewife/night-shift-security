---
name: day-shift-cycle
description: Use at Day Shift session open and close — read plan, execute blocks, verify, self-audit, hand off to Night Shift, write next session plan.
---

# Day Shift Cycle

Session-based operator workflow for Cursor (Day Shift). Complements Hermes cron (Night Shift).

## Session open

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull --ff-only
```

Read in order:

1. `data/security_results/day_shift/current.md` — active plan and block checkboxes
2. `data/security_results/lab_notebook/*.md` — newest first
3. `SPEC.md` (the operator command cookbook has been folded into `SPEC.md` §15 from the v4.2-era `BOUNTY_RUN.md`, which was retired on 2026-06-20)
4. `~/.hermes/profiles/night-shift/cron/output/` — last `nss-hipif-chain` run (if present)
5. `data/security_results/intel/latest.md` — optional, ≤5 bullets

If `current.md` missing or `Status: done`, promote `next.md` → `current.md` or bootstrap from SPEC Next Focus.

## Execute

- Work blocks top-to-bottom; mark `[x]` in `current.md` as each completes
- Long runs: background shell + `Await`; log exit codes in plan file
- Do not start new blocks if a blocker is hit — escalate once, then stop

## Verify

```bash
.venv/bin/python -m pytest
```

Plus block-specific proof (examples):

```bash
export SOLANA_MAINNET_RPC_URL=http://127.0.0.1:18989
export SOLANA_USE_VALIDATOR=1
SOLANA_EXPLOIT_ID=mango-markets-2022 ./solana/run_validator_test.sh
```

## Self-audit checklist

| Check | Pass criterion |
|-------|----------------|
| Trust boundary | No gate bypass; proposals untrusted until pipeline validates |
| Provenance | Lab notebook includes same vs different |
| Ultrafuzz | Discovery/harness/fuzzing claims used `ultrafuzz-discovery`; Solana invariant sequence fuzzing prefers Crucible when feasible; real fuzzing is separated from fixed replay |
| SPEC | Shipped work reflected in SPEC if material |
| Diff discipline | Changes serve session blocks only |
| Handoff | Night Shift section filled in plan |

Record in plan: `Audit: pass | fix_deferred | blocked`

## Session close

1. Skill `lab-notebook` — repo entry under `data/security_results/lab_notebook/`
2. Set `Status: done` in `current.md`
3. `mv current.md` → `data/security_results/day_shift/archive/YYYY-MM-DD-<slug>.md`
4. Write `data/security_results/day_shift/next.md` (next session plan)
5. Copy `next.md` → `current.md` when Kate says start next session (or leave `next.md` queued)
6. Optional: refresh `data/security_results/intel/latest.md` if intel slice ran

## Night Shift handoff template

```markdown
## Night Shift handoff
- Cron OK: nss-hipif-chain daily 04:00 (agent + hipif skill; deterministic fallback if no OAuth)
- Cron skip / deprioritize: saturated slugs in loop/state.json; assays Day Shift already completed
- Platform: weekly platform sync --all; platform diff before external submit
- Open questions for Kate: ...
```

## Escalation

Single message to Kate: blockers, policy gates, priority forks only.

## Gotchas

- Session ≠ calendar day — close when Kate says done or all blocks + audit complete
- x402 proxy port **18989** (not 18789 — NSS API tests)
- Dedicated wallet only: `solana/x402-proxy/.wallet/id.json`
- Intel timebox 30 min — no infinite Twitter