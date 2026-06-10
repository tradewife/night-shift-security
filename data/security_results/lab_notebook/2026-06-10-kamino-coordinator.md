# Lab entry — 2026-06-10

## Trigger
manual: coordinator bootstrap + scan + first Kamino coordinator cycle (parametric, no delegate proposals)

## Scan queue (dry-run top 3)
- kamino: grade 4, submission_ready=true, analogue=mango-markets-2022
- raydium: grade 4, submission_ready=true, analogue=crema-finance-2022
- orca: grade 4, submission_ready=true, analogue=crema-finance-2022

## Investigated
- kamino: `kamino_shoestring.json`, proposals=none (parametric), campaign=`kamino-immunefi-2026-06`
- coordinator mission: `flash_loan_oracle` (mission_id `bb549078-7da9-4554-92c9-481be6c5bc5f`)

## Delegate proposals vs last run
- First run — no prior proposals JSON in repo.
- Parametric-only cycle (LLM expansion disabled).

## Engine outcome
- Findings: 34 | max grade in debrief: 1 (shoestring track on findings: 4 via fixture)
- solana_reproduced: 90 | catalog_analogue: true | deployed_viable: 0
- findings_store: 93 records, 40 promoted, mean_evidence_grade 1.06
- Shoestring pack: `bounty/shoestring/kamino` (NSS-0001, solana_fixture)
- Debrief: `knowledge/debriefs/bb549078-7da9-4554-92c9-481be6c5bc5f.json`
- Promotion recommendation: `escalate_to_validator` (fixture without deployed_viable)

## Same vs different
First coordinator cycle — no prior lab entry. Baseline established. Next mission queued: `composability_risk` (priority_reason: novelty_gap after flash_loan_oracle retired).

## Update 14:08 UTC — cycles 2–3
- Mission 2 `composability_risk` retired (scoped template fix: 27 vectors vs 93 in cycle 1).
- Next pending: `reentrancy`.
- Coordinator state: 2 missions completed, 1 pending.

## Next action
Run `coordinator cycle` for `reentrancy`. Add Hermes delegate proposals scoped to mission template before cycle 4.

## Skill/recon updates
- Cron 2026-06-09 returned `[SILENT]` — notebook must run even when agent skips investigate.
- Wire `coordinator-cycle` into `nss-investigate-queue` cron recipe.
- Un-ignore `lab_notebook/` in `.gitignore` for versioned entries.