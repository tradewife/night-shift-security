# Lab entry — 2026-06-09

## Trigger
cron: `nss-investigate-queue` (manual `cron run` + `cron tick` smoke test), then manual `investigate` to complete failed step.

## Scan queue (dry-run top 3)
- **kamino**: grade 4, submission_ready, analogue `mango-markets-2022`
- **raydium**: grade 4, submission_ready, analogue `crema-finance-2022`
- **orca**: grade 4, submission_ready, analogue `crema-finance-2022`

## Investigated
- **kamino**: `data/security_results/investigations/kamino-investigate.json`, proposals `hermes_proposals/latest.json`, campaign `immunefi-kamino-2026-06`
- **raydium**: `data/security_results/investigations/raydium-investigate.json`, same proposals file, campaign `immunefi-raydium-2026-06`

## Delegate proposals vs last run
- **New**: first proposals file `2026-06-09-top2.json` (3 variants: 2× flash_loan_oracle, 1× composability_risk)
- **Repeated**: N/A (first cron expansion run)
- **Ingested**: Raydium run shows `llm_composability_risk_*` vectors — external bridge accepted composability proposal

## Engine outcome
- **Kamino**: 35 findings, max grade 4 (fixture), catalogue-heavy rediscovery 7/19
- **Raydium**: 34 findings, max grade 4 (fixture), shoestring pack exported
- **Novel vs catalogue**: catalogue / fixture replay — not novel live-target bugs

## Same vs different
First end-to-end outer loop. Cron agent wrote proposals but **did not run investigate** (wrong `--proposals` position after subcommand). Manual completion with `--proposals … investigate` ran both targets. Delegate params differ from default grid (e.g. `loan_fraction_of_ceiling: 0.92`).

## Next action
Fix `investigate-from-scan` skill CLI examples (`--proposals` is a **global** flag, must precede `investigate`). Re-run cron or wait for 2026-06-11 scheduled tick.

## Skill/recon updates
- **Gotcha**: `main.py investigate --proposals X` fails; use `main.py --proposals X investigate …`
- **Gotcha**: Cron `[SILENT]` suppressed delivery; lab-notebook step was skipped by agent despite skill load order
- **Gotcha**: Subagent `python -c` blocked in cron (no TTY for dangerous command approval)