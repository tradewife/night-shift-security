# Changelog

Release notes aligned with `SPEC.md` versions. Package version in `pyproject.toml` (`0.1.0`) is not tracked here.

## [3.2.0] — 2026-06-14

### HIPIF schema + hunt saturation (P1 fixes)
- Extended `CHAIN_SUBGOALS`: `depth_wormhole_bridge`, `kamino_preflight`, `cantina_slates`
- `hipif fold --subgoal <id>` — explicit subgoal folds; deterministic runner uses per-phase IDs
- Fork-ready hunt: `ignore_saturation=True` — hunt slugs not filtered by `saturated_slugs`
- Cantina slates: single fold after all programs (not one fold per slate)

## [3.1.1] — 2026-06-14

### Documentation & audit
- Root doc rewrite: `README.md`, `AUDIT.md`, `CHANGELOG.md`, `AGENTS.md`, architecture, methodology, sustainability
- `day_shift/current.md` handoff aligned to HIPIF primary cron
- SPEC test count corrected (324 passed, 3 skipped)

### Known issues documented
- Hunt rotation starves when fork-ready slugs are saturated (P1-2)
- HIPIF fold `subgoal_id` drift in deterministic runner (P1-1)
- 0 `submit_ready` — gates correct; KLend/Wormhole novel depth in progress

## [3.1.0] — 2026-06-14

### HIPIF all-in-one night chain
- `orchestration/hipif.py` — parse, ground, record, fold hooks; folded context
- `hipif` CLI subcommands; `hermes/skills/hipif/SKILL.md`
- Cron `nss-hipif-chain` replaces week-spread bounty/coordinator crons
- `nss-hipif-chain-run.py` deterministic bounty-depth profile
- Deprecated: `nss-bounty-loop`, `nss-investigate-queue`, `nss-coordinator-kamino` as standalone crons

### Bounty-depth profile (`991ab0c`)
- `NSS_HIPIF_BOUNTY_DEPTH=1` boosts fork/solana top_n, darwinian, MC/CPCV
- 12× Wormhole trials + core/token_bridge triage refinement
- KLend live preflight; 5 trials with `KLEND_PROBE=oracle_staleness_borrow`
- Fork-ready hunt only (wormhole, morpho, euler, ethena)
- Cron bootstrap defaults `NSS_KLEND_FIXTURE=0`

## [3.0.9] — 2026-06-13

- Cantina/EVM slugs use `euler_cantina.json`; `fork_validation.top_n >= 3`
- `NSS_LOOP_DEPTH_SLUG` bypasses saturated-slug skip for depth rotation
- Legacy cron Mon Wormhole / Thu KLend (`nss-bounty-loop-cron.sh`)

## [3.0.8] — 2026-06-13

- KLend mainnet account clone depth (`klend_accounts.json`, `klend_account_discovery.py`)
- Wormhole `testForkWormholeBridgePauserAuthSurface` + pauser fork target
- Hermes cron aligned to bounty-loop skill

## [3.0.5–3.0.7] — 2026-06-13

- Credible harness gate; `klend_require_live`; `HARNESS_MODE` markers
- Live KLend CPI probes (`PROBE_TX_CONFIRMED`); Wormhole getter/governance forks
- Per-probe CPI account metas; Wormhole triage governance forks

## [3.0.0–3.0.4] — 2026-06-12–13

- Operator Layer Phases A–D: task verifier, checkpoint, triage, MCP, Anvil, oracle/TVS
- Wormhole Block B: live program map, `sources/wormhole/recon.json`
- Novel validator CPCV exempt path; Wormhole core/token_bridge live forks

## [2.0.9–2.0.10] — 2026-06-11–12

- Autonomous bounty loop CLI; `program_registry`; human gate
- Deterministic RSI; improvement ledger; refinement hints

## [2.0.0–2.0.8] — 2026-06-08–11

- Immunefi-ready path; shoestring; Kamino target; Hermes integration
- Coordinator; x402 RPC proxy; Day Shift ops; bounty scoring; Cantina screen
- Novel-surface campaigns (KLend, Wormhole)

## [1.4–1.9] — 2026-06-07–08

- Hypothesis generation v1.4; LLM provider v1.5; validation layer v1.7
- Structural filters; findings store v1.9