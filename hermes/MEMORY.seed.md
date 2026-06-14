# Night Shift Security — Lab Notebook (Hermes Memory)

Persistent research log for the `night-shift` profile. Append after every scan, investigation, or significant triage session.

## Active campaigns

- `kamino-immunefi-2026-06` — Kamino shoestring; catalogue analogue mango-markets-2022

## What to record each run

1. **Run id** + date + which cron/manual triggered it
2. **Scan queue** — top targets from `bounty loop` / `investigate --dry-run` (not assumed Kamino)
3. **Delegate delta** — what proposals differed from last run (templates, param ranges, notes)
4. **Engine outcome** — findings count, max evidence grade, submission_readiness, catalogue vs novel
5. **Same vs different** — explicit comparison to previous run on same target
6. **Next action** — one concrete follow-up (recon update, template tweak, escalate, discard)

## Repo mirror

Canonical dated entries also go to:
`data/security_results/lab_notebook/YYYY-MM-DD-<slug>.md`

Commit notebook + findings artifacts when pytest passes (SOUL full-auto policy).

## Cron layout (2026-06-14, SPEC v3.3.0)

- Primary: `nss-hipif-chain` daily 04:00 — skill `hipif` + bounty-depth runner (`NSS_HIPIF_BOUNTY_DEPTH=1`, `NSS_KLEND_FIXTURE=0`)
- Deterministic fallback: `nss-hipif-chain-run.py --init` or `NSS_HIPIF_MODE=deterministic`
- RSI: inline after bounty-loop ticks + skill `recursive-improvement`
- Gate: `operator-submit` on `submission_alert.json`; export `bounty/submittable/` gated
- Profile: re-run `./hermes/install-profile.sh` after skill changes

## Open questions

- (none yet)

## Lessons / Gotchas

- (accumulate here and in skill Gotchas sections)