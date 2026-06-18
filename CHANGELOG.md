# Changelog

Release notes aligned with `SPEC.md` versions. Package version in `pyproject.toml` (`0.1.0`) is not tracked here.

## [5.0.0-draft] — 2026-06-18

### v5 pivot — NativeHarness substrate
- Recorded the 2026-06-18 directed audit at `SYSTEM_AUDIT_2026-06-18.md`. Eight structural defects upstream of the gates describe why v4.2.0 stayed at `submit_ready=0`. The gates, trust boundary, RSI, lab notebook, and skill lockdown remain authoritative; the discovery substrate pivots.
- Added `src/night_shift_security/native/__init__.py` (manifest schema + upsert + read) and a new CLI subcommand group `native status`, `native mark`. Manifest lives at `data/security_results/loop/native_harness_status.json`.
- Cron bootstrap (`hermes/scripts/nss-hipif-chain.sh`) now refuses to run the legacy chain when `NSS_HIPIF_PAUSE_FOR_NATIVE=1` (the default) and no target in the native-harness manifest has `status=ready`. Set `NSS_HIPIF_PAUSE_FOR_NATIVE=0` to revert to legacy v4.2 chain.
- Updated SPEC.md version to `5.0.0-draft` with new §0 "Why this version exists"; AUDIT.md records v4.2.0 closure + v5 Pivot section; hermes cron example YAML updated.
- Added `tests/test_native_harness.py` covering: empty state, upsert + ready counter, missing file fallback, garbage file fallback, default path, full round-trip persistence. 6 tests.
- First target = `uniswap_v4` ($15.5M Cantina pot) marked as `mapped` (ABI/IDL/source still required to reach `ready`).
- Tests: **444 passed, 5 skipped** (was 438 → +6 net new).

### 2026-06-19 — v5 first NativeHarness shipped (audit C1)
- Cloned `sources/uniswap_v4/repo` (v4-core @ commit `46c6834698c48bc4a463a86d8420f4eb1d7f3b75`); added `sources/uniswap_v4/repo/` to `.gitignore` next to the Wormhole/Kamino/AuditVault clones.
- Ran `semantic map --slug uniswap_v4 --repo sources/uniswap_v4/repo`: 46 files, 72 entrypoints, 18 value_flows, 1 authority_signal; promoted 66 concrete candidates into `data/security_results/knowledge/concrete_candidates.jsonl` (559 → 625). Coverage spans `PoolManager.{initialize,modifyLiquidity,swap,donate,settle,settleFor,take,mint,burn,transfer,unlock,…}` and all 10 `IHooks` before/after entrypoints plus `StateView.{getSlot0,getLiquidity,getFeeGrowthGlobals}`.
- Added `src/night_shift_security/crypto/__init__.py` — pure-Python Keccak-f1600 helper (no pycryptodome / pysha3 dependency). Cross-checked against canonical Ethereum vectors (`keccak256("") == c5d2460186f7…470`).
- Added `src/night_shift_security/native/uniswap_v4.py` — first per-target NativeHarness. Public surface: `selectors()` / `signatures()` / `load_abi()` / `resolve_pool()` / `PoolKey` / `PoolResolution`. Selectors are **canonical Ethereum Keccak-256** (`modifyLiquidity=0x5a6bcfda`, `swap=0x1998bab9`, `donate=0x234266d7`, `IHooks.beforeSwap=0x3fd9994c`, `StateView.getSlot0=0xc815641c`, etc.). Resolver computes the canonical `PoolId` via `keccak256(abi.encode(PoolKey))[:32]` (matches `PoolIdLibrary.toId`), then calls `StateView.getSlot0(PoolId)` against the deployed `0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227` using only `urllib` from stdlib (no web3.py). Default contract anchor: canonical Ethereum PoolManager `0x000000000004444c5dc75cB358380D2e3dE08A90` (Etherscan Verified, ~48KB bytecode on mainnet).
- Added `tests/test_native_uniswap_v4.py` (13 tests) and `tests/test_crypto_keccak.py` (6 tests) — all passing with no synthetic test doubles.
- Added `foundry/test/UniswapV4PoolManagerHarness.t.sol` — pure-import stub that hard-codes the canonical selectors for parity with the Python harness and runs a live Ethereum fork probe (`vm.createSelectFork(ETH_RPC_URL)`) confirming `PoolManager.code.length > 1000` (`~48KB`) and `StateView.code.length > 100` on Ethereum mainnet at "latest". Compiles under `forge build --force` (no v4-core remappings needed). `forge test -vv` with `ETH_RPC_URL` set → 2 passed, 0 failed.
- `native mark --slug uniswap_v4 --status harness_built --contract-address 0x000000000004444c5dc75cB358380D2e3dE08A90 --source-commit 46c6834698c48bc4a463a86d8420f4eb1d7f3b75`. `ready_count=0` (correct — `ready` waits for C2: a measured delta on a live fork).
- Tests: **463 passed, 5 skipped** (was 444 → +19 net new).
- No new packages installed; `pyproject.toml` untouched.

## [4.2.0] — 2026-06-17

### AuditVault Advisory Corpus + Agent Proposal Lane + Lockdown
- Added `src/night_shift_security/platform/auditvault.py` with deterministic CLI subcommands `platform auditvault-sync`, `platform auditvault-patterns`, `platform auditvault-summary`. Offline clone lives under the gitignored `sources/auditvault/repo/`.
- Synced corpus totals: 2383 findings, 826 protocol slug×id pairs across 533 protocols. Axis distribution: staking 141, oracle 115, bridge 72, amm 64, governance 57, lending 42, mev 28, perpetuals 9, messaging 5. Stored under `data/security_results/platform/auditvault_findings.json`, `data/security_results/knowledge/auditvault_patterns.jsonl`, `data/security_results/knowledge/auditvault_ids.jsonl`.
- Added repo-managed Hermes `auditvault-research` skill (corpus research only — never executes the chain). Locked the `nightsoul` profile to **20 skill symlinks** (19 canonical NSS + `auditvault-research`); unrelated skills were removed and the lockdown is now guarded by a unit test that asserts the canonical skill set.
- Added an optional authenticated agent proposal lane (xAI-OAuth `hermes chat`, `grok-4.3`, max-turns 25) bound to the `nightsoul` profile. Lane writes untrusted `data/security_results/hermes_proposals/auditvault-*.json` proposals with `metadata.trusted=false`, `severity_score=0.0`, `force_target=true`, and `auditvault_ref_unique_pattern_id` lineage stamp. Sample audit vault agent proposal (target=wormhole, lineage `f60cd87d0758`+`3365e69dc864`, vector `token_account_dos`) recorded for 2026-06-17.
- Added lab notebook entries: `2026-06-17-auditvault-ingest.md`, `2026-06-17-auditvault-agent-proposals.md`, `2026-06-17-hipif-bounty-depth-run.md`, `2026-06-17-full-auditvault-oauth-run.md`.
- Verified a full no-agent HIPIF bounty-depth run to `chain_status=complete` (13 folds, gate_ok=true, submit_ready=false, elapsed 3564s). Fold summary: scan_all, depth_wormhole (13 findings / 2 fork_repro), kamino_preflight, depth_kamino (39 findings / 108 solana_repro), cantina_slates (9 programs × 3 trials), hunt_rotation, rsi_fold, depth_wormhole_bridge (13 findings / 10 fork_repro), refine_conditional, coordinator_conditional, journal_fold, gate.
- Verified trust-boundary integrity: `rg 'auditvault|audit_corpus' src/night_shift_security/validation/` returns no matches; AuditVault never alters `submission_gates`, `evidence_grading`, `novel_gate`, `nss-hipif-chain-run.py`, `klend`, or `wormhole_economic`. AuditVault data joins the same authoritative Python gates as every other corpus.
- SPEC.md added §6.7 (AuditVault advisory corpus ingestion), §6.8 (agent proposal lane), §6.9 (Hermes lockdown), and §31 (implementation status). AUDIT.md and AGENTS.md baseline tables updated.
- Tests: 438 passed, 5 skipped in full local run; focused AuditVault suite passed (sync, patterns, summary, no-key skip, gitignore, enrichment, lineage); focused Solodit/self-interrogation/pipeline suite 66 passed; focused Wormhole RSI/economic suite 42 passed; live Wormhole Foundry value probe 2 passed, 3 optional route replays skipped by default.

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
- Added Wormholescan signed-VAA fetch/decode helpers and an optional real signed VAA replay lane. The latest Ethereum-native release VAA verifies through live core and is already completed, producing zero delta; `AUTHORIZED_REPLAY=1` is non-submittable unless a bridge accounting violation is proven.
- Added Wormholescan real VAA corpus classification and runtime report generation. Latest live scan decoded 12 token-bridge VAAs across recent operations: 11 foreign wrapped mints and 1 Ethereum-native lock-out; no Ethereum-native release candidate was present in the latest 100 operations.
- Added optional Foundry replay lanes for Ethereum wrapped-mint `completeTransfer` and asset-meta `createWrapped` VAAs, plus Wormholescan selectors for those routes.
- Added documented Wormholescan `page`/`pageSize` pagination, route fixture writers, and a 40-page corpus lane. The current deep scan found real native-release and wrapped-mint VAAs that were already completed with zero delta, split payload-id 3 transfer-with-payload messages out of standard replay routes, and found same-chain Ethereum asset metadata that correctly skips `createWrapped`.
- Fixed the native-release replay normalization to use live token decimals. A pending plain payload-id 1 native-release VAA now completes on fork with matching bridge, recipient, and outstanding deltas; this confirms authorized replay only and remains non-submittable.
- Added a Wormholescan selector/writer for uncompleted plain payload-id 1 Ethereum-native release VAAs so pending replay fixtures are reproducible without ad hoc extraction snippets.
- Tests: 418 passed, 5 skipped in full local run; focused Solodit/self-interrogation/pipeline suite 66 passed; focused KLend probe suite 13 passed; focused Wormhole RSI/economic suite 42 passed; live Wormhole Foundry value probe 2 passed, 3 optional route replays skipped by default.

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
