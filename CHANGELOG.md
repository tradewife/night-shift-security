# Changelog

Release notes aligned with `SPEC.md` versions. Package version in `pyproject.toml` (`0.1.0`) is not tracked here.

## [4.2.0] — 2026-06-16

### Solodit Hybrid Corpus
- Added deterministic Cyfrin Solodit findings sync and compact pattern JSONL extraction.
- Pipeline now stamps Solodit analogue metadata on matching candidates before self-interrogation; Solodit data remains advisory and cannot satisfy submission gates.
- HIPIF `scan_all` refreshes Solodit corpus best-effort and skips cleanly when `CYFRIN_API_KEY` is absent.
- Added `solodit-research` Hermes skill and an authenticated proposal cron recipe for next-run untrusted proposals.
- Hardened EVM fork verifier handling so Wormhole triage-surface/catalog-exempt probes with zero measured delta cannot remain `fork_reproduced`; these remain research evidence only and no longer inflate bounty exports.
- KLend live probe telemetry now records on-chain transaction errors (`chain_error` / `PROBE_CHAIN_ERROR`) so failed CPI attempts become actionable failure traces instead of ambiguous zero-delta `ok` probes.
- KLend probe instruction data now uses source-derived v2 instruction names and Borsh argument serialization, moving the oracle borrow probe from Anchor deserialization failure (`Custom 102`) to actionable incomplete-account-meta failure (`Custom 3002`).
- KLend oracle borrow probe now uses source-derived account metas, derived user metadata/vanilla-obligation/USDC ATA setup, cloned USDC/SOL mint accounts, and cloned Farms executable program. Live failure advanced through account wiring errors (`3002`, `3007`, `3009`) to KLend lending checks (`6009` `ReserveStale`, intermittently `6007` `MathOverflow`) with zero measured protocol delta.
- KLend validator replay now warps current-state clones to the source RPC slot, parses Scope oracle accounts from reserve state, prepends `refresh_reserve` / `refresh_obligation`, and captures transaction logs. Latest live blocker is `oracle_price_too_old`: Scope USDC price/TWAP are too old, leaving borrow reserve price status `00110101` and zero protocol delta.
- Wormhole failure-trace RSI now classifies triage-surface/no-delta fork evidence as `missing_economic_impact` and routes the next action to `generate_value_moving_poc`, while fork evidence stamps `economic_impact_verified=false` for triage-only Wormhole surfaces.
- Added a live Wormhole token-bridge value probe that checks malformed `completeTransfer` cannot move USDC or alter `outstandingBridged(USDC)` on a mainnet fork; the runner records it with `WORMHOLE_VALUE_PROBE` and downgrades it as missing economic impact.
- Extended the Wormhole value probe with a mocked-authorized signed-message baseline that moves exactly 1 USDC through deployed token-bridge accounting and marks `HARNESS_AUTH_MOCKED=1`; Wormhole economic gates now reject mocked authorization even when token delta is positive.
- Tests: 405 passed, 5 skipped in full local run; focused Solodit/self-interrogation/pipeline suite 66 passed; focused KLend probe suite 13 passed; focused Wormhole RSI/economic suite 29 passed; live Wormhole Foundry value probe 2 passed.

## [4.1.0] — 2026-06-16

### Adversarial Self-Interrogation
- Added deterministic `validation.self_interrogation` reports that challenge candidate assumptions before CPCV, Monte Carlo, fork, and Solana validation spend.
- Reports stamp candidate metadata with `self_interrogation`, `conviction_score`, and `conviction_action`.
- Default config enables advisory reports without changing pass/fail behavior.
- HIPIF bounty-depth configs now enable small conviction-based rank pressure so stronger candidates reach top-N validation lanes first.
- Tests: 385 passed, 5 skipped, 3 deselected in sandbox-safe run; focused self-interrogation/pipeline suite 60 passed.

## [4.0.1] — 2026-06-16

### NightSoul Cron PATH Fix
- Fixed the 04:00 `nss-hipif-chain` failure where cron's stripped PATH could not find `solana-test-validator`.
- Added canonical Solana active-release binary discovery via `SOLANA_VALIDATOR_BIN`, PATH, and `~/.local/share/solana/install/active_release/bin`.
- Updated Solana validator replay execution to pass the resolved validator binary instead of relying only on `shutil.which`.
- Reinstalled the patched wrapper into the active `nightsoul` profile and verified a full no-agent run completed 13/13 folds with `gate_ok=true`.
- Tests: 54 passed (`test_solana_rpc`, `test_bounty_loop`, `test_klend_live_probes`, `test_hipif`).

## [4.0.0] — 2026-06-15

### Cron Hardening + Target Refresh
- Switched `nss-hipif-chain` default cron mode to no-agent deterministic full runner (`--phase full`) so cron success requires the Python runner to reach final `hipif gate`.
- Converted installed `nightsoul` 04:00 job to no-agent mode and cleared agent skills from that cron record.
- Refreshed current Cantina target coverage from `cantina.xyz/opportunities`: added dYdX and Paxos to the curated registry; expanded default Cantina slates to `uniswap,reserve-protocol,euler,polymarket,coinbase,morpho,pendle,okx,paxos`.
- dYdX is tracked as a current target but excluded from default slates until a Cosmos SDK/CometBFT harness exists.

### Semantic Discovery Baseline
- Added semantic recon for Solidity, Rust/Solana, and Anchor IDL with entrypoint, authority, value-flow, oracle, and bridge artifacts.
- Added concrete v4 candidate schema/store plus `semantic map` and `semantic candidates` CLI.
- Generated Wormhole semantic artifacts: 606 production entrypoints, 559 bridge candidate seeds.
- Added Opengrep/Semgrep rule ingestion and scoped off-chain recon wrappers.
- Added candidate-specific fail-closed PoC generation/verification for Foundry and Solana.
- Added KLend v2 instruction discriminators, typed account roles, account diffs, probe results, and failure classifiers.
- Added Wormhole economic-impact fixtures/gates so triage-only surfaces remain research-only.
- Added Failure Trace RSI summarization into failure signatures and refinement hints.
- Hardened target-pinned proposals, `bounty loop --target`, HIPIF cron truth checks, and v4 submit-ready candidate requirements.
- Tests: 374 passed, 5 skipped, 3 deselected in sandbox-safe run; full suite blocked only by local socket restrictions in 3 API tests.

## [3.3.0] — 2026-06-14

### Bounty Platform Intelligence + Submittable Export
- `platform sync` / `platform diff` — Immunefi listing scrape (208) + Cantina API (52 live bounties)
- `data/security_results/platform/{immunefi_programs,cantina_programs,scope_registry}.json`
- Split export: `bounty/research/` (grade ≥ 3) vs `bounty/submittable/` (`qualifies_for_submission()` only, max 1/program)
- PoC bundler — runnable `forge test` / KLend harness wrappers (no TODO Solidity stubs on fork repro)
- IVSS v2.3 sections in submittable markdown (Brief, Details, Impact, Risk, Recommendation, References)
- Registry: Wormhole $1M cap; Tier-A adds jito, layerzero, gmx, sky, onre, uniswap (Immunefi); kiln, li.fi, pancakeswap, okx, chronicle-labs (Cantina)
- Harness: `coinbase_cantina.json`, `polymarket_cantina.json`, `reserve_protocol_cantina.json` (no more `wormhole_fork.json` for coinbase/polymarket)
- Scan: `scan_grade3_plus` + `submittable_candidate`; `submission_alert.json` schema v2; `operator-submit` skill
- HIPIF defaults: Cantina slates `reserve-protocol,coinbase,morpho,euler`; hunt adds `jito`
- **344 tests** (+16)

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
