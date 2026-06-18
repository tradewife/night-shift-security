# Lab notebook — 2026-06-19 v5 operator cron apply + completion spec

## Operator follow-up (Phase 6)

Applied live `nightsoul` cron configuration after Phase 6 code landed (`9c90cea`).

| Step | Result |
|------|--------|
| `bash hermes/install-nightsoul-overlay.sh` | Synced v5 `nss-hipif-chain.sh` to profile |
| `hermes config set cron.script_timeout_seconds 10800` | Fixed 120s timeout that killed 2026-06-19 04:00 run |
| `hermes cron edit 343324bfcbb2 --no-agent --clear-skills --script nss-hipif-chain.sh --prompt ""` | Cleared stale v4.1 hybrid agent prompt |
| Repo `.env` | `NSS_HIPIF_PAUSE_FOR_NATIVE=0`, `NSS_PHASE4_ROTATION_ENABLED=1`, `HERMES_CRON_SCRIPT_TIMEOUT=10800` |
| Dryrun verify | `pause_for_native=0 bounty_depth=1 script_timeout=10800` |

Next `nss-hipif-chain` run: 2026-06-20 04:00 AEST (job `343324bfcbb2`).

## Completion spec

Wrote [`SPEC_V5_COMPLETION.md`](../../../SPEC_V5_COMPLETION.md) — maps `SYSTEM_AUDIT_2026-06-18.md` phases 1–4 + C1–C9 to phases **7–12**:

- **G1–G5** completion criteria (8+ ready harnesses, 4+ Solana, first `submit_ready`)
- **Solana priority:** kamino ($1.5M, upgrade KLend) → jito ($2M) → raydium → orca
- **Phase 7 next:** `native/kamino.py` skeleton + Morpho liquid-market close-out
- **Phase 8:** `impact/solana_measured_oracle.py` — end fee-only CPI as sole signal

Operator doc: [`hermes/cron/OPERATOR_APPLY.md`](../../../hermes/cron/OPERATOR_APPLY.md).