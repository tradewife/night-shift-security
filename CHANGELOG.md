# Changelog

Release notes aligned with `SPEC.md` versions. Package version in `pyproject.toml` (`0.1.0`) is not tracked here.

## [Unreleased] — 2026-07-04

### v6.51 — Lombard cross-layer hard-first phase

- **Lombard cross-layer phase launched:** pivoted from v6.49 EVM GMP-core honest-zero to Solana `lombard_token_pool` + cross-layer EVM/Solana message and asset handling.
- **Code intelligence:** CodeGraph indexed 390 files / 3,999 nodes / 8,715 edges; Rust-aware call-path x-ray captured in `codegraph-x-ray-summary.md`.
- **Artifacts created:** `data/security_results/investigations/2026-07-03-lombard-cross-layer/{setup.md,property_fanin.md,property_candidates.md,invariants.md,summary.json,runs.jsonl}` plus 5 strategy files.
- **Solana build/IDL:** built and copied 11 primary SBF artifacts + 11 IDLs into `build_artifacts/`.
- **Native probes:** added `tests/test_native_lombard_cross_layer_v651.py`; focused Lombard native suite passes **19 passed, 1 skipped**.
- **EVM probes:** `PropEvmGmpCore` + `PropEvmDeepProbes` pass **16/16**; `HARDHAT_FORK=1 PropEvmForkAcl` passes **8/8**.
- **Token-pool Rust unit:** `cargo test --no-default-features --features localnet test_valid_signature` passes.
- **Cargo unit tests:** all-green for `lombard_token_pool`, `consortium`, `bridge`, `mailbox`, `bascule_gmp`, `asset_router`, `lbtc` (under `--no-default-features --features localnet`).
- **Anchor TS aggregate run:** 149 of 165 passing with 16 `before all` hook failures caused by validator shared-state cross-pollution (`12y3Uh6…`, `8SFqwq…`, `BqScmy…` PDAs).
- **Anchor TS per-file run:** `scripts/anchor-test-each.sh` with `ANCHOR_TEST_EACH_SLEEP_SECONDS=15`. **All 11 TS files green** — 310 tests passing total (asset_router 85, bascule.bankrun 12, bascule 1, bascule_gmp 21, bridge 71, ccip 7, consortium 17, consortium_utilities 23, mailbox 54, ratio_oracle 18, registry 1). Adjudicates the aggregate failures as test-infra cross-pollution, **not protocol bugs**. Results saved to `evidence/anchor-test-each/RESULTS.md`.
- **Crucible scaffold:** `InvalidAccountData` blocker resolved by copying mainnet-feature `lombard_token_pool.so` (686 KB) into the scaffold's `target/deploy/`. Dry-run log saved to `evidence/crucible-lombard-token-pool-dry-run.log`. Scaffold now reliably loads the program.
- **EVM cross-layer divergence probes:** new test suite `sources/lombard-finance/evm-smart-contracts/test/nss/PropEvmCrossLayerDivergence.ts` covers PROP-XR-EVM-006 (Mailbox handler-revert try/catch absorbed; MessageHandleError fires; subsequent retries re-run the handler) and PROP-XR-EVM-007 (AssetRouter.changeBascule(address(0)) under DEFAULT_ADMIN_ROLE disables Bascule.validateMint; non-admin is rejected). **5/5 passing.**
- **Solana CCIP v6.51 negative-path tests:** added N1/N2/N3 inside `tests/ccip.ts` "incoming CCIP bridge operation" describe. N1: wrong `destination_caller` (tokenPoolSignerPDA) stored verbatim by mailbox.deliver (no upstream gate); N2: re-init offramp at same nonce PDA reverts (ConstraintSeeds/init dedupe); N3: sourcePoolAddress without remoteChainConfig entry accepted by offramp.init but reverts on executeOfframp. **10/10 ccip.ts tests passing** (5 init + 1 happy + 3 v6.51 + 1 outgoing).
- **Crucible stateful harness on `lombard_token_pool`:** scaffold extended with three actions (`action_type_version`, `action_derive_accounts_release_or_mint`, `action_derive_accounts_lock_or_burn`) and a real invariant_test PDA-distinctness check. Dry-run PASS (1 program loaded, 2 tracked accounts, single iteration completed). 5-second stateful smoke executes 4 iterations / 0 crashes. Strategy `STRAT-S6-crucible-stateful-action-set.md` describes next-stage extension (load bridge/mailbox/consortium into the same context). Runs captured at `evidence/crucible-token-pool-dry-run-4.log` and `evidence/crucible-token-pool-stateful-run-5s.log`.
- **Consortium index-bounds DoS probe:** new pure-Rust unit-test module added at `sources/lombard-finance/repo/programs/consortium/src/utils/post_session_signatures_probe.rs`. Verifies through 3 tests that `post_session_signatures` indexes `current_validators/current_weights/session.signed` without bounds checking. Reachable impact is session DoS only — no fund-loss CPI proceeds before the panic. Fix recommendation: `require!(*index < current_validators.len() as u64, ConsortiumError::ValidatorIndexOutOfBounds)`. Adjudication: **honest-zero for fund-loss; informational DoS-only**. Logged as signal `SIG-CR-001-OOB-DOS`. Captured at `evidence/consortium-index-bounds-probe.log`.
- **Multi-program Crucible scaffold (R1 of carry-forward agenda):** eight programs (`lombard_token_pool` + `consortium` + `bridge` + `mailbox` + `bascule_gmp` + `bascule` + `mock_ccip_offramp` + `mailbox_receiver`) loaded into a single Crucible `TestContext` at canonical localnet IDs taken from each IDL `metadata.address`. Sister-IDL `declare_fuzz_program!` ctor collision fixed by reading IDs directly with `Pubkey::from_str`. Dry-run PASS: **2 tracked accounts, 8 programs loaded, harness validation passed**. 8-second stateful smoke: **21,076 iterations / 0 crashes / 5/5 actions discovered**. New actions: `action_type_version`, `action_derive_accounts_release_or_mint`, `action_derive_accounts_lock_or_burn`, `action_bootstrap_multi_program`, `action_config_pda_uniqueness_check`. Invariant_test asserts PDA distinctness (state vs pool_signer) plus pairwise distinctness of the 8 program IDs. Strategy file `STRAT-S6-multi-program-crucible-scaffold.md` records the bootstrap shape and the carry-forward plan to R2 (CPI integration of `release_or_mint` with bridge/mailbox instances). Logs captured at `evidence/crucible-token-pool-multi-program-dry-run-6.log` and `evidence/crucible-token-pool-stateful-multi-program-run-8s.log`.
- **Key refinement:** `release_or_mint_tokens` mailbox handler is token-pool `state` PDA, not `pool_signer`; remote `destination_caller` must match state PDA bytes while `pool_signer` is only bridge CPI signer.
- **Cross-layer divergence (round-2 insight):** EVM `Mailbox._deliverAndHandle` wraps `handlePayload` in try/catch + only sets `handledPayload[payloadHash]=true` on success (handler revert leaves message re-attemptable; the second `MessageHandled` re-runs the handler); Solana `mailbox.handle_message` writes `Handled` then `invoke_signed` (atomic rollback on recipient CPI revert). Both chains gate double-delivery via PDA `init` dedupe keyed on `[MESSAGE_SEED, payload_hash]`, so literal replays cannot pass init in either. Solana needs a brand-new tx after a failed `gmp_receive`; EVM lets the same `Delivered` payload be re-attempted in a new `deliverAndHandle` call.
- **No new submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

## [Unreleased] — 2026-07-03

### v6.49 — RedStone Cantina skill deep-dive completeness sweep

- **Mandatory skill deep-dive complete:** read `auditvault-research`, `onchain-forensic-tracing` (local `skill.md`), and `solodit-research`; `auditware-research` is not present locally, closest match is `auditvault-research`.
- **Completeness sweep complete:** enumerated and lightly reviewed all remaining `.agents/skills/`; no missed RedStone primary-subsystem angle beyond the signed Redstone envelope builder blocker.
- **New artifact:** `data/security_results/investigations/2026-07-03-redstone-cantina/skill-correlation-matrix.md`.
- **Properties extended:** `PROP-RS-015..018` added for reference-adapter fail-open, stale-reference deviation gate, clearing-adapter timestamp-view desync, and forensic storage trace equivalence.
- **Invariants extended:** `G-14..G-16` and `X-4` added.
- **Strategies updated:** signature/timestamp precision drift, ERC-7412 TTL early-return, and multi-feed reference griefing now include skill-derived evidence requirements.
- **Foundry probes extended:** added `RedstoneReferenceAdapterProbe.t.sol` (4 tests) and `RedstoneSinglePriceClearingProbe.t.sol` (2 tests). RedStone probe suite now passes **18/18** with 256 fuzz runs retained.
- **Foundry profile:** `[profile.redstone]` compiler bumped to solc `0.8.28` while keeping `evm_version = london`, needed for mixed RedStone `^0.8.17` and OZ `^0.8.20` pragmas.
- **Candidate status:** PROP-RS-007 advanced to executable fail-open/stale-reference behavior, but remains deployment-impact dependent. PROP-RS-001/002 strengthened, still blocked on signed payload assembly.
- **No new submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

### v6.48 — RedStone Oracles Cantina bounty scaffolding + first falsification pass

- **RedStone Oracle Infrastructure Bug Bounty (`36c588d4-0681-45a8-9694-13a871cc4ae6`, $250k critical).** Hard-first scaffolding on the EVM data package verification + aggregation + adapter write pipeline.
- **Repos cloned:** `sources/redstone/repo` (active monorepo, shallow `--depth 50`) and `sources/redstone/evm-connector` (mirror).
- **Code intelligence:** CodeGraph indexed 1,694 files / 16,789 nodes / 43,834 edges (10.3s). `.sol` not first-class; direct Grep + Read substitutes per past-session convention.
- **Primary subsystem mapped:** `CalldataExtractor.sol`, `RedstoneConsumerBase.sol`, `RedstoneConsumerNumericBase.sol`, `RedstoneConsumerBytesBase.sol`, `ProxyConnector.sol`, `libs/{SignatureLib,BitmapLib,NumericArrayLib}.sol`, `RedstoneAdapterBase.sol`, `MultiFeedAdapterWithoutRounds.sol`, `SinglePriceFeedAdapter{WithClearing}.sol`, `MultiFeedAdapterWithoutRoundsWithReference.sol`, `RedstonePrimaryProdWithoutRoundsERC7412.sol`.
- **Production signer set:** `MergedSinglePriceFeedAdapterWithoutRoundsPrimaryProd` hard-codes 5 signers (indices 0..4) and threshold 3. Reproduces in `PrimaryProdDataServiceConsumerBase`.
- **14 properties catalogued** (`PROP-RS-001..014`); 13 invariants categorized (G-1..G-13, X-1..X-3, E-1..E-3). 6 false candidates dropped with code evidence.
- **3 strategy files** in `data/security_results/investigations/2026-07-03-redstone-cantina/strategies/`: signature/timestamp precision drift, ERC-7412 TTL early-return race, multi-feed partial + reference-adapter griefing.
- **Foundry harness** — new `[profile.redstone]` block in `foundry/foundry.toml` (solc 0.8.17, `evm_version = london`, `allow_paths` for `../sources/redstone/repo`). Mocks: `RedstoneHarnessConsumer`, `RedstoneVerifierExposed`, `RedstoneMultiFeedAdapterMock`. Probe suites: `RedstoneInvariantProbe.t.sol` (8 witness tests) + `RedstoneMultiFeedAdapterProbe.t.sol` (4 tests, 256 fuzz runs).
- **PROP-RS-013 falsified honest-zero**: storage desync across `isValueBigger` flip holds across 256 fuzz runs; storage-packing round-trip correct at uint152 boundary.
- **Known open falsification candidates** (deferred to next session): PROP-RS-001 (ms→s truncation drift), PROP-RS-002 (ERC-7412 early-return TTL race), PROP-RS-007 (reference-adapter griefing).
- **Blockers:** RedstonePayload envelope assembly for full signed-payload harness; production signer ECDSA reproduction for Mainnet-fork pass; bounty scope pinning (researcher login required).
- **Artifacts (local-only per AGENTS.md):** `data/security_results/investigations/2026-07-03-redstone-cantina/` and `data/security_results/lab_notebook/2026-07-03-redstone-cantina-session-1.md`.
- **No submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

### v6.47 - Aztec Network Cantina nexus fresh-context pass

- **Aztec Network Cantina Bounty (`80e74370-10d8-4e52-8e4b-7294deb7c9ee`).** Fresh-context hard-first pass on the L1 Governance–Reward–Slashing–Inbox/Escape economic and trust nexus.
- **Scope:** `GSE.sol`, `Governance.sol`, `GovernanceProposer.sol`, `RewardLib.sol`, `EpochProofLib.sol`, `ProposeLib.sol`, `SlashingProposer.sol`, `Inbox.sol`, `EscapeHatch.sol`.
- **Codegraph/static:** Codegraph `explore`/`impact`/`query` artifacts captured. Slither ran via `uv tool run --from slither-analyzer slither`; 92 detector entries triaged, no confirmed submission-quality issue.
- **Fresh-context reviews:** 4 focused workers reviewed governance bonus voting, reward economics, inbox/escape temporal behavior, and slashing circular storage.
- **Interesting behaviors, not yet submission-ready:**
  - `GSE.voteWithBonus` uses the proposal `pendingThrough` timestamp for latest-rollup eligibility, not proposal creation time.
  - `EscapeHatch.validateProofSubmission` checks proven tip and archive match, not proof submitter identity.
- **Validation:** targeted Foundry passed `30/31` (1 skipped); full Aztec L1 Foundry passed `865/868` (3 skipped).
- **Artifacts:** `data/security_results/investigations/2026-07-03-aztec-cantina-nexus/` and lab notebook entry are local-only per AGENTS.md.
- **No submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

### v6.46 — Agglayer Cantina bounty deep-dive — honest-zero

- **Agglayer by Polygon Cantina Bounty (`3aaad22b-52ee-4bb2-bed2-4be53b0993cc`).** Hard-first cross-component analysis of pessimistic proof verification + AgglayerManager + AgglayerBridge + AgglayerGER + AgglayerGateway settlement/root invariants.
- **Repos:** `agglayer-contracts` (Solidity), `agglayer` (Rust SP1 prover), `lxly-bridge-and-call` (deprecated extension).
- **Codegraph + x-ray:** Investigation dir at `data/security_results/investigations/2026-07-03-agglayer-cantina/` with invariants.md, property_candidates.md, codegraph summaries, 4 strategy files.
- **19 executable attempts** across 5 rounds: 58+ Hardhat/Forge/Cargo tests. `runs.jsonl` entries 1–19.
- **9 invariant classes catalogued (PROP-AGG-001 through PROP-AGG-009).** All honest-zero.
  - PROP-AGG-001: encoding parity confirmed matching (Rust bincode vs Solidity `abi.encodePacked`)
  - PROP-AGG-002: nullifier replay prevented
  - PROP-AGG-003: balance overflow safe via U512 intermediates; `e2e_local_pp_overflow_attempt` passes
  - PROP-AGG-004: migration bootstrap consistent (empty state on both sides)
  - PROP-AGG-005: GER duplicate root deduplication confirmed
  - PROP-AGG-006: bridge reentrancy nullifier-first pattern holds
  - PROP-AGG-007: fee-on-transfer custody falsified (`BridgeV2FeeOnTransfer.test.ts`); origin path uses balance delta
  - PROP-AGG-008: gateway route selector is protocol-intended
  - PROP-AGG-009: stale L1 info root requires >4B GER updates (impractical)
- **H-FEE-001** closed (honest-zero). Origin ERC20 path uses received amount.
- **H-IDX** AgglayerGlobalIndexProbe 5/5 (512 fuzz iterations).
- **Remaining untested:** SP1 bootstrap proof for non-empty exit tree (requires SP1 prover toolchain).
- **`submit_ready` unchanged** at 1 (OnRe H1 v6.13).

## [Unreleased] — 2026-07-02

### v6.45 — OKX Labs DEX Solana Router Cantina bounty deep-dive — honest-zero

- **OKX Labs DEX Onchain Bug Bounty (`00992789-fcd1-4bda-862e-463b0c73faa9`).** Hard-first source-level deep-dive on the OKX DEX Router Solana program `6m2CDdhRgxpH4WjvdzxAYbGxwdGUz5MziiL5jek2kBma` (Anchor 0.31.1, 9 V3 handlers, 3 processors, 60+ DEX adapters, 130KB of Sanctum LST bridge integration).
- **Audit PDF re-read:** 13-page internal OKX Web3 Audit Team 2024-05-10. Base commit `229bc2b` (2024-02-07), final commit `a20505a`. 4 findings all Fixed: (3.1) Low — single-hop destination validation bypass (`if/else if` → separate `if` blocks); (3.2) Info — `with_capacity` underallocation in `spl_token_swap` args; (3.3) Info — misleading error message; (3.4) Info — `find_program_address` CU-heavy.
- **V3 surface un-audited:** No audit coverage for `swap_v3`, `swap_tob_v3`, `swap_tob_v3_with_receiver`, `swap_tob_v3_enhanced`, `swap_v3_with_cpi_event`, `wrap_unwrap_v3`, `wrap_unwrap_v3_with_receiver`, processor/* fee/trim logic, Sanctum router LST bridge, perpetuals adapter, or 50+ post-audit adapters.
- **48 invariants verified** (G-1..G-23 + I-1..I-8 + X-1..X-7 + E-1..E-7). Audit's specific bug class (single-hop `if/else if` boundary condition) was searched exhaustively in V3 paths — no analogues found; modern `common_swap.rs:601-604` uses two separate `if` blocks.
- **2 leads closed:** MOONIT-AUTH (false-positive, `invoke_signed(SA_AUTHORITY_SEED)` defense-in-depth); OKX-CORE-011 (Token-2022 fees `get_transfer_fee` and `harvest_withheld_tokens_to_mint` are dead code).
- **2 leads reclassified:** OKX-CORE-007/012 (`transfer_sol_with_rent_exemption` over-delivers, not under-delivers; user always gets ≥ requested amount).
- **7 leads open_informational:** ADAPTER-MINOUT-0 (per-DEX `min_amount_out=0/1`), OKX-CORE-013 (trim suffix parser panic on empty `remaining_accounts`, DoS only), OKX-CORE-017 (`transfer_sol_fee` rent top-up for non-SA authority, off-chain log under-reports), OKX-CORE-019 (Sanctum router `bridge_stake` PDA uniqueness delegated to Sanctum Router, cross-program trust assumption), AUDIT-GAP.
- **New invariants added (G-23):** Sanctum router bridge cross-program authority check at `adapters/sanctum_router.rs:1420-1424` (`require_keys_eq!` between `prefund_withdraw.swap_authority_pubkey` and `deposit_stake.swap_authority_pubkey`).
- **Structural observations (non-bugs):** Custom before_check G-7 omission in sugar_money/pumpfun/boopfun/boopfun2/moonit is double-layered defense via `invoke_signed(SA_AUTHORITY_SEED)` — not exploitable. SA-mediated Moonit sell `sync_wsol_account` would fail (wSOL account is user-owned, not SA-owned) — broken feature, not fund loss. Sugar Money / Pumpfun buy2/sell2 wsol vs token program layout mismatch — user-controlled layout, DoS only. `okx_bridge_program` constant (constants.rs:119-129) is dead code; trust model is solely `claim_authority` hard-coded pubkey.
- **Abort stubs catalogued:** 9 adapters (quantum, alphaq, taurusfi, goonfi, goonfi_v2, bisonfi, scorch, humidifi, humidifi_swap2) + 2 pumpfun variants — all `require!(true == false, ErrorCode::AdapterAbort)`.
- **Artifacts (local-only, gitignored per AGENTS.md):** `data/security_results/investigations/2026-07-02-okx-dex-solana-router/{invariants.md, property_candidates.md, property_fanin.md, runs.jsonl, summary.json, strategies/STRAT-OKX-CORE-017.md, strategies/STRAT-OKX-SANCTUM-ROUTER.md}` and `data/security_results/lab_notebook/2026-07-02-okx-dex-solana-router-session-{1,2,3,4}.md`.
- **No submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

### v6.44 — Perena Numeraire Cantina bounty deep-dive — honest-zero

- **Perena Numeraire Cantina Bounty.** Hard-first binary analysis of the 1.1MB eBPF program `NUMERUNsFCP3kuNmWZuXtm1AaQCPj9uw6Guv2Ekoi5P` + Anchor IDL decomposition (3375 lines) across all 23 instructions.
- **Verified gated (OnlyOwner — no bypass):** All 11 admin instructions (compound, skim, 9 setters) correctly reject non-owner. compound/skim gated at `skim.rs:65` and `skim.rs:18`. Instructions tested: set_status, set_inv_t_max, set_fee, set_owner, set_rate, set_numeraire_owner, set_numeraire_status, set_numeraire_whitelisted_pool_creator.
- **Binary/IDL reverse engineering:** Confirmed discriminator mappings for all instructions. Identified the `AddLiquidityData` C-struct with `take_swaps: u8`, `swap_paths: [u8; 10]`, `swap_amounts: [u64; 10]`. Reverse-engineered the 13-account pattern (7 fixed + 6 remaining with program-ID sentinel).
- **Historical on-chain analysis:** 326 add_liquidity + 174 remove_liquidity events mined from D99 pool across 51 unique users. MixerDepositScorer behavioral clustering: synchronous batch execution, single-pool only, balanced add/remove — no obfuscation signals.
- **Attack surfaces identified (not fully testable via mainnet sim):** add_liquidity take_swaps path manipulation, SwapExactOutHinted accuracy-hint manipulation, Token-2022 fee-on-transfer accounting mismatch, VirtualStablePair extreme parameter exploit.
- **programIdIndex bug fixed:** All prior miners used `ix.get('programId')` which doesn't exist in Solana RPC JSON; instructions use `programIdIndex`. Fixed by resolving `accts[ix.programIdIndex]`.
- **Artifacts:** `data/security_results/investigations/2026-07-01-v6-44-perena-cantina-deep-dive/` and `data/security_results/lab_notebook/2026-07-02-perena-numeraire-cantina-conclusion.md`.
- **No submission-ready finding.** `submit_ready` unchanged at 1 (OnRe H1 v6.13).

### v6.43 — Superform v2 Cantina bounty deep-dive — critical self-deposit exploit

- **Superform v2 Cantina Bounty (`02d2b20f-fe2e-4d8b-b9af-d38616e9836f`, 100k USDC + $UP max Critical).** Hard-first deep-dive on SuperVault allocation + hook execution + Merkle validation + PPS oracle subsystem. Repos cloned to `sources/superform/{core,periphery}` (`v2-core` @ `c73f452`, `v2-periphery` @ `4b004d1`).
- **Critical finding:** `SuperVaultStrategy._processSingleHookExecution` blocks hook calls to the SuperVaultAggregator but not calls to the SuperVault itself. A manager/session key can execute a registered, Merkle-valid hook that calls `vault.deposit()` from the strategy context.
- **Impact:** `SuperVault.deposit()` performs `safeTransferFrom(strategy, strategy, assets)`, a self-transfer no-op, then calls `handleOperations4626Deposit()` (no `nonReentrant`) and mints shares to an attacker without real assets entering. Shares dilute honest depositors and can be redeemed to drain vault TVL.
- **Upstream-integrated PoC passes:** `sources/superform/periphery/test/integration/SuperVault/SuperVaultSelfDepositHookPoC.t.sol`; uses real `SuperVault`, `SuperVaultStrategy`, `SuperVaultAggregator`, `SuperVaultEscrow`, registered-hook check, global Merkle root validation, and redeem path. Output: attacker receives `900e18` free shares with zero net deposit, then redeems `900e18` real assets from a `1000e18` honest deposit, leaving only `100e18` backing.
- **Artifacts:** `data/security_results/investigations/2026-07-01-v6-43-superform-v2-deep-dive/{setup.md,adjudication/submission_report.md}` and `data/security_results/lab_notebook/2026-07-01-v6-43-superform-v2-self-deposit-exploit.md`.
- **Submitted to Cantina on 2026-07-01.** `submit_ready` queue returned to 1 after Superform submission; remaining outstanding human-gated item is OnRe H1 v6.13. Superform is now awaiting Cantina triage.

## [Unreleased] — 2026-06-30

### v6.42 — Doppler Protocol Cantina bounty deep-dive — honest-zero

- **Doppler Protocol Cantina Bounty (`2c7af549-c36c-4432-bae6-3f4b1fa6b217`, $50k max Critical).** Exhaustive deep-dive on Doppler (1422 lines, 31 functions), Airlock, UniswapV4Initializer, DopplerHookInitializer, Multicurve, FeesManager, ProceedsSplitter. Repo: `github.com/whetstoneresearch/doppler` — cloned to `sources/doppler/repo`.
- **25 properties catalogued** in canonical property fan-in table. 27 invariants verified (4 dropped). 3 strategy files for highest-priority vectors (curve manipulation, early exit bypass, fee truncation).
- **9/9 Foundry probe tests pass** (`test/unit/DopplerDeepDive.t.sol` — P-01, P-06×3, P-07×2, P-11, P-13, P-19). All migration gates, epoch atomicity, totalTokensSold bound, beforeDonate revert, epoch skip catchup confirmed executable.
- **Infrastructure fix:** Resolved v4-core submodule issue (pinned commit unreachable) via deep-clone + symlink daisy-chain for nested deps (v4-periphery/lib/v4-core, universal-router/lib/v4-periphery, etc.).
- **P-17 external hook reentrancy:** Promising lead downgraded to Low/Informational after analysis. Two independent reentrancy locks (poolManager + solady `nonReentrant`) constrain impact to fee-collection timing only. Not submission-worthy.
- **Investigation artifacts:** `data/security_results/investigations/2026-06-30-v6-42-doppler-deep-dive/{setup.md,property_fanin.md,invariants.md,codegraph-x-ray-summary.md,adjudication.md,strategies/,harness_scaffold/}`.
- **Lab notebook:** `data/security_results/lab_notebook/2026-06-30-v6-42-doppler-deep-dive.md`.
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13).

### v6.41 — Liquity V2 Cantina bounty deep-dive — honest-zero

- **Liquity V2 Cantina Bounty (`7aa23a2b-7e8b-4b88-a9bb-713dc102a11a`, 125k BOLD max Critical).** Exhaustive deep-dive on CollateralRegistry, TroveManager, StabilityPool, BorrowerOperations, ActivePool, SortedTroves, PriceFeeds (5), DefaultPool, LiquityMath. Repo: `github.com/liquity/bold` @ latest main (v1.11.0).
- **20 properties catalogued** in canonical property fan-in table. 6 ranked attack vectors across 3 novelty tiers.
- **Key observations (not exploitable):**
  - wstETH oracle asymmetry: non-redemption price uses market only (no min with canonical), unlike rETH. Design difference due to oracle structure.
  - Batch shares ratio bypass: `_checkBatchSharesRatio=false` during redemptions. Redistribution can push ratio above MAX. Requires 217+ years of operation.
  - Accumulated rounding in batch trove debt: 3 separate integer divisions cause ≤6 wei loss per trove.
  - Urgent redemption dust: 8.82 BOLD per trove at $3000 ETH.
- **Reviewed:** Certora specs (sum_of_trove_debts, sameInterestRateForBatchTroves, collateral/debt adjust effects), existing test suite (500+ tests), git history.
- **11/11 Foundry probe tests pass.** `forge test --match-path test/liquity/*`.
- **No submission-ready finding.** Mature codebase with 700+ prior Cantina findings + 4 audit rounds (ChainSecurity, Coinspect, Dedaub, Recon).
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13).

### v6.40 — BitGo ETH Multisig v4 flushERC721Token ownerOf bug — submission-ready Medium

- **BitGo ETH Multisig v4 Cantina Bounty (`78a734d2-b460-4245-9c81-833487d6a339`, $75k max Critical).** Hard-first deep-dive on core multisig execution + ForwarderV4/Forwarder NFT flush mechanics. Repo: `github.com/BitGo/eth-multisig-v4` @ `8df06ad`.
- **`flushERC721Token` ownerOf bug confirmed:** `ForwarderV4.sol:265` and `Forwarder.sol:237` use `instance.ownerOf(tokenId)` as the `from` argument to `transferFrom` instead of `address(this)`. Transfers NFTs from whoever currently owns them — not just forwarder-owned NFTs. If any address has approved the forwarder via `setApprovalForAll`, the NFT is moved to `parentAddress` (the wallet).
- **Three attack vectors confirmed by passing PoC tests:**
  1. Rogue 1-of-3 signer via `WalletSimple.flushERC721ForwarderTokens` (`onlySigner`, not 2-of-3).
  2. Unauthenticated attacker via `RecoveryWalletSimple.flushERC721ForwarderTokens` (NO access control).
  3. `feeAddress` direct call via `ForwarderV4.flushERC721Token` (`onlyAllowedAddress`).
- **Inconsistency proof:** 7 of 8 NFT/token transfer functions in ForwarderV4 and Forwarder correctly use `address(this)`. Only `flushERC721Token` uses `ownerOf`. Auto-flush in `onERC721Received` uses `address(this)` — confirms manual flush is a bug.
- **Secondary finding (Low):** `init()` missing duplicate signer check. `[A,A,B]` → 2-of-2; `[A,A,A]` → permanent lockout.
- **Self-sanity check completed:** No duplicate (no GitHub advisories, no SECURITY.md, v2 has no NFT support — bug introduced in v4). Scope implicitly defined (no explicit file exclusion list). Severity downgraded from initial HIGH claim to Medium (configuration-dependent — requires victim `setApprovalForAll`; NFT goes to wallet not attacker).
- **21/21 Foundry tests pass** (6 PoC + 15 invariant). `FOUNDRY_PROFILE=bitgo forge test`.
- **Submission pack assembled:** Report + PoC gist + false-positive checks + validation summary + lab notebook + self-sanity check. Gist: https://gist.github.com/tradewife/3dfb2939a5e9c2e73633e3c5f2dc188e (secret).
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13).

## [Unreleased] — 2026-06-30

### v6.39 — Kiln OmniVault DELEGATECALL storage clobber — submission-ready Medium

- **Kiln OmniVault Cantina Bounty (`c9a4b51b-2e80-4713-a06f-13524c530fa6`, $500k–$1M max).** Deep-dive on Vault + ConnectorRegistry + dynamic connectors + FeeDispatcher + ExternalAccessControl intersection.
- **Unsafe DELEGATECALL confirmed:** `Vault._deposit()`/`_withdraw()` invoke connectors via `functionDelegateCall`, executing connector code in Vault proxy's storage context. Connector `assembly { sstore(slot, value) }` writes to arbitrary Vault storage slots.
- **Committed PoC:** `FeeOverrideConnector` overwrites `_depositFee` (ERC-7201 anchor+2) to 50% (50\*10^6), bypassing `_MAX_FEE` cap of 35%. Documented read-before-delegatecall timing analysis confirming why tx does not revert.
- **Raw SSTORE proof:** `KilnSStoreProbe` confirms `sstore(5, 0xC0FFEE)` lands in Vault proxy slot 5.
- **Storage influence map:** VaultStorage slots >1 (`_depositFee`, `_rewardFee`, `_lastTotalAssets`, `_collectableRewardFeesShares`, `_blockList`, `_depositPaused`) safely overwritable without tx revert. Slot 0 (`_connectorRegistry`) causes revert.
- **Severity:** Medium (impact=theft of fees/corruption of controls, likelihood=low per bounty matrix). Requires CONNECTOR_MANAGER_ROLE. Structural unsafety exists regardless.
- **Submission pack assembled:** Report + PoC gist + validation summary + false-positive controls + lab notebook. Gist: https://gist.github.com/tradewife/2018a5fe2a6d73273a053e9e189b815c (secret).
- **18/18 Kiln Foundry tests pass**.
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13).

## [Unreleased] — 2026-06-30

### v6.38 — Sablier Cantina corpus-exhaustive — AuditVault #42010 adjudicated

- **Sablier Cantina Bounty (`f9c0e285-1713-48f6-ac80-3271892c87f5`, Cantina, $100k max critical).** Corpus-exhaustive deep-dive across all 3 Sablier repos (Flow@e55caba, Lockup@baf9a9e, Airdrops@5b06824). AuditVault corpus mining (2384 patterns), found Sablier-specific #42010 overflow finding + 6 cross-protocol analogues.
- **AuditVault #42010 adjudication**: "sender-can-brick-stream-by-forcing-overflow-in-debt-calculat" — proven NOT exploitable on pinned commit. `UD21x18 = uint128` constraint makes `elapsedTime * ratePerSecond` overflow of `uint256` physically impossible (max product 3.7e50 << 1.15e77). Empirical proof via H-017 test.
- **4 new Death Probe tests** (H-017 through H-020): overflow proof, rate accumulation, edge deposit, fee dust boundary. All pass.
- **33/33 Flow tests pass** (17 existing + 16 custom probes), 289/290 total (1 fork test needs RPC).
- **Lockup/Airdrops CEI verification**: no reentrancy, no double-claim, clawback logic correct.
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). No submission-ready finding.
- **Artifacts:** `sources/sablier/flow/repo/tests/v6-37-SablierFlowDeathProbe.t.sol`, investigation workspace preserved.

## [Unreleased] — 2026-06-29

### v6.36 — Pendle Finance corpus x-ray (Cantina $2M) — honest-zero for current surface

- **Pendle Finance / Pendle Bounty (`fb1f1c54-0cb9-4201-8791-fb1e78e6e600`, Cantina, $2M, live since 2024-06).** Source cloned `pendle-finance/pendle-core-v2-public` to `sources/pendle/repo`. Hard-first on the most-convoluted subsystem intersection: PT/YT/SY/Market accounting + router callback composition (PendleYieldToken, InterestManagerYT, PendleMarketV7, MarketMathCore, ActionCallbackV3, ActionBase).
- **Corpus-driven entrypoint.** AuditVault/Solodit/refinement-hints signals pointed specifically at SY exchange-rate assumptions, batch/share accounting, rewards/interest share math, and oracle/TWAP manipulation. Active whitelisted market feed (77 markets above $100k TVL as of 2026-06-29) enumerated via `https://api-v2.pendle.finance/core/v2/markets/all`.
- **Property fan-in (7 corpus-correlated properties):** P1 `mintPY`/`redeemPY` SY conservation under monotone PY index (incl. multi variants); P2 YT interest invariance under transfers / partial claims / reward claims / same-block PY index caching; P3 post-expiry first-PY snapshot treasuries only post-expiry interest/rewards; P4 Market internal reserves cannot be desynced by direct transfers/callbacks/router self-composition; P5 public router callbacks cannot convert transient router balances into attacker-controlled PT/YT/SY; P6 `pendleSwap.swap` cannot allow arbitrary external routers to drain `pendleSwap` balances; P7 `pyYtLpOracle` TWAP cannot be made stale / manipulated for active integrations.
- **Concrete code signals (real behavior, not yet submittable):**
  - `ActionCallbackV3.swapCallback` and `ActionCallbackV3.limitRouterCallback` are publicly callable without caller validation (`msg.sender` market / limit-router check absent).
  - `PendleSwap.swap` is public and approves arbitrary `data.extRouter` for the full input token balance via `_safeApproveInfV2`.
  - Both require material residual/transient balances to cross the bounty threshold; without that proof they classify as low-impact residual-balance or user-error-adjacent. Active whitelisted markets have a heterogeneous SY surface (sUSDe / sUSDS tested via Sourcify + downloaded source for `PendleSUSDESY` and `PendleSUSDSSY`; USDat/USDai Sourcify entries are proxy metadata only and require resolving the implementation address); the hard remaining work is per-SY exchange-rate assays.
- **Toolchain check.** `corepack yarn install --immutable` + `corepack yarn compile` succeeded with warnings (code size, SPDX, peer deps). `codegraph init sources/pendle/repo` indexed only 4 non-Solidity files (same Solidity-blind engineering blocker seen in v6.28 LayerZero, v6.32 Coinbase); investigation used direct source review and grep.
- **Validators ran clean except pre-existing environment artifact.** `NSS_LOOP_DEPTH_SLUG=pendle hermes/scripts/nss-bounty-loop.sh --iterations 1` produced 37 findings / 0 live fork reproductions / 0 Immunefi packs (`hold`). `.venv/bin/python -m pytest -q` -> 1002 passed + 13 skipped + 1 pre-existing failure (`tests/test_native_kast.py::test_variant_builds_have_expected_matrix_and_files` missing `sources/kast/target/deploy/ext_swap.so`, unrelated to Pendle).
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). No new submittable candidate. Pendle hard-target work continues in subsequent sessions: mainnet-fork deployed-balance/materiality scan for router and `pendleSwap`, plus the top active SY sources for exchange-rate accounting fork assays.
- **No regressions.** 0 changes to `pyproject.toml` / Python pipeline / Hermes.
- **Artifacts (kept local per AGENTS.md):**
  - Investigation pack: `data/security_results/investigations/2026-06-29-v6-36-pendle-corpus-xray/` (setup.md, property_fanin.md, strategies/callback-and-residual-balance.md, evidence/{static-assay.log,bounty-loop.log,sy-source-probe.log}, evidence/sy_sources/{sUSDe-eth,sUSDS-eth,…}, runs.jsonl, summary.json)
  - Lab notebook: `data/security_results/lab_notebook/2026-06-29-v6-36-pendle-corpus-xray.md`

### v6.35 — Monad Foundation UI Bounty (Cantina) — 3 loops, 16 findings, 0 submission-ready

- **Monad Foundation / Monad.xyz UI Bounty (`a3806410-4f70-4023-8b29-103ddbd5b8a3`, Cantina, Critical $100k/High $30k).** Investigation of `claim.monad.xyz` — Monad airdrop claim portal with Privy authentication. Full surface inventory of 9 subdomains (claim.monad.xyz, app.monad.xyz, faucet.monad.xyz, developers.monad.xyz, etc.) including CSP audit across all.
- **Privy API surface mapping.** Recovered complete Privy app configuration via public API. Discovered reflective CORS with credentials on ALL `auth.privy.io` endpoints (F-011, High) — any attacker origin is echoed in `Access-Control-Allow-Origin` with `Access-Control-Allow-Credentials: true`. The `GET /api/v1/apps/:id` endpoint returns full app config cross-origin.
- **Complete Privy REST API discovered.** ~80 endpoints mapped from Next.js build manifest + OpenAPI spec (publicly accessible without auth). Includes user search by email/wallet/social, wallet management/export/transfer/RPC, key quorums, policies.
- **Two ECDSA P-256 verification keys recovered.** Second key from embedded wallets SSR page. JWKS endpoint publicly accessible.
- **Abuse chain analysis.** 4 chains documented: CSP+CORS+Config phishing chain, stale domain subdomain takeover, email enumeration, API surface recon. None submission-ready without an authenticated session or live XSS vector.
- **Analysis of 76K-address public claimer CSV.** 3.33B MON claimed, top allocation 12.2M MON ($244K), 73 genesis wallets, zero sybil clusters, zero sequential address groups.
- **16 findings total:** 1 High (reflective CORS), 7 Medium (CSP weakness, Privy config leak, stale allowed domain, email auth no captcha, cross-origin CORS, API surface exposure, key exposure, missing CSP), 3 Low (cookie security, CORS credentials, email plus-addressing), 2 Info (public CSV, claimer analysis).
- **87 canonical properties** across 11 categories (A–K) in property_fanin.md.
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). Surface exhausted without authenticated session. Investigation closed.
- **Artifacts (kept local per AGENTS.md):**
  - Investigation pack: `data/security_results/investigations/2026-06-29-v6-35-monad-ui-bounty/` (setup.md, property_fanin.md, 6 strategy files, summary.json, evidence/, harness/)
  - Lab notebooks: `data/security_results/lab_notebook/2026-06-29-v6-35-monad-ui-bounty-recon.md`, `...-loops.md`, `...-loop3.md`

### v6.35 — Alchemy Modular Account V2 (Cantina) — parked as underspecified-documentation-gap (ALC-23 overlap)

- **Alchemy Modular Account V2 (Cantina `246de4d3-e138-4340-bdfc-fc4c95951491`, $400k critical).** Pinned source at `c9e7683f9093448a033d4f3a85bf1f07ca8480b1` from `alchemyplatform/modular-account` v2.0.x. Hard-first on permission + validation module composition (`AllowlistModule` + signer validation modules + `ModularAccountBase` + `ModuleManagerInternals._installValidation`). Scope confirmed from Cantina: `ModularAccount`, `SemiModularAccount*`, `AccountFactory`, signer validation modules, `AllowlistModule`, `NativeTokenLimitModule`, `PaymasterGuardModule`, `TimeRangeModule`, `ExecutionInstallDelegate`.
- **Property fan-in (4 properties):** PROP-ALCH-001/002/003/004 covering allowlist-bypass paths, runtime/UserOp path consistency, reinstall hook lifecycle, and global-validation + native-management privileges.
- **Candidate finding (PROP-ALCH-001) reproducible:** A limited global `SingleSignerValidationModule` entity protected by `AllowlistModule` cannot directly transfer ETH via `execute`, but can call native `installValidation` through `executeWithRuntimeValidation`. `AllowlistModule.checkAllowlistCalldata` silently no-ops for non-`execute`/`executeBatch` selectors, so the limited session key installs an attacker-controlled global validation, which then drains 1 ETH.
- **UserOp reproduction:** `test_userOpLimitedGlobalAllowlistCanInstallArbitraryValidation` passes through the canonical EntryPoint flow, confirming the issue is reachable from real UserOp submissions, not only from `executeWithRuntimeValidation` direct calls.
- **Negative control:** `test_userOpSelectorScopedAllowlistCannotInstallValidation` passes — selector-scoped limited validations (the default aa-sdk `PermissionBuilder` limited-permission shape) cannot reach `installValidation`. The bypass requires a limited validation configured as `isGlobal=true`, similar to the `root` level format.
- **Known-issue overlap (classifies the finding as `underspecified_issue_with_executable_impact`, not a clean production defect):** `AllowlistModule.checkAllowlistCalldata` is precisely the design Alchemy/Quantstamp flagged as **ALC-23 — Allowlist: native-function risk on global validation entities**. ALC-23 acknowledges that custom global validation configurations can route around `AllowlistModule`'s selector scope and recommends documented UX expectations rather than code-level enforcement. The runtime and UserOp PoCs are reproducible evidence of the documented behavior on a configuration that is not the aa-sdk default.
- **Audit overlap (full).** Quantstamp ALC-23 (native-function risk on global validation), ALC-16 (executeBatch self-call hook bypass), ALC-15 (stale module cleanup), ChainLight ALCHEMY-001 (deferred-action native access). All are consistently flagged as **previously known**, which the bounty scope treats as out-of-scope for reward but in-scope for goodwill.
- **Validators ran clean:** Foundry PoCs passed; full `AllowlistModule` test suite (12 tests) passed; `.venv/bin/python -m pytest -q` -> 1002 passed + 13 skipped + 1 pre-existing KAST `ext_swap.so` artifact failure (unrelated).
- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). Pending human gate: park as ALC-23-overlapped documentation gap, or submit with explicit overlap caveat. Default posture is **parked**.
- **No regressions.** 0 changes to `pyproject.toml` / Python pipeline / Hermes.
- **Artifacts (kept local per AGENTS.md):**
  - Investigation pack: `data/security_results/investigations/2026-06-29-v6-35-alchemy-modular-account/` (setup.md, property_fanin.md, codegraph-x-ray-summary.md, known_issue_overlap.md, alc23_analysis.md, adjudication_inputs.md, strategies/, evidence/{poc.diff,poc-test.log,userop-poc-test.log,state-deltas.md}, adjudication/native-selector-bypass.json, runs.jsonl, summary.json)
  - Lab notebook: `data/security_results/lab_notebook/2026-06-29-v6-35-alchemy-modular-account.md`

### v6.34 — Coinbase Onchain Bug Bounty (Cantina $5M Tier 0) deep-dive sidecar — honest-zero (session-39 + session-40)

- **Coinbase Onchain Bug Bounty (program `55316f42-3c5e-4746-9bd0-0f18dcbc344b`, $5M Tier 0, broad scope: every mainnet Coinbase contract + every Base production contract).** Hard-first on most-convoluted subsystem intersection: Smart Wallet (MultiOwnable / ERC1271 / executeWithoutChainIdValidation / WebAuthn passkey) + Spend Permission Manager + SpendRouter + PublicERC6492Validator + MagicSpend.

- **Pinned source at 4 commits:**
  - `smart-wallet` → `e7fde11a50faa2fcff6f02210fe6571e21d906c8`
  - `spend-permissions` → `e0004e63edc4e17de7aa978293800ac7a16892e5`
  - `webauthn-sol` → `619f20ab0f074fef41066ee4ab24849a913263b2` (v1.0.0)
  - `magicspend` → `988d48c4d61eefa10e44b873380d6587dff1884e`

- **Property fan-in: 69 properties across 8 categories** (A Owner consistency, B Signature validation, C Cross-chain replay/nonce-key, D Spend permission lifecycle, E Router composition, F ERC-6492 wrapper, G MagicSpend, H Multi-component cross-cutting).

- **5 strategy files (STRAT-001..005) targeting 6 hypotheses:**
  - H1 — Signature/owner validation bypass
  - H2 — Cross-chain replay via 8453 nonce key + 5-selector whitelist
  - H3 — Spend permission lifecycle / allowance / revocation accounting
  - H4 — Integration / composability at trust boundaries
  - H5 — Edge deployment / new chain vectors
  - H6 — Broader economic / oracle / composability

- **NativeHarness `src/night_shift_security/native/coinbase_smart_wallet.py`** — replay-safe hash, cross-chain replayable nonce key 8453, canSkipChainId whitelist, RIP-7212 precompile address, 64 canonical properties, bounty metadata. 19/19 native pytests passing.

- **Cantina target config** `src/night_shift_security/config/targets/coinbase-cantina.json` (catalog_analogue=false, 6 templates, 4 pinned commits, metadata for Cantina program).

- **Foundry harness `sources/spend-permissions/repo/test/coinbase_propfuzz/` — 8 suites, 40 tests, 0 failures:**

  | Suite | Tests |
  |---|---|
  | MultiOwnableTest | 9 |
  | SpendPermLifecycleTest | 8 |
  | SpendRouterDecodeTest | 4 |
  | WebAuthnTest | 4 |
  | CrossChainReplayTest | 5 |
  | SpendTransientRaceTest | 2 |
  | Rip7212MockTest | 3 |
  | Router7702Test | 5 |

  Compile: `forge build` (119 files, success with warnings). Test runtime ~10ms full harness. Upstream regression: 201/201 clean. NSS full suite: 1002 passed + 13 skipped; 1 pre-existing KAST failure (unrelated).

- **4 carry-forward hypotheses adjudicated — none reached submission grade:**

  | ID | Adjudication | Result |
  |---|---|---|
  | PROP-CCH-006 | `engine_level_honest_zero_with_documented_intent` | `getUserOpHashWithoutChainId` is structurally identical across chainIds (chainA→99, chainA→8453); `upgradeToAndCall` ∈ 5-selector whitelist. Cross-chain replay is **documented Coinbase design** well-audited by OpenZeppelin, Certora, Cantina, Code4rena. UX hazard, not protocol defect. Submission-blocked. |
  | PROP-SPM-013 | `underspecified_partial_evidence_safe` | `receive()` correctly reverts when `value != _expectedReceiveAmount`. Transient slot gate works at surface. Full reentrancy fixture deferred to Phase 4 — transient storage is canonical defense. |
  | PROP-SIG-005 | `engine_level_honest_zero_with_environmental_observable` | Foundry env: `address(0x100)` staticcall → ok=true, ret.length=0; library's `abi.decode(ret, (uint256)) == 1` falls through to FCL. Same behavior on chains-without-RIP-7212. No divergence. |
  | PROP-RT-007 | `underspecified_low_severity` | SpendRouter constructor rejects 0xef0100-only exact match; non-7702 23-byte contracts accepted (deploy-time check, no real impact). |

- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). Coinbase deep-dive documents the cross-chain replay primitive in clean code; no protocol defect, no measured-impact blast.

- **Codegraph Solidity-blind** (same as v6.28 LayerZero): only 2 yaml files indexed, 0 Solidity nodes. Resolved by manual structural mapping of all 5+ core contracts. Engineering blocker recorded.

- **Pre-MPF covered from session-38 sweep**: MultiOwnable byte-length validation, SpendPermissionManager receive() boundary, SpendRouter EIP-7702 indicator rejection, WebAuthn replay-safe hash chainId+address binding, RIP-7212 precompile probe.

- **Phase-3 deepen session (session-40):**
  - Cross-chain replay structurally proven via Foundry (3 chainIds: harness default, 99, 8453)
  - Transient race receive() boundary empirically tested
  - RIP-7212 precompile behavior captured
  - EIP-7702 23-byte persistence check inverted-matrix tested

- **No regressions** in core pipeline. 0 changes to `pyproject.toml`/Python pipeline/Hermes.

- **Artifacts:**
  - Investigation pack: `data/security_results/investigations/2026-06-29-v6-34-coinbase-cantina/` (setup.md, property_fanin.md, 5 strategy files, 4 adjudication JSONs, summary.json)
  - Lab notebooks: `data/security_results/lab_notebook/2026-06-29-v6-34-coinbase-cantina.md` (Phase 1/2), `...-phase3.md` (Phase 3)
  - NativeHarness: `src/night_shift_security/native/coinbase_smart_wallet.py` + `tests/test_native_coinbase_smart_wallet.py` (19 tests)
  - Target config: `src/night_shift_security/config/targets/coinbase-cantina.json`
  - Source manifest: `sources/coinbase/source_manifest.json`
  - Foundry tests: 8 files in `sources/spend-permissions/repo/test/coinbase_propfuzz/`

### v6.33 — Veda boring-vault deep-dive: Token-2022 deposit fee honest-zero (session-38)

- **Veda (Immunefi $1M Critical) deep-dive closed as sustained honest-zero for current in-scope surface.** Hard-first on the most-convoluted subsystem: core BoringVault + yield streaming + cross EVM-SVM. Coverage:
  - `Veda-Labs/boring-vault` (EVM) + `Veda-Labs/boring-vault-svm` (Solana) + LayerZero share mover.
  - All `Mainnet/` configurations audited: HyperBTC, Scroll LiquidBTC/ETH/USD, Sepolia, Base, Arbitrum, Linea, Sonic, Swell, HyperEVM, TAC, Zircuit, Corn, Bera, Ink, Bob, Plasma, Katana, Plume, Fraxtal, Mantle, Monad, Optimism, XLayer.

- **STRAT-01 (Token-2022 deposit fee) — EXECUTABLE / PRODUCTION ZERO.** `test/VedaTokenFeeTest.t.sol` at `sources/veda/repo` — 4/4 tests passing:
  - `test_tokenFeeVaultUndercollateralized`: 1000 sent → vault receives 990 → 1000 shares minted
  - `test_tokenFeeRedemptionReverts`: full-share redemption reverts at `safeTransfer`
  - `test_tokenFeeMultiUserLatentInsolvency`: late depositor SqueezedOut; first movers drain vault with withdrawal-fee erosion
  - `test_controlNoFeeNoBug`: standard ERC20 — clean accounting, no insolvency
  - Production blast currently zero on EVM (canonical WBTC-family ERC20s only). Bug class becomes live the moment Veda adds a Token-2022 deposit mint to any in-scope vault.

- **STRAT-01 SVM Mirror — STATICALLY CONFIRMED.** `programs/boring-vault-svm/src/utils/teller.rs` lacks `validate_mint_fee`, MINT_WHITELIST, `is_supported_mint`, and pre-fee measurement. Identical gross-accounting bug applies if any SVM-side vault adds a Token-2022 mint. Built `boring_vault_svm.so` successfully.

- **STRAT-02 FixedRate phantom fees — SCOPE CARVE-OUT.** "Performance Fee accounting model" explicitly OUT in Immunefi Veda Known Issues. Not pursued.

- **STRAT-03 YieldStreaming uint128 truncations — SUBSUMED + UNREACHABLE.** "Yield streaming entry/exit asymmetry" carve-out applies; mathematically bounded by `maxDeviationYield` (500 bps × realistic TVL ≪ type(uint128).max). Not pursued.

- **STRAT-04/05 SVM `manage` sub_account routing + `update_rate` pause bypass — PRIVILEGED-ACCESS bounded.** Require strategist role; out of "no privileged access" rule.

- **STRAT-06 DecodersAndSanitizers coverage — Audit gaps out of scope this round.** Requires exhaustive IX selector audit.

- **`submit_ready` unchanged** (still 1, OnRe H1 v6.13). No new submission drafted; honest-zero bound by full coverage proof.

- **Cross-target Token-2022 fee pattern now tracked across 4 targets:**
  - OnRe — submit-ready (v6.13)
  - Veda EVM — confirmed executable, production blast zero
  - Drift — gated by `validate_mint_fee` (v6.30.1)
  - Marginfi — pre-fee compensated (v6.29)

- **No regressions** in core pipeline. 0 changes to `pyproject.toml`/Python pipeline/Hermes.

- **Artifacts (kept local per AGENTS.md):**
  - Investigation pack: `data/security_results/investigations/2026-06-28-v6-30-veda-deep-dive/` (setup, property_fanin, STRAT-01..06 strategies)
  - Lab notebook: `data/security_results/lab_notebook/2026-06-28-v6-30-veda-deep-dive.md`
  - Foundry tests: `sources/veda/repo/test/VedaTokenFeeTest.t.sol`
  - SVM build: `sources/veda-svm/repo/programs/boring-vault-svm/target/deploy/boring_vault_svm.so`

### v6.32 — Silo Finance reentrancy in defaulting liquidation (session-37)

- **Silo Finance v2/v3 reentrancy finding validated and submission-packaged.** `Actions.repay()` lacks `turnOnReentrancyProtection()` before `beforeAction(REPAY)`, unlike `borrow()`/`withdraw()`. During `liquidationCallByDefaulting`, the guard is turned off before the repayment step, creating a window where a malicious hook can reenter `ISilo.repay()` and double-count debt reduction.
- **Measured deficit:** 50,000 tokens (50k hook, 350k position) — 1:1 ratio of hook repay to protocol deficit. Max observed: 116,645 tokens (33% of debt).
- **Fork validation confirmed.** Mainnet fork at block 22,800,000 reproduces the exploit with 50k deficit. `FALSE POSITIVE RULED OUT`.
- **Known-issue differentiation.** Audit I-10 (Description Final Report) identified the window but NOT the reentrancy exploit. Incorrectly assumed `nonReentrant` on `PartialLiquidationByDefaulting` prevented exploitation. `ISilo.repay()` on `Silo.sol` has no `nonReentrant`.
- **10 tests passing** (8 PoC + 2 fork).
- **Submission artifacts created:**
  - `data/security_results/investigations/2026-06-28-v6-29-silo-finance-dual-liq/submission_report.md`
  - Secret Gist: `https://gist.github.com/tradewife/e5ef5d5e36809b30ffa28e491107e8ae`
  - `false_positive_checks.json`, `validation_summary.json`
- **`submit_ready` unchanged** (still 1, OnRe H1 from v6.13). Human gate required for submission.
- **No regressions.** 0 pipeline changes.
- **Lab notebooks:** `data/security_results/lab_notebook/2026-06-28-silo-reentrancy-validation.md`

### v6.31 — Raydium CP-Swap + CLMM forensic depth (session-36)

- **Raydium CP-Swap + CLMM forensic analysis (additive depth, not new hunt).** No new `submit_ready` candidate. Re-audited the two Raydium programs that had been in the broader audit cycle (#397 baseline) for adversarial depth.
- **Scope:** ~215K chars of Rust source read in full — CP-Swap pool.rs/curve_calculator.rs/swap_base_input.rs/swap_base_output.rs/deposit.rs/withdraw.rs/collect_creator_fee.rs/collect_protocol_fee.rs/collect_fund_fee.rs/utils/token.rs (MINT_WHITELIST etc.) + CLMM swap.rs (6631 lines, full file)/swap_math.rs/pool.rs/pool_fee.rs/dynamic_fee_config.rs/limit_order.rs (2600 lines)/tick_array.rs (1656 lines)/open/settle/close/decrease limit order/collect_protocol_fee.rs/lib.rs.
- **What was checked (5 deep-dive lanes).** Each verified with a working simulation or a full code-trace:
  1. **CLMM limit order settlement fuzz** — `hermes/scripts/clmm_limit_order_fuzz.py`: 100,000 random iterations + 5 edge cases (settle_base=0, phase equality, unfilled_ratio near-one, unfilled_ratio=1, both swap directions). **Zero anomalies.** No over-payment, no vault drain, no dust compounding across increase/decrease/settle.
  2. **Token-2022 PermanentDelegate extension** — full trace of `is_supported_mint` (BOTH CP-Swap AND CLMM). **Verdict:** ATA bypass requires admin keys; regular users cannot create pools with dangerous mints. CLMM is missing `close_support_mint_associated` (no revocation path) → **design concern**, not an exploit.
  3. **Cross-program CPI between CP-Swap and CLMM** — **None.** Programs are isolated. Only standard-program CPIs (SPL Token, Token-2022, System, ATA, Metaplex NFT for positions).
  4. **CLMM reward distribution precision** — Q64.64 growth simulation across 7 liquidity regimes. Precision loss <0.03% at realistic L. Vault shortfall gracefully caps transfers. `claim + owed ≤ emitted` invariant holds with only expected rounding dust.
  5. **Observation oracle TWAP manipulation** — 25-minute window limit (100 obs × 15s min spacing). `tick_cumulative` overflow takes ~660k years. External-protocol trust risk only (same as Uniswap V3 oracles).
- **Verdict on Raydium submission gate.** `submit_ready` unchanged → still 1 (OnRe H1 from v6.13). No new finding survives `qualifies_for_submission()`. **No regression in any token-accounting path.**
- **No regressions.** 972 tests passed, 0 changes to NSS pipeline.
- **Lab notebook:** `data/security_results/lab_notebook/2026-06-28-raydium-phase2-complete.md` (final), `…-raydium-phase2-analysis.md` (interim), `…-raydium-forensic-analysis.md` (initial pass).
- **Fuzz artifact:** `hermes/scripts/clmm_limit_order_fuzz.py` — re-runnable for any future CLMM upgrade with Q64.64 math changes.

### v6.30.1 — Drift Token-2022 guard-bound honest-zero (session-35)

- **Drift Token-2022 honest-zero confirmed.** Codegraph-first structural analysis of Drift Protocol's Token-2022 transfer fee handling. `validate_mint_fee()` at `controller/token.rs:214-227` is a hard gate that rejects any Token-2022 mint with a non-zero `TransferFeeConfig` extension, returning `ErrorCode::NonZeroTransferFee`. Called in all 5 token movement functions: `send_from_program_vault_with_signature_seeds` (line 69), `receive` (line 120), `mint_tokens` (line 176), `burn_tokens` (line 201), `transfer_checked_with_transfer_hook` (line 241). No bypass paths — only `invoke_signed` for SPL transfers is in `controller/token.rs:274`. Liquidation is purely accounting-based. All 7 properties (P-TF-Drift-001 through P-TF-Drift-007) honest-zero by design.
- **Codegraph intelligence.** 15,908 nodes, 88,958 edges indexed across 556 Rust/TypeScript files. `validate_mint_fee` identified as single point of enforcement. Blast radius mapped: 5 callers, all in `controller/token.rs`.
- **Cross-protocol Token-2022 coverage updated.** OnRe: 1 confirmed defect (submit_ready). Drift: 1 guard-bound honest-zero (no action needed). Marginfi: 1 candidate (requires validator deployment). Corpus gap partially filled.
- **No regressions.** 972 tests passed, 3 skipped (1 pre-existing KAST failure unrelated).

### v6.30 — Token-2022 transfer fee invariant campaign (session-34)

- **Portable Crucible harness template built.** Reusable Token-2022 transfer fee invariant module with 7 canonical properties (P-TF-001 through P-TF-007) covering deposit, withdraw, liquidation, fee-on-fee, share math, CPI safety, and fee recipient handling. Configurable `TARGET_PROGRAM_ID` and `TARGET_SO_PATH` for any Solana program. Strategy files: `tf_deposit_fee_mismatch`, `tf_liquidation_fee_impact`, `tf_fee_on_fee_lending`.
- **OnRe H1 confirmed (submit_ready).** `create_redemption_request` records gross amount (100M) but vault receives net (95M after 5% Token-2022 transfer fee). Cancel/fulfill revert; boss top-up + cancel returns only 95M to user (second fee charge), creating 5M protocol treasury hole. PoC validated on mainnet binary dump (SHA256 `abcea77d935ca5eb...`). Already submit_ready from v6.13 investigation.
- **Marginfi honest-zero (deposit/withdraw).** Deep code review of `deposit.rs`, `withdraw.rs`, `repay.rs`, `liquidate.rs`. Marginfi correctly handles Token-2022 fees via `calculate_pre_fee_spl_deposit_amount` — pre-compensates for fee before SPL transfer. Vault receives exactly gross amount after fee. No bug in deposit/withdraw path.
- **Drift Token-2022 honest-zero confirmed (v6.30.1).** Codegraph-first structural analysis: `validate_mint_fee()` at `controller/token.rs:214-227` rejects all Token-2022 mints with non-zero TransferFeeConfig via `ErrorCode::NonZeroTransferFee`. Called in all 5 token movement functions. No bypass paths. Liquidation is accounting-only. All 7 properties (P-TF-Drift-001..007) honest-zero by design.
- **Corpus gap partially filled.** Token-2022 transfer fee invariant (previously zero corpus entries) now has 1 confirmed + 1 honest zero + 1 pending.
- **`submit_ready=0` for new candidates.** OnRe H1 already submit_ready from v6.13. No new submittable candidate from this campaign.
- **No regressions.** 51 tests passed (Marginfi 26 + OnRe 11 + Drift 14), 1 skipped.

### v6.29 — Variational sidecar + corpus correlation + Marginfi Crucible (session-32/33)

- **Variational H1: batchDepositUSDCAtomic creator over-deposit — Bug confirmed (Medium).** Deployed settlement pool at `0x8db6c8b7...` (9107B runtime bytecode, verified identical to compiled source on fork) deposits `creatorPartyAmountRequested` N× for an N-item batch because batch loop never resets the variable. Human Gate falsified "permanent freeze" claim — provider-issued fresh withdrawal UUIDs always recover any stuck funds. Pool remains solvent. Severity downgraded Critical→Medium.
- **Fork verification completed.** 4/4 fork tests pass against live Arbitrum mainnet: bytecode length (9107B), selector presence (offset 87), proxy type (custom, not EIP-1967), admin topology (`0x8e4d1Ad...` = DEFAULT_ADMIN_ROLE).
- **Corpus correlation analysis (SPEC §9.2).** Deep-dived AuditVault (2383 findings, 826 protocols) + Solodit (159 findings) against 17-campaign surface. Built 10-class invariant bug taxonomy with per-class corpus density, discovery pathway efficacy table. Key finding: Token-2022 transfer fee accounting is ZERO corpus entries — critical blind spot.
- **Marginfi v2 Crucible harness built and fuzzed.** 8-action Crucible harness (deposit/withdraw/borrow/repay/liquidate/start-flashloan/end-flashloan/advance-slots) with conservation-of-value invariant. Stateful fuzz: 11.3M iterations across two runs, 0 crashes, 0 invariant violations, ~15.2% OK rate, 8/8 actions discovered. 6th empirical-FNR datum.
- **`submit_ready=0`** — Variational H1 downgraded to Medium. No submittable candidate.
- **No regressions.** Foundry: 76 passed, 0 failed, 13 skipped. Marginfi native: 26 passed, 1 skipped.

### v6.28 — LayerZero V2 Endpoint+ULN302 codegraph hardening (session-31)

- **New target: Enzyme Onyx (Immunefi, EVM, $200k critical max).** Modular tokenization protocol with Shares, ValuationHandler, FeeHandler, FeeTrackers, LinearCreditDebtTracker, AccountERC20Tracker, ERC7540-like queues, forwarders, CCIP wallets, beacon factories. Repo cloned to `sources/onyx/repo`, build verified (192 artifacts), full protocol test suite passing.
- **Deep code intelligence.** Read and analyzed all 44 Solidity source files across 7 subsystem layers: Shares, Valuation, Fees (2 trackers), Position Trackers (AccountERC20, LinearCreditDebt), Issuance Queues (Deposit+Redeem), Forwarders (Limited/OpenAccess), CCIP (WalletsManager+DepositorWallet), Factories (Beacon/Deterministic), Address Lists, Chainlink CRE, deployment infrastructure.
- **Integration test suite shipped (7 tests).** Exercises fee cycles, queue execution, perf fee HWM reset on zero supply, phantom fee with LinearCreditDebtTracker, entrance fee rounding bypass, management fee retroactive rate change, fee claim solvency. All pass.
- **Fuzz invariant tests shipped (2 tests, 512 runs).** `test_fuzz_depositUpdateRedeem_consistency` (256 runs): no solvency violation under random deposit/fee/time parameters. `test_fuzz_multiCycleAccounting` (256 runs): no accounting inconsistency in multi-user cycles. All pass.
- **Deep adversarial probes shipped (6 tests).** Phantom LCDT extraction confirmed (fund trapping with 25k phantom value, 17.5k shortfall — admin-gated). Retroactive mgmt fee (0%→50% after 330 days extracts 45% of fund — documented). Multi-layer fee compounding (4 fee layers, no insolvency). Tiny-supply inflation (1e36 share price — documented risk). Fee claim overflow (correct revert). LCDT boundary transitions (correct per spec). All pass.
- **Solodit/AuditVault correlation.** Cross-referenced Onyx surface against 7 NSS pipeline templates (`access_control_escalation`, `treasury_drain`, `flash_loan_oracle`, `reentrancy`, `composability_risk`, `upgradeability_risk`, `governance_capture`). All control flow, access control, upgradeability, and composability edges safe by design or properly gated.
- **Ultrafuzz-discovery conformance.** Property fan-in (15+ canonical properties), strategy fan-out (6 strategy files), fresh-context repetition (512 fuzz runs), failure preservation, adjudication classification, honest-zero basis.
- **Full protocol suite clean.** 380/381 tests pass (1 infra failure: CreWorkflowConsumerTestEthereum needs Mainnet fork URL). 0 regressions.
- **Gate result:** `submit_ready=0`. No exploitable bug found. Close target.

### v6.28 — LayerZero V2 Endpoint+ULN302 codegraph hardening (session-31)

- **Mandatory codegraph-first pass completed, with an explicit Solidity blind-spot result.** Installed `@colbymchenry/codegraph`, ran `codegraph init` against `sources/layerzero/repo`, and recorded that the current build indexed only 5 non-Solidity files in this workspace. Session carried that negative signal into the investigation pack rather than silently skipping the requirement.
- **New hardening investigation pack** at `data/security_results/investigations/2026-06-27-v6-28-layerzero-codegraph-hardening/`: updated property table `PROP-PKT-001..010`, 3 refined strategy files, setup note, and summary JSON.
- **Python sidecar refreshed** to `v6.28.0-layerzero-endpoint-uln302-codegraph-hardening-session31`; discriminator set expanded from `PROP-PKT-001..007` to `PROP-PKT-001..010`. Root pytest suite remains **17 passed**.
- **New EndpointV2 migration-boundary sequences (local-only in pinned source clone).** `sources/layerzero/repo/protocol/test/EndpointV2CodegraphHardening.t.sol` adds 2 passing tests covering default receive-library grace expiry and custom receive-library timeout expiry at the exact boundary block.
- **New ReceiveUln302 quorum-hardening sequences (local-only in pinned source clone).** `sources/layerzero/repo/messagelib/test/ReceiveUln302CodegraphHardening.t.sol` adds 2 passing tests covering post-commit quorum-storage reclamation and header-scoped quorum isolation.
- **AuditVault + Solodit corpus deep-dive completed.** Mined 2383 AuditVault + 159 Solodit findings for LayerZero/messaging/bridge patterns; surfaced 12 direct LayerZero ecosystem matches and 569 high-value correlated findings across 247 protocols. 9 new attack hypotheses synthesized (Directions D-L: nonce replay via skip/nilify/burn, library upgrade grace race, composeMsg reentrancy, allowInitializePath first-nonce race, executor option decoding, DVN quorum sybil bypass, send-side fee flow, packet codec, address cast truncation). All 9 honest-zero with strong structural prevention.
- **Direction C live signals** (`foundry/test/LayerZeroEndpointIsSupportedEidAudit.t.sol`, local-only): on Ethereum mainnet fork via Alchemy, `isSupportedEid==true` + dead DVN `0x...dEaD` in default ULN config for EIDs 30155 (Tac) and 30301 (Read chan); quote path reverts for 4/5 probed EIDs. Default-config liveness/availability issue, not direct fund-theft.
- **Direction M CEI flag** (`foundry/test/OFTAdapterReentrancy.t.sol`, local-only): mirror harness demonstrates `OFTAdapter._credit` state-write-before-transfer pattern. Temporary `availableToSend` inflation confirmed during the callback window. Bounded exploitation requires non-standard (ERC777-like) underlying tokens; defensive-only flag.
- **Root sidecar validators remain green.** `forge build --root foundry` clean, `forge test --root foundry --match-path 'test/LayerZero*'` + OFTAdapterReentrancy -> **17 passed / 0 skipped** (was 10/3 before Directions C/D/M added). The 4 new upstream local-only sequence tests also pass.
- **Gate result unchanged:** `submit_ready=0`. No reproduction-tier funds-at-risk path survived the hardened packet lifecycle checks or any of the 9 new honest-zero directions.

### v6.27 — LayerZero V2 Endpoint+ULN302 hard-first sidecar (session-30)

- **New target lane: Immunefi LayerZero omnichain messaging bounty ($15M critical max, $2M V2 cap), sidecar-only.** Phase 1 hard-first scope: EndpointV2 + SendUln302 + ReceiveUln302 only; OFT / Solana / V1 / Aptos deferred to Phase 2A contingent on engine-level signals.
- **Source pinned** at `LayerZero-Labs/LayerZero-v2 @ audit` tag (`0990059e3ee61ea95f45011cf7284243531fb4c3`). Source-manifest `sources/layerzero/source_manifest.json` records per-contract sha256 (`EndpointV2.sol = 9702083e…`, `SendUln302.sol = bd198eb3…`, `ReceiveUln302.sol = 71f8b928…`). `bytecode_manifest.json` is populated with addresses but empty runtime sha256 fields (live RPC deferred — no `ETHEREUM_RPC_URL` in sandbox).
- **Python property-fan-in model** (`src/night_shift_security/native/layerzero.py` + `tests/test_native_layerzero.py`): **17 tests pass**. Direct select recomputation vs. `night_shift_security.crypto.keccak256` (a second independent ground-truth path), packet-codec invariants (81-byte header, version 1, nonce/sender/distinct collisions, deterministic encoding, payload-hash distinctness), nonce-bucket separation, harness-version sentinel.
- **Foundry harnesses (codec-only, no library install).** `foundry/test/LayerZeroEndpointHarness.t.sol` (5 tests: 2 selector-sanity PASS, 3 fork-mode SKIP without `ETHEREUM_RPC_URL`). `foundry/test/LayerZeroULN302LifecycleFalsifier.t.sol` (8 packet-codec falsifiers PASS).
- **Property-fan-in table** (`data/security_results/investigations/2026-06-27-v6-27-layerzero-sidecar/property_fanin.md`): PROP-PKT-001..007 mapped to source-pinned file paths; canonical sentinels are _assertAtLeastOneDVN, GUID.generate, keccak256(payload), _verifiable nonce check, lzClearPayload reentrancy guard.
- **Strategy fan-out (3 strategy files)**: `dvn-positive-negative.md`, `executor-privilege-escalation.md`, `message-lib-migration-edge.md`. Each strategy lists target properties, positive/negative controls, and the adversarial hunt to run.
- **Adjudication (3 per-discovery files)** classifying: H1 codec invariants = `engine_level_honest_zero`; H2 DVN-quorum resolution = `underspecified_when_owners_allowed`; H3 message-lib migration = `configuration_gated`.
- **Engine reachability at codec-only:** 8 codec falsifiers green + 17 python tests green + 2 selector tests green (Solidity inline keccak matches Python recompute) — `engine_level_honest_zero` for Phase-1 round 1.
- **Audit-saturation framing remains bounded (NOT asserted)** per SPEC §3.2. This is the 4th empirical-FNR datapoint after Ethena (v6.1) + Marginfi (v6.2) + Kamino (v6.3); all four are honest-zero. Saturation is bounded, not asserted.
- **Hard cutoffs honored**: `day_shift/{current,next}.md` NOT touched; sidecar status lives at `day_shift/layerzero_sidecar.md`. Investigation workspace + source clone are gitignored by default per AGENTS.md.
- **Promotion criteria for any submission candidate:** see `qualifies_for_submission()` in `src/night_shift_security/validation/submission_gates.py` (forge_reproduced tier + grade 4 + non-catalog-analogue + deployed-viable + balance-verified + human-gate). Phase-1 has none of these — `submit_ready=0`.

### v6.27 — KAST m_ext + ext_swap sidecar final: cross-instance swap, H5 retraction, honest-zero (session-28)

- **New target: KAST M0 Solana M Extensions (Immunefi), sidecar-final.** Source pinned at `c12a23acd8baeba92d4d9f64feb47837ddccca09` from `github.com/m0-foundation/solana-m-extensions`. 3 m_ext variants built (scaled-ui, crank, no-yield) + ext_swap CPI router.
- **Cross-instance swap integrated.** Added `ext_a` (no-yield variant at `3joDhmLtHLrSBGfeAe1xQiv3gjikes3x8S4N3o6Ld8zB`) as a second m_ext instance sharing the same M mint. Added `action_ext_swap_swap` for atomic EXT_A -> primary EXT swaps via ext_swap CPI passthrough. ext_swap `SwapGlobal` whitelists both extensions.
- **Crucible harness at 23 actions.** Actions added: `ext_swap_wrap`, `ext_swap_unwrap`, `ext_swap_swap`, `ext_swap_install`. Total actions: 23 covering all executable m_ext + ext_swap instructions across both instances.
- **Value conservation invariant.** Custom `after_action` check: `ext_supply * ext_index <= vault_raw * m_index`. 0 genuine violations found. Stale-index false positives (update_multiplier before sync) identified and ruled out.
- **H5 definitively retracted.** The claim_for collateral check (`ext_supply + rewards > vault_ui` at `claim_for.rs:138`) is mathematically correct for crank mode. Crank EXT tokens have no ScaledUiAmount multiplier; comparison units are consistent. Full algebraic proof in property_fanin.md.
- **Campaign results: scaled-ui 2629 execs/82% ok/0 crashes, crank 2308 execs/61% ok/0 crashes.** Cross-instance swap (ext_a -> primary) verified correct with M vault conservation.
- **Python state model.** `src/night_shift_security/native/kast_state_model.py` — systematic wrap/sync/claim/unwrap invariant tests across multiplier growth scenarios.
- **Investigation pack updated.** summary.json, property_fanin.md, runs.jsonl all reflect 23-action cross-instance state. Lab notebook entry created.
- **Verdict: honest-zero across full instruction surface.** ~40,000+ total fuzzing executions across 5+ campaign variants, 0 crashes, 0 confirmed defects. Harness exhaustively covers executable m_ext + ext_swap paths. No further ROI expected.


### v6.26 — Lombard Phase 4-5 corridor endgame: 9-program orchestrator + LBTC standalone harness (session-29)

- **Phase 4 corridor harness shipped.** `crucible/corridor/` loads all 9 Lombard Solana programs (consortium, mailbox, bridge, asset_router, bascule, bascule_gmp, ratio_oracle, registry, mailbox_receiver) in a single stateful Crucible harness. Dry-run validates 9 programs loaded, 9 tracked accounts.
- **Phase 4 stateful campaigns (corridor).** 2 runs: traced 60s (6,962 iters, 4/4 actions, 0.8% edge coverage) + no-trace 120s (21,428 iters, 4/4 actions). 0 crashes, 0 invariant violations.
- **Phase 5B: LBTC standalone Crucible harness shipped.** `crucible/lbtc/` implements the full lbtc lifecycle: secp256k1 key generation via `k256` crate, valset lifecycle (create_metadata → post_metadata → create_valset_payload → set_initial_valset), mint payload lifecycle (create_mint_payload → post_mint_signatures → mint_from_payload), redeem, pause/unpause, set_mint_fee, enable_bascule.
- **LBTC stateful campaign.** 18,660 iters, 0 crashes, 6/6 actions discovered, 5.1% edge coverage, 10.7% action success rate — healthiest campaign across all Lombard crucible lanes.
- **Phase 5A: Lombard Token Pool evaluated and skipped.** CCIP-based pool using `base_token_pool` external crate with highly parameterized types — poor Crucible IDL fuzzing fit.
- **Engineering blocker documented.** litesvm lacks `secp256k1_recover` syscall, preventing BasculeGMP `report_mint`/`validate_mint` CPI execution. AssetRouter configured with `bascule_gmp=None` as mitigation.
- **All 5 crucible harnesses compile.** consortium, mailbox, bridge, corridor, lbtc — all pass `cargo fmt --check` and `cargo check --features invariant_test`.
- **Total investigation coverage.** 10 attempts, 9 honest-zero runs, ~2.2M executed units, ~2.75M actions observed across 5 crucible lanes. All honest-zero.
- **Gate result:** `submit_ready=0` for Lombard Solana.

### v6.25 — Midas sidecar onboarding + Crucible pre-written-state harness (session-26)

- **New target lane: Midas bug bounty (Cantina + Sherlock, midas-vault main focus), sidecar-only.** Source cloned at `2932436b13c055cf51c74da07a12a580f64ad56e`; 4 mainnet BPFs dumped (`access_control.so`, `data_feed.so`, `token_authority.so`, `midas_vaults.so`); 4 modern IDLs copied (`access_control.json`, `data_feed.json`, `token_authority.json`, `midas_vaults.json`). `sources/midas/source_manifest.json` records commit + per-program BPF/IDL sha256 + Cantina/Sherlock bounty URLs.
- **Crucible harness rebuilt using Drift v6.12 pre-written-state pattern.** Pre-creates `vault_common`, `minter_vault`, `redeemer_vault`, `mint_vault_request@id=0`, `redeem_vault_request@id=0` with correct Anchor 8-byte discriminator + borsh layout. Access-control role PDAs pre-written owned by `AccessControl::id()`. Real Anchor `reject_mint_request` / `reject_redeem_request` instructions reach the dumped mainnet BPF dispatcher.
- **Python falsifier model** (`src/night_shift_security/native/midas.py` + `tests/test_native_midas.py`): 11 tests pass covering Token-2022 transfer-fee math, H2 reject stranding, H3 post-request approval, mainnet payment-mint KPI.
- **Investigation pack** at `data/security_results/investigations/2026-06-26-v6-23-midas-sidecar/`: setup, property fanin, 7 strategy files (vault issue/redeem round trip, CPI sequence, missing features, role lifecycle, oracle bypass, Token-2022 abuse, economic accounting), `runs.jsonl` (5 attempts), `summary.json`, six adjudication files (H1..H6).
- **Stage-3 stateful Crucible run (76s, single client):** 68,639 executions, 0 crashes, **ok = 42,598 / 405,650 (10.5%)**, `actions/exec=5.9`, `edges=526/15,686 (3.4%)`, `branches=500/7,843 (6.4%)`, `discovered_actions=5/5`. Sustained `[REJECT_MINT ok:0]` lamport-delta pattern `delta_user=3_000_000 mint_req_before=3_000_000 mint_req_after=0` over 10,710+ occurrences — Anchor `close = user_account` constraint verified to fire.
- **H2 status upgraded** from `engine_level_honest_zero` to `engine_partial_directional_H2` (recorded `adjudication/H6_reject_pda_lamport_close_empirical.json`). Payment-token-side leakage remains unexercised and requires Stream B (full vault fixture + `mint_request` → `reject` on `solana-test-validator`), queued as next-operator carry-forward.
- **Sidecar posture preserved:** no edits to `day_shift/{current,next}.md`, `SPEC.md`, or `CHANGELOG.md` until now (this commit is the durable record). `submit_ready=0`, `promoted_from_sidecar=0`.
- **Stream B evidence preserved:** source-anchored fingerprint of all four request handlers (`reject_mint_request.rs`, `reject_redeem_request.rs`, `mint_request.rs`, `redeem_request.rs`) at `evidence/validator/H2_request_rejection_custody.json`; both reject handlers contain `close = user_account` + emit event only, with zero `transfer_token` calls.
- **Full NSS suite clean:** 945 passed, 13 skipped — no regressions from Midas code additions.

### v6.24 — Lombard Solana bridge-stack onboarding + first Crucible executable campaign (session-27)

- **New target: Lombard Finance (Immunefi, Solana bridge stack, $250k critical max).** Onboarded following the 2026-06-25 Immunefi scope update adding Solana programs. 7 scoped programs: consortium, mailbox, bridge, asset_router, bascule, bascule_gmp, ratio_oracle.
- **NativeHarness shipped.** `src/night_shift_security/native/lombard.py` with canonical program IDs, instruction discriminators for 60+ instructions across all 7 programs, IDL loading from cloned Lombard repo, RPC resolution for live/validator checks.
- **Target config shipped.** `src/night_shift_security/config/targets/lombard-finance.json` — Solana target slice integrated into NSS pipeline.
- **Recon + semantic artifacts generated.** `sources/lombard-finance/recon.json` with 5 invariant families and threat model. Semantic map, triage files (79 files above min-score 4), and patch shapes under `data/security_results/semantic/` and `data/security_results/triage/`.
- **Ultrafuzz investigation pack.** 20 property IDs (PROP-CONS-001 through PROP-CROSS-002), 4 strategy files covering consortium session replay, mailbox message reuse, bridge route rate-limit, and asset_router mint/redeem conservation.
- **First Crucible executable campaign (consortium).** 2 fuzz runs: attempt 1 (364K exec, 60s, 4 cores, 0 crashes), attempt 2 (815K exec, 120s, 4 cores, 0 crashes). Total: 1.18M executions, 1.6M actions observed, engine-level honest-zero on consortium session creation surface.
- **Full NSS suite clean.** 945 passed, 13 skipped — no regressions.
- **Gate result:** `submit_ready=0` for Lombard Solana.

### v6.22 — Zest amplified multi-step falsifiers (session-25 continuation)

- **6 amplified falsifiers added** (`test_h7_1` through `test_h7_6`): multi-collateral liq boundary, DAO egroup LTV change mid-position, extreme 99.9% utilization, mixed oracle staleness fail-fast, asset disable + collateral-remove, multi-collateral extreme price divergence (+300%/-80%).
- **All 40 tests pass**, no regressions. Honest-zero on all submission-grade vectors. `submit_ready=0`.
- Key finding: the multi-collateral + other-debt-repayable path (H7.1) is unreachable in production because no egroup is configured for multi-collateral + single-debit masks — architectural gap rather than exploitable bug. DAO LTV update (H7.2) correctly enforced via capacity check.

### v6.21 — Zest Protocol V2 static-first falsifier (session-25)

- **New target: Zest Protocol V2 (Clarity/Stacks).** Cloned `zest-v2-contracts` to `sources/zest/repo` (e033a61). Built `source_manifest.json` with 12 in-scope contracts under deployer `SP1A27KFY4XERQCCRCARCYD1CC5N7M6688BSYADJ7`.
- **Python falsifier model shipped.** `src/night_shift_security/native/zest.py` with faithful Clarity math translation: mul-div-down/up, normalize, liquidation factor/penalty, vault share math, egroup resolution. All integer semantics match Clarity v4 uint (128-bit, no underflow).
- **34 property-based tests.** Covering egroup transitions (H1), liquidation math (H2), vault share accounting (H3), DEFAULT egroup observation (H4), market-vault consistency (H5), and audit reproduction gates (H6). All 34 pass.
- **Low-severity finding: liq-penalty-max mismatch.** `market.clar` `liquidate()` uses `liq-penalty-max` (1000bps) instead of actual graduated `liq-penalty` (500-1000bps) in two paths. Quantitative impact: 0-4.55% systematic under-counting of remaining debt. Limited to dust-level material impact. Not submission-grade.
- **All audit gates confirmed.** C-01 (zToken caching) fix present, M-05 (dust collateral) fix present, M-07 (vault div-by-zero) acknowledged.
- **Gate result:** `submit_ready=0` for Zest.

### v6.20 — 3F Grunt full-scope corpus-driven ultrafuzz (session-24)

- **Full-scope corpus map added.** Re-read repo-managed Hermes skills (`ultrafuzz-discovery`, `auditvault-research`, `solodit-research`, `operator-*`, `lab-notebook`) and built v6.20 artifacts under `data/security_results/investigations/2026-06-25-v6-20-3f-grunt-full-scope/`: `setup.md`, `property_fanin.md`, 4 strategy files, and `runs.jsonl`.
- **Cyfrin/Solodit + AuditVault correlations incorporated.** Solodit local API sync: 159 findings / 21 queries, with correlated lanes Morpho 39, Reentrancy 43, Oracle 29, Access Control 29, Flash Loan 12. AuditVault: 2383 patterns, with correlated families oracle/valuation 241, vault/share math 151, liquidation/LTV 131, async stuck funds/recovery 104, access/roles 91, callback/reentrancy 60, signature/replay 59, upgrade/factory 42. Advisory only, no gate bypass.
- **2 new Foundry falsifier harnesses shipped.**
  - `test/request/GruntH20RequestCorpusReplay.t.sol`: 5 tests for offer nonce replay, invalid-signature nonce rollback, `setNonce` bulk cancellation, and partial PT/YT conservation.
  - `test/request/GruntH21RequestFactoryInit.t.sol`: 6 tests for Request/PT/YT proxy reinitialization rejection, non-beacon-owner upgrade rejection, and initialized state preservation after beacon-owner upgrade.
- **Regression suite clean.** New harnesses: 11 passed. Request suite: 417 passed. NSS validator: 24 passed. Full NSS suite: 881 passed, 12 skipped.
- **Gate result:** `submit_ready=0` for the 3F Grunt track. New H20/H21 lanes are honest-zero within deterministic falsifier scope; carry-forward is PositionManager/Morpho stateful H20/H1, Facility guardian replay matrix, fund-adapter async fuzz, and TransferGuard/factory zero-delta matrix.

### v6.19 — 3F Grunt Cantina round 3 audit-gap falsifiers (session-23)

- **7 new Foundry falsifier harnesses shipped.** Targeting audit-acknowledged / risk-accepted findings extracted from the ChainSecurity + Cantina reports. 46 tests total across 7 files, all green on pinned commit `89cbfa01e5d14c34354ef715757bc84289cc2d04`.
  - `test/manager/GruntH13ExternalDebtFeeInflation.t.sol`: 8 falsifiers + 2 smoke (10 tests). Verifies Cantina 3.3.21 ME-info dynamic — management=0 PM + external Morpho.repay(500e18, shares) → ~92.59e18 perf-fee shares minted to feeRecipient on next accrueInterest(). Documents the dynamic with quantitative magnitude.
  - `test/request/GruntH14FlashLoanExecutorScope.t.sol`: 7 falsifiers. Verifies Cantina 3.3.25 M finding — flash loan executor role correctly routes to whitelisted scripts; non-whitelisted scripts revert at storage-write gate.
  - `test/request/GruntH15DeadlineAutoFlipDrain.t.sol`: 5 falsifiers + smoke. Verifies Cantina 3.2.1 H (accepted) — preDeadline syncRepaidStatus is no-op; postDeadline forces flip; pullFunds reverts once deadline-lock engages; PT redeem yields zero without a separate repayment.
  - `test/facility/GruntH16ClaimBlockedTokenDoS.t.sol`: 5 falsifiers + smoke. Verifies Cantina 3.2.2 M finding — claim() iterating per-token entries; per-token fail does not block downstream tokens.
  - `test/borrow/GruntH17PreLiquidateMEV.t.sol`: 6 falsifiers + smoke. Verifies Cantina 3.3.6 M (partial fix) — intervening Morpho activity shifts computed (seized, repaid) amounts without necessarily reverting; expected market balance checks catch front-running on the path-direction where previewed results diverge.
  - `test/request/GruntH18OnRequestConsumedReentrancy.t.sol`: 6 falsifiers + smoke. Verifies Cantina 3.2.5 M (acknowledged) — callback can invoke `syncRepaidStatus` from inside `consume()`; pre-deadline it's a no-op (returns false); post-deadline the forced flip is observable but `pullFunds` remains the gating primitive and reverts.
  - `test/funds/pareto/GruntH19ParetoEpochGating.t.sol`: 6 falsifiers + smoke. Verifies Cantina 3.3.22/23 + 3.4.7 (all ME/Info acknowledged) — keyring withdraw disabled blocks redeem-create; fresh tranche deposit commit succeeds; instant-withdraw detection reverts; creation gating surface all-in-one test.
- **Regression suite clean.** `test/manager/*` 231 tests, `test/borrow/*` 180 tests, `test/funds/*` 426 tests, `test/request/*` 406 tests, full project 1795 tests pass (1 skipped). No regressions.
- **NSS validators added.** 7 new v6.19 harness presence checks in `tests/test_native_grunt.py` (21 checks total); full NSS suite 878 passed (+12 skipped, +7 from v6.18).
- **H14-H19 honest-zero, H13 documents acknowledged dynamic.** All 6 falsifier surfaces for H14-H19 do not flip within exercised scope. H13 records the Cantina 3.3.21 perf-fee-skim dynamic with quantitative measurement (donation 500e18 → feeRecipient shares 92.59e18).
- **Gate result:** `submit_ready=0` for the 3F Grunt track. v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain the active `submit_ready=1` packs (human gate pending). No autonomous submission.

### v6.18 — 3F Grunt Cantina round 2 falsifiers (session-22)

- **4 new Foundry falsifier harnesses shipped.** Targeting H9 (preLiquidate math), H10 (CentrifugeFund pollution), H11 (burn multi-position), H12 (perf fee bad-debt). 23 tests total across 4 files, all green on pinned commit `89cbfa01e5d14c34354ef715757bc84289cc2d04`.
  - `test/borrow/GruntH9PreLiquidateMath.t.sol`: 6 falsifiers + smoke, 2 fuzz tests. Verifies repaidShares mode never causes Morpho health-check DoS, seizedAssets mode always leaves position healthy, diluted share markets don't allow free collateral extraction, successive partial liquidations preserve health, and LLTV boundary liquidation doesn't DoS.
  - `test/funds/centrifuge/GruntH10CentrifugePollution.t.sol`: 3 falsifiers + smoke. Verifies attacker vault deposits don't inflate unlock output, don't cause premature unlocking with permanent loss, and don't interfere with RECOVERING state recovery.
  - `test/manager/GruntH11BurnMultiPosition.t.sol`: 4 falsifiers + smoke. Verifies burn with different LTV positions, with interest accrual, with dust rounding, and with SEQUENTIAL strategy all maintain per-position safeLtv.
  - `test/manager/GruntH12PerfFeeBadDebt.t.sol`: 4 falsifiers + smoke. Confirms perf fee skip on bad-debt recovery (documented), management fee is 0 during bad-debt, fee avoidance requires oracle manipulation (trusted), and partial bad-debt doesn't zero lastDebt.
- **Regression suite clean.** `test/manager/PositionManager*.t.sol` 221 tests pass, `test/borrow/MorphoBorrowPosition.t.sol` 143 tests pass, `test/funds/centrifuge/CentrifugeFund.t.sol` 108 tests pass. No regressions.
- **Static probe re-confirmed.** All 9 canonical invariants still present on the pinned commit.
- **NSS validators added.** 4 new v6.18 harness presence checks in `tests/test_native_grunt.py`; full NSS suite 871 passed (+12 skipped, +4 from v6.17).
- **H9/H10/H11/H12 honest-zero.** All 4 hypotheses do not flip within the targeted falsifier surface. Key observations: preLiquidate math rounding is compensated by mulDivUp ceilings; CentrifugeFund pollution is handled by partial-fill support; burn skipLtvCheck is safe by construction; perf fee avoidance requires trusted oracle manipulation.
- **Gate result:** `submit_ready=0` for the 3F Grunt track. v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain the active `submit_ready=1` packs (human gate pending). No autonomous submission.

### v6.17 — 3F Grunt Cantina execution falsifiers (session-21)

- **H4 falsifier harness shipped.** Added `sources/3f-grunt/repo/test/manager/GruntH4PositionManagerLtv.t.sol` with 6 falsifier tests (+ 1 inherited `test_empty`): aggregate-LTV non-increase across round-trip, single-queue sequential withdraw bound, share-price stability after dust burn, hand-mulDiv parity with `PositionManagerLP.burn`, per-BP safe-LTV bound across full-queue proportional burn, levered-slice performance-fee basis bounded by NAV. All 7 tests green on pinned commit `89cbfa01e5d14c34354ef715757bc84289cc2d04`.
- **Regression suite clean.** `test/manager/PositionManager*.t.sol` 221 tests pass, `test/request/Request*.t.sol` 135 tests pass, `test/borrow/MorphoBorrowPosition.t.sol` 143 tests pass. No regressions in the Grunt source tree.
- **Static probe re-emitted.** All 9 canonical invariants still present on the pinned commit; envelope at `data/security_results/investigations/2026-06-25-v6-16-3f-grunt-static-probe/grunt_static_probe.json`.
- **NSS validator added.** `tests/test_native_grunt.py::test_v617_h4_falsification_harness_present` keeps the Foundry harness presence logged; full NSS suite 867 passed (+12 skipped, +1 from v6.16).
- **H4-prime honest-zero.** H4 does not flip within the targeted falsifier surface. Per `AGENTS.md`, the 6-of-6 green is recorded as "documented protections hold under targeted rounding/LTV transitions", not "no bug exists". v6.18 carry-forward: H1 production-bootstrap scaffold, H8 nested-callback harness, Stateful-fuzz over H4 surface.
- **Gate result:** `submit_ready=0` for the 3F Grunt track. v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain the active `submit_ready=1` packs (human gate pending). No autonomous submission.

## [6.16.0-grunt-session20] — 2026-06-24

### v6.16 — 3F Grunt Cantina deep-dive substrate (session-20)

- **3F Grunt source pinned.** Fetched `3FLabs/grunt` shallow 50 commits to `sources/3f-grunt/repo`; pinned at `89cbfa01e5d14c34354ef715757bc84289cc2d04`. Audit PDFs available in-repo at `sources/3f-grunt/repo/audits/` (ChainSecurity 2026-04 core+funds, Cantina 2026-05 audit + fee review). Audit baseline `chainsecurity_grunt=7056bb17257b7745fed054e7ba158f5f48cfda2c` captured in `sources/3f-grunt/source_manifest.json`.
- **In-scope inventory.** Walked all 103 Solidity files under `src/`: 102 in-scope, 1 out-of-scope (`src/facility/IntentDescriptor.sol`).
- **NativeHarness added.** Added `src/night_shift_security/native/grunt.py` exposing canonical 4-byte selectors for Facility (Intents / LP / PM / Requests / Funds / Swap / top), Request (with min/max-balance and mint-to-repaid delay), PositionManager (deposit / withdraw / burn / supply / withdrawal queue / rebalance / transfer guard), MorphoBorrowPosition (including preLiquidate and onMorphoRepay), TransferGuard, and USCCFund. Recorded role groups, EIP-712 typehashes (`SWAP_PARAMS_TYPEHASH`, `SET_FUND_PARAMS_TYPEHASH`, `SET_REQUEST_PARAMS_TYPEHASH`), PositionManager constants (`VIRTUAL_ASSETS=1`, `WAD=1e18`, `MAX_MANAGEMENT_FEE_BPS=200`, `MAX_PERFORMANCE_FEE_BPS=5000`, `MAX_REBALANCE_LOSS_BPS=1000`), and a 10-item bounty out-of-scope summary.
- **Static probe added.** `hermes/scripts/v6_16_grunt_static_probe.py` reads the cloned repo, re-checks 9 canonical invariants (facility role constants, `_checkSignatures`, Request min/max balance, syncRepaidStatus, virtual-share-offset formula, burn virtual-share-in-denominator, Morpho preLiquidate two-paths, `expectedMarketBalances`, TransferGuard `addressStatus`), and emits `data/security_results/investigations/2026-06-24-v6-16-3f-grunt-static-probe/grunt_static_probe.json`. All 9 invariants confirmed on the pinned commit.
- **Hypothesis ledger.** 8 entries (H1/H3/H4/H5/H6/H7/H8-prime variants plus a designated H6 SC-wallet replay note) with explicit Cantina out-of-scope kill-criteria per item so the next session can run the qualified subset.
- **Tests.** 9 new pytest cases (`tests/test_native_grunt.py`); full suite `866 passed, 12 skipped`.
- **Gate result:** `submit_ready=0` for the 3F Grunt substrate. v6.15 WEB-003 and v6.13 NSS-ONRE-1 remain the active `submit_ready=1` packs.

### v6.15 — Origin Protocol web attack surface: WEB-003 blind-trust aggregator API finding (session-19)

- **Origin web source pinned.** Added `OriginProtocol/origin-defi` at `333ba8b` (archived 2025-09-17) to `sources/origin/source_manifest.json`. Full clone remains local (`.gitignored`).
- **Web attack surface mapping.** Mapped all 7 routes (`/oeth`, `/ousd`, `/os`, `/super`, `/ogn`, `/arm`, `/oeth/bridge`) and 30+ swap actions across 5 product pages. Classified each route as safe (`simulateContract` with hardcoded addresses) or vulnerable (`sendTransaction` with raw API data).
- **6 hypotheses falsified.** XSS via `dangerouslySetInnerHTML` (static SVGs only), `postMessage` hijack (none), `sessionStorage` exfil (none), URL param poisoning (regex-validated), cross-chain CCIP confusion (safe), OGN delegate injection (regex-validated).
- **WEB-003 finding.** `magpie.swap()` and `openOcean.swap()` forward API-returned `to`/`data`/`value`/`chainId` to wagmi's `sendTransaction()` without any `simulateContract`, allowlist check, chain ID validation, or calldata inspection. OpenOcean has `openOceanExchangeAddresses` used in `approve()` but NOT in `swap()` — proving code defect, not design choice. Magpie `approve()` uses untrusted API `targetAddress` as ERC-20 spender.
- **Live reproduction.** Vitest test (`web-003.poc.test.ts`) imports the ACTUAL `magpie` and `openOcean` route objects from Origin's source, mocks `@wagmi/core` and `axios`, captures `sendTransaction` arguments. 6/6 tests passed. 0 `simulateContract` calls before `sendTransaction` in either vulnerable path.
- **Evidence package.** Captured `sendTransaction` args JSON, wallet prompt comparison (legitimate vs. malicious MetaMask prompts), 5 false-positive control tests, standalone differential script (`run_poc.mjs`). Secret Gist: https://gist.github.com/tradewife/939dd67356e672d0792496990da6dd00
- **Immunefi mapping.** Impact IDs 1358 (tampering with wallet txs), 1357 (wallet interaction modification), 42 (direct theft). All Critical, $25K flat, Primacy of Rules.
- **Gate result:** `submit_ready=1` for WEB-003, human gate pending. v6.14 Origin ARM/Morpho candidates remain `submit_ready=0`.
- **Tests:** Not applicable (finding is in third-party source, not NSS pipeline).

### v6.14 — Origin Protocol ARM + Morpho V2 cross-chain research pivot (session-18)

- **Origin source pinned.** Added `sources/origin/source_manifest.json` for `OriginProtocol/arm-oeth` at `7e0c4868f341744f03ac45445254a1ace6e56338` and `OriginProtocol/origin-dollar` at `d78437879c5e96a5af2243ca1fd3cc92209192b4`. The full third-party clones remain local working copies, not required for the committed evidence pack.
- **ARM JIT discount-release PoC.** Added research artifacts under `data/security_results/investigations/2026-06-23-origin-deep-forensic/` plus `data/security_results/bounty/research/origin/ORIGIN-ARM-JIT-1.json`. Local Foundry PoC measured a just-in-time LP capturing `1 WETH` of pending base-asset redemption discount release with `crossPrice=0.998e36`, `P=1000`, and attacker deposit equal to pre-claim TVL.
- **PoC hardening.** Added a committed PoC evidence copy at `data/security_results/investigations/2026-06-23-origin-deep-forensic/evidence/Origin_JitClaimRedeem_PoC.t.sol` and a 1,000-run fuzz property proving JIT profit is bounded by `pendingAssets * (1 - crossPrice)` in the modeled setup.
- **Live materiality check.** Queried live Ethena ARM at Ethereum block `25381386`: `paused=true`, `pendingRedeemAssets=0`, `crossPrice=0.99996e36`, and current extractable value `0`. At that 0.4 bps discount, a hypothetical `10,000,000 USDe` pending queue releases only `400 USDe` absolute value before attacker dilution.
- **Morpho V2 cross-chain review.** Queried OUSD CrossChain Master on Ethereum and Remote on Base: both at nonce `24`, no pending transfer, and Master cached balance `9.965163 USDC` lower than Base Remote actual balance. This is a conservative undercount, not a value-moving over-credit. No cross-chain submission candidate survived.
- **JIT monitoring.** Added `hermes/scripts/nss_origin_jit_monitor.py`, a read-only monitor that flags when Ethena ARM is unpaused with non-zero `pendingRedeemAssets` and prints materiality estimates. Latest output is stored at `data/security_results/investigations/2026-06-23-origin-deep-forensic/evidence/jit_monitor_latest.json`.
- **Gate result:** Origin remains `submit_ready=0`. `ORIGIN-ARM-JIT-1` is research-grade only until live materiality improves. No autonomous external disclosure.
- **Tests:** ARM PoC `4 passed`; ARM ClaimRedeem regression `16 passed`; full NSS suite `857 passed, 12 skipped`.

### v6.13 — OnRe deep dive + Token-2022 redemption validator finding (session-17)

- **OnRe source pinned.** Cloned `onre-finance/onre-sol` to `sources/onre/repo` at commit `361cd588ba48b89a44236801140cdc2b5d110251`; recorded `sources/onre/source_manifest.json`.
- **NativeHarness added.** Added `src/night_shift_security/native/onre.py` with the OnRe program ID, 38-instruction discriminator surface, IDL loader, PDA seed manifest, and high-signal bounty surface list. Added `tests/test_native_onre.py`.
- **Ultrafuzz artifacts written.** Investigation directory: `data/security_results/investigations/2026-06-22-v6-13-onre-deep-dive/` with setup, property fan-in, Token-2022 strategy, runs log, static probe output, adjudication, and summary.
- **Candidate confirmed.** Static probe found a Token-2022 transfer-fee accounting asymmetry: offer execution rejects fee-bearing mints, while redemption request/fulfill/cancel paths do not apply the same guard and record gross request amounts. Validator PoC confirmed requested `100000000000`, redeemer after `0`, vault `95000000000`, request amount `100000000000`, plus cancel rejection.
- **False-positive controls passed.** SPL Token and Token-2022 zero-fee controls cancel cleanly; 5% Token-2022 fee control matches exact `5000000000` fee, cancel/fulfill fail as expected, and top-up cancel returns only net. Dumped deployed binary replay also reproduces the issue; current mainnet config exposure appears configuration-dependent.
- **Execution substrate fixed.** Solana 2.3.7 platform-tools v1.48 produced an SBFv1 artifact; LiteSVM 0.8 remained incompatible, LiteSVM 0.7 executed the first control then aborted, so the final PoC used `solana-test-validator` with the program loaded as upgradeable.
- **Gate result:** `submit_ready=1` locally, human gate pending. Added `data/security_results/bounty/submittable/onre/NSS-ONRE-1.json`.
- **Tests:** NSS full suite `857 passed, 12 skipped`.

### v6.12 — Drift Crucible harness fix + engine-level honest-zero (session-16)

- **Root cause of v6.11 0% success rate discovered and fixed.** Two harness bugs: (1) wrong `DRIFT_PROGRAM_ID` bytes decoded to `FeT7anGCrq...` instead of `dRiftyHA39...`; (2) deployed BPF compiled from post-comment-out source (commit `e32903b`, 2026-04-01) with empty Anchor dispatch table, causing `InstructionFallbackNotFound` for all instructions.
- **BPF rebuilt from pre-comment-out source.** Checked out files from commit `27e0e05` (parent of `e32903b`), fixed `ahash` dependency (downgraded to 0.7.4/0.8.11 for `stdsimd` compatibility), rebuilt with `cargo build-sbf --arch sbfv1`. New BPF: 6,091,136 bytes, e_machine=247 (BPFv1).
- **Discriminator investigation.** Confirmed Anchor 0.29 uses `SHA256("global:<snake_case_name>")[..8]`. On-chain IDL uses camelCase names (post-processed), but discriminators are computed from original snake_case source. No discriminator bytes appear as literals in the BPF due to SBF compiler optimizations. The `drift-macros` crate does NOT generate custom dispatch (only `assert_no_slop` and `legacy_layout` proc-macros).
- **5-minute fuzz campaign results.** 186,589 executions at 653.6 exec/sec, 27.3% success rate (400,959 OK / 1,466,185 total), 9/9 actions discovered, 0 crashes, 0 invariant violations. Edge coverage: 909/105,382 (0.9%), branch coverage: 827/52,691 (1.6%).
- **Engine-level honest-zero (bounded).** The 9-action surface with conservation invariant produced zero crashes in 186K executions. Bounded by limited action surface (no SpotMarket/PerpMarket/oracle accounts pre-created).
- **Gate result:** `submit_ready=0`. No candidate produced. `qualifies_for_submission()` not invoked.

### v6.11 — Crucible+Drift in-scope surface (session-15)

- **Crucible engine first execution.** Installed Crucible CLI (`cargo install --path sources/crucible/repo/crates/crucible-fuzz-cli`), fetched deployed Drift BPF from mainnet (`solana program dump dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`), converted legacy IDL to modern format via `anchor idl convert`, and built a working Crucible harness at `sources/crucible/fuzz/drift/`.
- **Session-9 scope error corrected.** Re-read Drift `SECURITY.md` item #4: *"Incorrect data supplied by third party oracles (this does not exclude oracle manipulation/flash loan attacks)."* Oracle manipulation and flash loan attacks ARE in scope up to $500K critical. Session-9 incorrectly excluded the entire oracle surface for 5+ sessions.
- **Harness with 9 actions via raw_call.** `action_init_user`, `action_deposit`, `action_settle_pnl`, `action_settle_funding`, `action_update_funding_rate`, `action_liquidate_perp`, `action_place_perp_order`, `action_cancel_order`, `action_advance_slots`. All use `raw_call` with hardcoded 8-byte Anchor discriminators from the modern IDL.
- **Substrate limitation identified.** LiteSVM does not persist CPI-created account data from within BPF programs. The Drift `initialize` instruction "succeeds" but the State PDA has 0 data bytes, causing all subsequent instructions to be rejected (0% success rate, 5.9 actions/exec). Coverage stuck at 184/4260 edges (4.3%), 166/2130 branches (7.8%). Fix: pre-write State PDA with Drift State struct binary layout in `setup()` — carry-forward for v6.12.
- **FNR claim downgraded.** The v6.11 Drift datapoint is recorded as "substrate-wiring datum" not "empirical-FNR datum" because only 1 of 249 instructions was effectively exercised and the 0% success rate means no production logic was tested. Engine-level empirical-FNR dataset remains N=3 (Marginfi x2 + KLend engineering-blocked).
- **Flash Trade observational.** Per user direction, Flash Trade confirmed as having no Immunefi/Cantina bug bounty. Read-only queries only (health_check, get_trading_overview). No `sign_and_send` or `open_position` calls. Observational patterns documented in lab notebook.
- **Gate result:** `submit_ready=0`. No candidate produced. `qualifies_for_submission()` not invoked.
- **Tests:** 846 passed, 12 skipped (up from 783 baseline).

### Ultrafuzz discovery workflow skill

- Added repo-managed Hermes skill `ultrafuzz-discovery`, adapted from Monad Foundation's Ultrafuzz workflow (`https://blog.monad.xyz/blog/ultrafuzz`) for NSS discovery work.
- Wired the skill into the shared agent checklist for this Droid, future orchestrators, and Hermes cron: `AGENTS.md`, `hermes/SOUL.md`, `hermes/DAY_SOUL.md`, `hermes/NIGHTSOUL_NSS_V4.md`, `hermes/skills/hipif/SKILL.md`, `hermes/skills/day-shift-cycle/SKILL.md`, and `hermes/cron/nss-hipif-chain.prompt.md`.
- Added optional cron recipe `nss-ultrafuzz-agent-discovery` in `hermes/cron/jobs.example.yaml` for executable harness/fuzz/mirror follow-up after deterministic HIPIF and proposal mining.
- Encoded v6.10 gotchas as checklist rules: fixed-input libFuzzer replay is not fuzzing; empty action sequences do not support honest-zero; preserve failures before harness edits; classify harness artifacts separately from production defects.
- Cloned Asymmetric Research Crucible (`https://github.com/asymmetric-research/crucible`) into `sources/crucible/repo` and incorporated Crucible expert-use guidance into `ultrafuzz-discovery` as the preferred Solana invariant sequence-fuzzing path when a program `.so` plus IDL or raw-call bindings are available.

## [6.10.0-session14] — 2026-06-22

### Ultrafuzz-informed KLend mirror attempt + Marginfi flash-loan Path B

- **Outcome:** Corrected engine-level honest-zero. v6.10 now has real libFuzzer exploration evidence, not fixed-input replay: 5/5 pass@k runs passed with executed units `[283885,277065,276515,275365,265135]`, flash actions observed in every counted run, `fixed_input_replay=false`, and panic count 0. Long fuzz ran 86s with 938,090 executions, 10,908 exec/s, start rejects 80,259, end rejects 21,456, panic count 0.
- **KLend mirror Path B:** Added `sources/kamino/klend_mirror/` Anchor 0.31 scaffold and replaced the invalid placeholder id with valid pubkey `G9cZAWjKwksrb2fRxD3DxULMn6o6r4BhhxXNxxdXfrnA`. Build remains blocked by Solana platform-tools Cargo 1.79 vs `hashbrown` `edition2024`; blocker recorded in `data/security_results/investigations/2026-06-22-v6-10-mirror-attempt-1/build_status.md`.
- **Marginfi flash-loan Path B:** Added `lend_flash_loan` fuzz target plus start/end flash-loan helper APIs and synthetic instructions sysvar construction so the fuzz engine exercises the flash-loan surface. Expected flash-loan rejections are classified and logged instead of being treated as production panics.
- **Orchestrator correction:** Added `hermes/scripts/v6_10_flash_orchestrator.py`, corrected to run corpus directories with `-max_total_time`, parse executed units, reject fixed-input replay, require observed flash actions, and preserve per-attempt artifacts under `data/security_results/investigations/2026-06-22-v6-10-mirror-attempt-1/`.
- **Gate result:** No gate-passing production candidate. `submit_ready=0`; no external submission, no gate loosening, and no fixture-only claim.

## [6.9.0-proposal-session13] — 2026-06-21

### KLend engine execution attempt: discriminator-blocked engineering discovery

- **Outcome**: **Discriminator-blocked.** v6.9 successfully built a real executable test harness from the v6.8 stub. Validator boots in 3s with the deployed klend.so loaded. The deployed BPF rejects every standard anchor-lang sighash variant for `initLendingMarket` (and by induction, every other KLend instruction). v6.9 records a *discriminator-engineering discovery* rather than a bug-finding. `submit_ready` remains 0. Empirical-FNR extended from engine N=1 (Marginfi) to N=2 (Kamino, engineering-blocked).
- **What v6.9 built**:
  - Resolved npm dep conflict: `@project-serum/anchor ^0.25.0` → `@coral-xyz/anchor ^0.31.1` + `@solana/spl-token ^0.4.14` + `@solana/web3.js ^1.95.0`.
  - Rewrote `sources/kamino/klend/tests/flash_loan_fuzz.ts` from 559 lines of scaffolding stubs to ~840 lines of real transaction-construction logic using raw serialization (no Anchor workspace).
  - Updated `tsconfig.json` to target `es2020` + include only the new harness file (excluding the legacy `tests/klend.ts`).
  - Built 11 control + K-2c-vault-conservation attempt shells ready to drive strategy execution.
  - Re-wrote `setupMarketAndReserve` to match the protocol-required topology per `programs/klend/src/handlers/handler_init_reserve.rs`.
  - Validator boots in 3s as `solana-test-validator 2.1.20`, KLend BPF loaded as upgradeable program at the deployed pubkey, payer airdrop succeeds, initial SPL token setup tx succeeds.
- **What v6.9 discovered (engineering diagnosis)**:
  - All four standard sighash schemes rejected by the deployed BPF. `initLendingMarket` discriminators attempted: `6db4bb1d2508c11f` (raw-name anchor 0.29), `d0e33898a37b8b57` (global: prefix anchor 0.30+), `95cfa8e1104f450e` (anchor:), `2ebb0b0a61f7b1a7` (anchor:ix:). All elicit `AnchorError::InstructionFallbackNotFound (0x65 / 101)`.
  - Static-binary-pattern search of `klend.so` (10 MB) returned 0 matches across 60 ix names × 5 prefix variants — consistent with anchor-lang 0.29+ computing sighash at runtime rather than embedding as a static array; **but the runtime computation still rejects our wire signature**, so the deployed-BPF was built against a pre-image convention not covered by any published scheme.
  - Three plausible explanations logged: (1) klend used a fork of anchor-lang with custom sighash scheme, (2) custom MacroDerived entrypoint computes sighash over non-trivial pre-image, (3) `tests/fixtures/klend.so` was downloaded at the wrong deployment date.
  - Diagnose verified by a standalone Rust probe (`/tmp/anchor-sighash-probe`, pinned to Rust nightly + solana-program 1.18 for anchor-lang 0.29.0 compatibility) that emits all 60 instruction sighashes for both raw-name and global: schemes.
- **Post-conviction**: substrate-engine execution surface is **now operational**. The harness can drive any instruction whose ix-discriminator matches the deployed-BPF scheme. v6.9 sets up the boundary condition for v6.10+ to lift either via (a) build kamino locally with anchor-cli 0.29 (now installed via avm), (b) write a kamino-mirror test program in anchor 0.31, or (c) source-review klend git history between May 2024 and present.
- **Promoted to v6.10+**: Path B (kamino-mirror test program, preferred); Path C (rebuild klend, alternate); H2 full executable; H5 full executable; H5 mainnet-exposure check (blocked by Alchemy compute-units 24h cooldown).
- **Trust boundary preserved**: no gate loosening, no auto-submit, no sentinel coercion, no fixture-only claims. Honest-zero recorded honestly as a discriminator-blocked engineering datum. Source-review honest-zero from v6.8 preserved unchanged.
- **Untouched**: AGENTS.md, root docs, hermes profile, native_harness_status.json. No external API writes, no auto-submit.

## [6.8.0-proposal-session12] — 2026-06-21

### Ultrafuzz 4-phase campaign on Kamino KLend flash-loan path ($1.5M bounty)

- **Outcome**: Honest-zero at source-review level. 5 hypotheses traced through the fee calculation chain; 3 falsified with high confidence, 2 underspecified (require executable testing). 6th substrate-level empirical-FNR datum recorded. `submit_ready=0`.
- **4-phase workflow**: Properties (12 invariants) -> Strategies (5 hypotheses) -> Forensic tracing -> Quorum adjudication. Following the Ultrafuzz post's methodology (https://blog.monad.xyz/blog/ultrafuzz): each hypothesis is an independent attack angle with its own kill criterion and source anchor.
- **Hypotheses falsified**:
  - H1 (fee bypass via reserve state mutation): `calculate_flash_loan_fees` reads ONLY `flash_loan_fee_sf`, `referral_fee_bps`, `has_referrer` -- NOT cumulative_borrow_rate, borrowed_amount, or total_available. Fee is structurally independent of reserve state.
  - H3 (multi-flash-loan bypass): `flash_borrow_checks_internal` scans forward in same transaction only. Cross-block flash-loans are independent sequential transactions.
  - H4 (fee precision loss): `BorrowTooSmall` guard prevents fee >= amount; minimum_fee = 1u64 enforced. Flash-loan operations do NOT mutate `reserve.config.fees`.
- **Hypotheses underspecified** (require executable testing):
  - H2 (obligation health check race): Flash-loan path does not interact with obligations; requires test with obligation + flash-borrow + liquidation in separate transactions.
  - H5 (Token-2022 double-charge): SPL Token-2022 transfer fee extension may deduct transfer fee IN ADDITION to flash-loan fee; requires Token-2022 reserve setup.
- **Infrastructure prepared**:
  - BPF binary: `sources/kamino/klend/tests/fixtures/klend.so` (dumped from mainnet via Alchemy RPC)
  - IDL: `sources/kamino/klend/target/idl/klend.json` (fetched from deployed program, 8685 lines)
  - Test harness: `sources/kamino/klend/tests/flash_loan_fuzz.ts` (Anchor TS, 559 lines, 5 strategies x 3 attempts)
  - Orchestrator: `hermes/scripts/v6_8_ultrafuzz_orchestrator.py` (212 lines)
- **Empirical-FNR dataset (N=6, source review)**: Ethena, Marginfi v2, Kamino (v6.3), Drift, Meteora DLMM, Kamino KLend (this session) -- all honest-zero.
- **Deferred to v6.9+**: (a) resolve npm dependency conflict (`@project-serum/anchor` vs `@coral-xyz/anchor`) and run test harness on `solana-test-validator`; (b) H2/H5 executable tests; (c) build cargo-fuzz harness for Kamino KLend (following Marginfi `fuzz/` template); (d) engine-level N=2 if harness is built.

## [6.7.0-proposal-session11] — 2026-06-21

### Ultrafuzz engine operationalization on Marginfi v2 substrate (pass@k with executable fuzz targets)

- **Outcome**: Honest-zero at engine level for substrate N=1 (Marginfi v2). 0 production defects surfaced at pass@k across 7 attempts × 20 corpus replays + ~846M cumulative libfuzzer iterations in instrumented-release mode over 90s × 2 binaries.
- **What v6.7 actually delivers (vs sessions 5–10)**: a *real* executable fuzz engine harness on the most-tested substrate (Marginfi v2). Prior sessions ran the *wrapper* (multi-attempt + quorum) without the *engine* — re-reading `https://blog.monad.xyz/blog/ultrafuzz` on 2026-06-21 named this as the structural gap. Per the post's autoresearch block: *"two executions of the same prompt had produced two largely disjoint bug sets"* — a single manual-review execution is a biased sample; the bug-class likely hiding is control-flow / edge-ordering / composition (the post's "different types of bugs than a manual review").
- **Marginfi fuzz engine**:
  - New fuzz target `sources/marginfi/repo/programs/marginfi/fuzz/fuzz_targets/lend_extended.rs` — 200-action enum mirroring the original `lend.rs` Action set, harness-artifact suppression policy (action errors are not bug signals; only substrate-invariant verification at end-of-run is).
  - Added to `fuzz/Cargo.toml` as `[[bin]] lend_extended`; builds clean under nightly-2024-06-05.
  - `cargo +nightly-2024-06-05 build` produces `target/debug/{lend, lend_extended}`; `RUSTFLAGS='--cfg fuzzing' cargo +nightly-2024-06-05 build --release` produces instrumented-release binaries.
  - Build persists at `target/release/lend_extended`.
- **Engine orchestrator**: `hermes/scripts/v6_7_engine_orchestrator.py` — pass@k writer; runs 7 attempts (3 binaries × strategies) × 20 seeded corpus inputs and captures `runs.jsonl` per attempt. `hermes/scripts/v6_7_engine_long_run.py` — runs true libfuzzer fuzz mode for 90s per binary with `max_total_time=90 -print_final_stats=1` for raw iteration counts.
- **Empirical-FNR dataset — substrate-level (N=5, unchanged from v6.6) + engine-level (N=1, NEW)**:
  - Substrate-level: Ethena V1, Marginfi v2, Kamino, Drift, Meteora DLMM — source-review honest-zero across all 5.
  - Engine-level: Marginfi v2 — 7 pass@k attempts, 0 panics, 0 abnormal exits, exit_code=0 everywhere. Cumulative crate iterations: **846,081,229** (423,658,407 in `lend` 90s + 422,422,822 in `lend_extended` 90s, instrumented-release).
- **Trust boundary preserved**: no gate loosening, no auto-submit, no fixture-only claims, Kate's human gate for any submission. `qualifies_for_submission()` is authoritative. `submit_ready=0` unchanged. `native_harness_status.json` unchanged (marginfi_v2 stays `ready`, all other harnesses unchanged).
- **Deferred to v6.8+ (engine expansion)**: (a) wire `lending_account_start_flashloan`/`end_flashloan` into the engine — current `marginfi-fuzz` crate lacks `ixs_sysvar` plumbing required for the CPI check; needs `solana-program-test`-based `tests/flash_loan.rs` ts-mocha bankrun substrate (not the fuzz crate); (b) extend the engine to Ethena, Kamino, Drift, Meteora — each requires a per-target fuzz crate that none of the cloned repos ship; (c) per-substrate engine-level empirical-FNR datapoints beyond the one collected here.

## [6.5.0-proposal-session9] — 2026-06-21

### Drift Protocol v2 native harness + post-$285M-exploit in-scope vector enumeration

- **Outcome**: Honest-zero. No exploitable bug found in Drift's in-scope surfaces (the actual $285M exploit class — oracle manipulation + admin key compromise + durable nonces — is explicitly excluded from Drift's bug bounty via SECURITY.md item #4, #2, #3). 4th empirical-FNR datapoint (N=4). Empirical-FNR dataset now bounded across 4 substrates (Ethena, Marginfi, Kamino, Drift).
- **Why this target**: Drift is the largest DeFi hack of 2026 ($285M, April 1, 2026) and the second-largest security incident in Solana history. As principal on-chain forensic investigator, the natural next step is to enumerate residual in-scope vulnerabilities in new post-audit code paths.
- **NativeHarness scaffolded**: `src/night_shift_security/native/drift.py` — Drift v2 program ID (`dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`), top-15 instructions (including `add_liquidity`, `remove_liquidity`, `swap`, `consume_signed_msg_user_orders`, `initialize_signed_msg_user_orders`), IDL loader, account loader, market resolver (`dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH`), `get_slot`/`get_account_info` RPC helpers.
- **Probe driver**: `hermes/scripts/v6_5_drift_probe.py` — executable cross-slot read-only probe, classifies measured impact via `solana_measured_oracle`, OS-locale-corrected.
- **Probe ran on Alchemy Solana mainnet RPC**: pre-state at slot 427822428 (program_lamports=49155476) → post-state at slot 427822443 (program_lamports=49155476), delta=0; classification=`slot_advanced_without_measurable_state_change`. Honest-zero outcome consistent with read-only observation (no transaction broadcast).
- **In-scope surface review** (frame structure for future sessions):
  1. **LP pool constituent arithmetic** (`lp_pool.rs`, 1,898 LOC) — `update_aum()` reads constituents, computes AUM, adjusts for `total_quote_owed`; uses saturating arithmetic throughout. New AMM introduced late 2025, post-Trail-of-Bits-audit.
  2. **`signed_msg_user` order eviction** (`state/signed_msg_user.rs`) — `SIGNED_MSG_SLOT_EVICTION_BUFFER=10` allows slot drift on leader schedule; user-controlled `max_slot` prevents real replay risk.
  3. **`revenue_share` builder/referrer fee accounting** (`state/revenue_share.rs`, 573 LOC) — u64 counter for `total_referrer_rewards`; overflow requires implausible volumes.
  4. **Insurance fund settlement** (`controller/insurance.rs`) — no new code since audit.
- **Honest-zero rationale**: every balance-modifying operation in Drift uses `safe_add`/`safe_sub`/`safe_mul`/`safe_div` (4,200+ source call sites). The new `lp_pool.rs`/`signed_msg_user.rs`/`revenue_share.rs` are defended by the same wrappers. Source-grounded falsification of "unchecked arithmetic bug" hypothesis is *complete* — to find an exploitable in-scope vulnerability, the next session will need to (a) build drift.so BPF and execute test compositions, or (b) look at a different substrate.
- **Tests**: 14 new tests in `tests/test_native_drift.py` covering harness constants, program IDs, discriminators, LP pool / signed_msg instruction presence, IDL/account loaders, SECURITY.md out-of-scope surface, resolve_market failure paths. **All 14 passed.** Full unit suite: **795 passed, 12 skipped** (vs prior 783 passed, 11 skipped; gain is +12 new tests).
- **Trust boundary preserved**: no gate loosening, no auto-submit. Drift excluded: oracle trust, key compromise, governance are explicitly out-of-scope per SECURITY.md and those vectors are NOT promoted to `submit_ready`.

## [6.4.0-proposal-session8] — 2026-06-21

### Marginfi v2 source-grounded property testing (Ultrafuzz engine operationalized, LLM-in-the-loop pass@k)

- **Outcome**: Honest-zero. No exploitable bug found. 3rd empirical-FNR datum (N=3). All 56 executed tests pass. 7 defense layers documented.
- **SPEC.md replaced**: v6.3.0-proposal-session7 header → v6.4.0-proposal-session8. v6.3 §0–§14 content preserved verbatim below the new §0.1; the bump is header + §0 only. Stale deferred paths pruned (§0.4); §0.4 parallel Ultrafuzz deep-read requirement marked SATISFIED (§0.5).
- **Independent Ultrafuzz decomposition (SPEC §0.5)**: the v6.4 orchestrator performed its own deep-read of the Ultrafuzz post and **inverted v6.3's takeaway**. v6.3 took the wrapper (multi-attempt + quorum) and dropped the engine (executable fuzz tests). N=3 honest-zero is the *expected* result of running the wrapper without the engine. v6.4 makes executable fuzzing the core mechanism; multi-attempt is the variance-amplifier on top. Seven leverage points identified (engine > wrapper; emergent disjointness; pass@k cumulative; executable strategy as unit of work; generic + per-target strategies; artifact handoff; 5-judge triage).
- **Path A executed** (was deferred from v6.2): resolved canonical MarginfiGroup + USDC Bank + liquidity vault PDA addresses via multi-source cross-verification (Anchor.toml fixture, on-chain getAccountInfo parsing, Solscan vault authority, transaction ALT expansion) → `sources/marginfi/marginfi_accounts.json`. Updated `marginfi.py` defaults from sentinels to real addresses. marginfi_v2 promoted `scaffolded`→`ready` (ready_count 8→9).
- **BPF build**: installed anchor 0.31.1 via avm, fixed corrupted platform-tools, built marginfi.so + mocks.so as BPF with `mainnet-beta` feature. Test framework verified working.
- **Property enumeration**: 6 invariants documented in `data/security_results/investigations/2026-06-21-v6-4-properties/properties.md` (flash-fee purity, conservation of value, oracle freshness, liquidation oracle consistency, rate limiter bypass, socialize_loss edge case).
- **Source analysis**: Read and analyzed flashloan.rs, liquidate_start.rs, liquidate_end.rs, handle_bankruptcy.rs, socialize_loss, check_account_bankrupt, check_account_init_health, is_signer_authorized, withdraw.rs, accrue_interest, calc_interest_rate_accrual_state_changes, share conversion functions, decrease_balance_internal, SECURITY.md known issues.
- **Key defense layers identified**: (1) `validate_ixes_exclusive` blocks flash loan + liquidation in same tx; (2) `pre_health > post_health` in end_receivership; (3) `is_signer_authorized` blocks self-liquidation; (4) Live prices for bankruptcy determination; (5) Truncation toward zero in share conversions; (6) `validate_not_cpi_by_stack_height` on flash loan and liquidation; (7) 471 existing tests covering all major operations.
- **Trust boundary preserved**: no gate loosening, no auto-submit, no sentinel coercion, no fixture-only claims, Kate's human gate for any submission. `qualifies_for_submission()` is authoritative.

## [6.3.0-proposal-session7] — 2026-06-21

### Three-attempt forensics on Kamino flash_borrow composition (Ultrafuzz-pattern, LLM-as-orchestrator)

- **SPEC.md replaced**: v6.2.0-proposal-session6 header → v6.3.0-proposal-session7. v6.2 §0–§14 content is preserved verbatim below the new §0.1 + §0.3 deferred-items table; the bump is header + §0 only.
- **Operating-model acquisition**: the post-v6.2 reflection observed that the chain was too linear/mechanical and not generating enough disjoint high-signal attack surfaces. Reading the Ultrafuzz reference (Monad Foundation, https://blog.monad.xyz/blog/ultrafuzz) made the gap concrete: gains came from (a) **multiple isolated LLM attempts** on the same scaffold, (b) **artifact-based handoff** between stages, (c) **quorum adjudication** of findings. v6.3 operationalizes that pattern *inside the orchestrator session itself* — the LLM in the loop is the orchestrator; "fresh context per attempt" = distinct analytic frames; "quorum" = a self-adjudication rubric that distinguishes production defect / underspecified behavior / harness artifact / false-positive (Ultrafuzz's evaluation taxonomy).
- **Highest-signal angle chosen defensibly**: Kamino KLend `flash_borrow_reserve_liquidity` composition. Justified by `kamino_measured_delta.json` showing `cumulative_borrow_rate` advance across slots 427417165→427417221 with `borrowed_amount_sf` constant — the on-chain signature of an autonomous state advance on a fully-ready substrate with live fixtures. Marginfi Path A deferred because it depends on canonical PDA discovery; cross-substrate differential deferred as broader-but-shallower.
- **Three disjoint frames**: (1) **repay-timing race** — does the flash repay use pre- or post-flash `borrowed_amount_sf`? (2) **cumulative-rate I80F48 ceiling** — does rate-WAD math saturate in a way that lets depositors skim yield? (3) **flash-callback CPI composition** — can a flash callback invoke `refresh_reserve`/`deposit_reserve_liquidity` between borrow and repay? Each frame has its own kill criterion; artifacts go to `data/security_results/investigations/2026-06-21-v6-3-attempt-{1,2,3}/` with `attempt.md` + `evidence.json` + `README.md`.
- **Quorum self-adjudication**: `data/security_results/investigations/2026-06-21-v6-3-quorum.md`. A finding is promoted only if ≥2 frames independently surface the same root cause with the same kill-criterion outcome; single-frame findings are recorded as `single-frame-candidate`. **The existing `qualifies_for_submission()` gate and submission path remain authoritative — nothing here loosens any gate.**
- **Path A formally deferred** to v6.4 (canonical MarginfiGroup + USDC bank PDA seeds via SDK resolution / filtered `getProgramAccounts` / explorer paste). Topology-runner scaffolding deferred to v6.5 if the three-frame structure proves its worth.
- **No harness flip**: `data/security_results/loop/native_harness_status.json` is unchanged. kamino stays `ready`; marginfi_v2 stays `scaffolded`; ethena_native stays `scaffolded`. The three frames build on the already-captured kamino evidence — they do not require new RPC fixtures.
- **Trust boundary preserved**: HermeS orchestration, gates, cron, and `metadata.trusted=false` for any LLM output are unchanged. The orchestrator (this session) is the only LLM step.

## [6.2.0-proposal-session6] — 2026-06-20

### MarginFi v2 NativeHarness onboarding + novel-vec probe
- **SPEC.md replaced**: v6.1.0-proposal-session5 → v6.2.0-proposal-session6 single-shot Marginfi v2 onboarding + novel-vec probe. v6.1 + earlier versions preserved verbatim in `git log`.
- **Marginfi v2 NativeHarness**: `src/night_shift_security/native/marginfi.py` is a faithful mirror of `kamino.py` (program IDs + top-10 instruction discriminators via `anchor_discriminator` + IDL loader + AccountResolution + resolve_market/resolve_accounts). Marginfi v2 program is `MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA` on Solana mainnet-beta (executable, 1,141,459 lamports — verifiable via canonical `getAccountInfo`).
- **Sibling-substrate generalization**: confirms that the v5 NativeHarness substrate shape (program IDs + survivable losslessness + IDL loader) generalizes across Solana lending protocols: Kamino + Marginfi share a one-to-one code pattern with only `TOP_*_INSTRUCTIONS` differing.
- **Probe driver**: `hermes/scripts/v6_2_marginfi_probe.py` is a read-only cross-slot observation driver that records pre-state at slot N and post-state at slot N+k, persists the evidence envelope at `data/security_results/impact/marginfi_v2_measured_delta.json`, and gates every gate (without modifying any).
- **Honest-zero outcome**: `submit_ready` does not move; `pack_count = 0`. Single blame: `_v4_candidate_submission_ok` correctly blocks on `impact_oracle.measured=False` because the `DEFAULT_MARGINFI_GROUP` / `DEFAULT_USDC_BANK` / `DEFAULT_USDC_LIQUIDITY_VAULT` defaults are documented as `PENDING_*_DISCOVERY` sentinels (the v6.2 session could not derive canonical mainnet addresses from the public Marginfi docs alone — a discovery state, not a security claim).
- **NativeHarness manifest**: `data/security_results/loop/native_harness_status.json` now carries `marginfi_v2` at status=`scaffolded`. `ready_count = 8` unchanged; `scaffolded_count = 2` (ethena_native + marginfi_v2).
- **Tests**: `tests/test_native_marginfi.py` adds 26 tests + 1 skipped (RPC-dependent live-smoke). Coverage spans: program address, top-10 discriminators, IDL loaders, default fallback, AccountResolution round-trip, resolve_market typed rejections (rpc_url_required / rpc_url_unreachable / rpc_no_code_at / rpc_not_executable), resolve_accounts alias, sentinel-default contract, cross-discriminator uniqueness vs Kamino.
- **Foundation for v6.3**: the empirical-FNR dataset is now bounded by 2 datapoints (Ethena EVM + Marginfi Solana), both yielding honest-zero. Next session must populate canonical Marginfi v2 addresses via one of: (a) `@mrgnlabs/marginfi-client-v2` SDK resolution, (b) filtered `getProgramAccounts` by `dataSize`, (c) explorer-paste into `sources/marginfi/marginfi_accounts.json`.
- **Persisted artifacts**: `SPEC.md`, `src/night_shift_security/native/marginfi.py`, `tests/test_native_marginfi.py`, `hermes/scripts/v6_2_marginfi_probe.py`, `data/security_results/impact/marginfi_v2_measured_delta.json`, `data/security_results/bounty/submittable/marginfi_v2/NSS-MFI2-1.json`, `data/security_results/bounty/submittable/marginfi_v2/nss-mfi2-1-gate-trace.json`, `sources/marginfi/repo/LICENSE`, plus three nursinglog entries.

## [6.1.0-proposal-session5] — 2026-06-20

### Empirical-calibration pivot
- **SPEC.md replaced**: v6.0.0-draft → v6.1.0-proposal-session5 single-shot empirical calibration probe. v6.0.0-draft history preserved verbatim in `git log` (commits `617c412`, `2e48c9a`, `c2a2fbe`, `bf14075`, `482fd4f`).
- **First quantitative false-negative rate datum:** `foundry/test/EthenaCalibrationProbe.t.sol` proves the `verifyNonce(address,uint256)` uint64-truncation bug class is reproducible on the deployed EthenaMinting V1 contract at `0x2cc440b721d2cafd6d64908d6d8c4acc57f8afc3` (Lane A PASS) and confirms the collision is not exploitable for direct USDe extraction because per-block mint cap (2,000,000 USDe) + MINTER_ROLE gate + EIP-712 envelope enforcement form a binding constraint (Lane B PASS).
- **Gate trace:** `hermes/scripts/v6_1_calibration_gate_trace.py` exercises every gate in `qualifies_for_submission()` without modifying any of them. Result `qualifies_for_submission=False` with single blame on `_v4_candidate_submission_ok` (correctly gated by `impact_oracle.measured=False`). Persisted at `data/security_results/bounty/submittable/ethena/nss-calib-1-gate-trace.json`.
- **Honest-zero outcome:** `submit_ready` does not move. No gate was loosened; the spec's `NSS_CALIBRATION_LANE` knob is documented but not deployed as runtime code.
- **Persisted artifacts:** `foundry/test/EthenaCalibrationProbe.t.sol`, `data/security_results/impact/ethena_calibration_measured_delta.json`, `data/security_results/bounty/submittable/ethena/NSS-CALIB-1.json`, `data/security_results/bounty/submittable/manifest.json` (updated), `data/security_results/loop/native_harness_status.json` (`ethena_native.status` stays `scaffolded`), and three new nursinglog entries (`data/security_results/lab_notebook/2026-06-20-session-5-calibration-ethena-nonce-collision.md`, `data/security_results/reflection/2026-06-20-calibration-reflection.md`, `data/security_results/self_criticism/2026-06-20-empirical-calibration.md`).

## [6.0.0-draft] — 2026-06-20

### v6 pivot: target rotation + less-audited-program onboarding
- **Audit cycle complete**: Audited 8 well-defended DeFi protocols (Kamino, Uniswap v4, Aave v3, Raydium, Wormhole, Orca, Jito, Morpho). All major attack surfaces (price manipulation, flash loans, reentrancy, integer overflow, access control) are properly defended.
- **VULN-001 FALSIFIED**: Claimed `PoolManager.mint()` unchecked `amount.toInt128()` overflow — FALSIFIED by `SafeCast.toInt128(uint256)` at SafeCast.sol:56-59 which explicitly reverts for `x >= 2^127`. 7 Foundry tests in `UniV4MintOverflowFalsification.t.sol` confirm. False-positive measured-delta artifact deleted.
- **Key insight**: The 8 audited protocols are all audited by OtterSec, Kudelski, Neodyme, Trail of Bits, Spearbit. Novel bug discovery requires new, less-audited targets.
- **v6 strategy**: Target rotation engine that prioritizes less-audited programs (`bounty_usd / (audit_firm_count + 1)`), self-evolving loop, self-documentation.
- **Recommended targets** (in priority order): Reserve Protocol ($10M), Coinbase ($5M), Ethena ($3M), SSV Network ($250K), Pendle ($2M), DeXe Protocol ($500K).
- **New directories**: `data/security_results/self_criticism/` (what hasn't worked), `data/security_results/reflection/` (strategy adaptation).
- **New tests**: 4 Foundry tests for Orca wrapping analysis, 8 Python tests for Orca analysis. Total: 747 passed, 11 skipped.
- **New falsification test files**: `foundry/test/OrcaProtocolFeeWrapping.t.sol`, `tests/test_orca_wrapping.py`.
- **SPEC.md replaced** with v6.0.0-draft spec including target rotation, self-evolving loop, mandatory falsification protocol.

## [5.0.0-draft] — 2026-06-18

### 2026-06-19 — v5 phases 7–11 shipped (SPEC_V5_COMPLETION)
- **Solana NativeHarness substrate:** `native/kamino.py`, `native/jito.py`, `native/raydium.py`, `native/orca.py` — program IDs, Anchor discriminators, IDL loaders, RPC resolvers.
- **Solana MeasuredImpactOracle:** `impact/solana_measured_oracle.py` + capture scripts (`_capture_kamino_measurement.py`, `_capture_solana_slot_measurement.py`).
- **Kamino semantic map:** 153 concrete candidates from `sources/kamino/klend`.
- **Concrete sequences (D6):** `hypothesis/concrete_sequences.py` wired into depth pass via `generate_target_vectors(depth_pass=…)`.
- **Phase 11 discovery:** `NSS_PREFER_SOLANA`, `NSS_DISCOVERY_MISSING_PCT`, +5 Immunefi Solana programs (drift, marginfi, sanctum, meteora, pump).
- **Manifest:** `ready_count=6` — uniswap_v4, aave_v3, kamino, jito, raydium, orca (morpho_blue stays `harness_built`).
- **Bootstrap fix:** `nss-hipif-chain.sh` preserves pre-set `NSS_HIPIF_MODE` over repo `.env` (dryrun tests).
- TESTS: **678 passed, 7 skipped** (+70 net from 608).

### 2026-06-19 — v5 completion roadmap + operator cron apply
- **SPEC_V5_COMPLETION.md** — phases 7–12 roadmap from `SYSTEM_AUDIT_2026-06-18.md` to G1–G5 completion; Solana-first scope (kamino → jito → raydium → orca).
- **hermes/cron/OPERATOR_APPLY.md** — live `nightsoul` cron apply steps (timeout 10800s, env vars, job `343324bfcbb2`).
- **Operator applied:** `cron.script_timeout_seconds=10800`, `.env` production NSS vars, `hermes cron edit` no-agent v5.
- **.env.example** — documents Phase 6+ cron env knobs.

### 2026-06-19 — v5 Phase 6: cron unpause + Phase 4 rotation rollout
- **Decision (Path A):** unpause cron with two ready NativeHarness targets (`uniswap_v4` + `aave_v3`) rather than waiting for Morpho Blue promotion. Rationale: `SYSTEM_AUDIT_2026-06-18.md` D7 discovery mode — real forks against real deployed contracts beats a third harness gate. Morpho Blue stays `harness_built` (honest zero-delta on empty USDC/WETH market).
- **Dryrun validated:** `NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 NSS_HIPIF_BOUNTY_DEPTH=1` bootstrap reaches `HIPIF_CHAIN_READY` with `pause_for_native=0`.
- **Production cron env documented:** `hermes/cron/jobs.example.yaml` now documents `NSS_HIPIF_PAUSE_FOR_NATIVE=0` + `NSS_PHASE4_ROTATION_ENABLED=1` on `nss-hipif-chain`. Script default remains `NSS_HIPIF_PAUSE_FOR_NATIVE=1` for manual safety.
- **AGENTS.md** updated: Phase 6 cron unpaused state, `ready_count=2`, Phase 4 rotation on in production cron.
- **New tests:** `tests/test_cron_unpause.py` (7), +3 in `tests/test_measured_oracle.py`, +4 in `tests/test_phase4_rotation_rollout.py` (cron YAML assertions flipped for Phase 6 rollout).
- TESTS: **608 passed, 6 skipped** (was 594 → +14 net new).

### 2026-06-19 — v5 Phase 5: Aave v3 measured delta + Phase 4 Option B
- **Aave v3 promoted to `ready`**: Foundry fork probe at blocks 25347105-25347205 (100-block window) on live Ethereum RPC. USDC reserve deltas: `liquidityIndex` +1,559,553,810,655,708,363,489; `variableBorrowIndex` +2,024,360,283,185,808,215,593; `isolationModeTotalDebt` +252,930,327. First organic interest accrual proof. Evidence: `data/security_results/impact/aave_v3_measured_delta.json`. Manifest updated: `ready_count=2` (uniswap_v4 + aave_v3).
- **Foundry test rewritten**: `foundry/test/AaveV3Measure.t.sol` uses `vm.createSelectFork` for true cross-block reads (original `staticcall(to, blockNum)` does NOT read at a different block). Added assembly decode for Aave reserve data.
- **Morpho Blue capture script updated**: `scripts/_capture_morpho_measurement.py` rewritten with proper delta computation and evidence schema. Honest zero-delta result: USDC/WETH market has no on-chain positions. Status stays `harness_built`.
- **Phase 4 Option B shipped**: `is_saturated_for_rotation()` added to `bounty/native_picker.py` — skips `harness_built` candidates touched within `rotation_window_days`. Integrated into `pick_next_target_v6_phase4`. Safer default: no production behavior change without explicit opt-in.
- **New tests**: `tests/test_aave_v3_measured_delta.py` (8), `tests/test_morpho_value_moving.py` (5), `tests/test_phase4_rotation_rollout.py` (10), +6 new cases in `tests/test_measured_oracle.py`.
- TESTS: **594 passed, 6 skipped** (was 568 → +26 net new).

### 2026-06-19 — v5 measured-delta phase4 + Aave v3 skeleton
- Morpho Blue measured-delta capture: `foundry/test/MorphoBlueMeasure.t.sol` reads `market(bytes32)` across a 20-block window on live Ethereum RPC. `scripts/_capture_morpho_measurement.py` parses forge output and writes `data/security_results/impact/morpho_blue_measured_delta.json`. Honest zero-delta result: USDC/WETH market (ID `0xb859…`) has no on-chain positions. Status stays `harness_built` per audit C2 (no positive delta).
- Phase 4 rotation opt-in: `NSS_PHASE4_ROTATION_ENABLED` env var (default off) gates `pick_next_target_v6_phase4` in `bounty/native_picker.py`. Cold programs float: `score = (bounty_usd * state_multiplier) * max(days_since_touched, 1)`. `rotate_target()` records `state["last_touched"][slug]`. Wired into `bounty_loop.py` `pick_next_target()` behind the opt-in flag.
- `depth_env()` in `hermes/scripts/nss-hipif-chain-run.py` now sets `NSS_PREFER_FULL_REGISTRY=1` chain-wide (C5 widened from bounty_depth-only). `bounty_depth()` no longer duplicates the override.
- Aave v3 skeleton: `src/night_shift_security/native/aave_v3.py` (10 pool selectors, 7 view selectors, 2 provider selectors, `resolve_pool()` via `getReserveData`). `foundry/test/AaveV3Measure.t.sol` passes against live Ethereum RPC (USDC reserve read at block 25347124). `sources/aave_v3/repo` cloned at `b74526a7` (v1.19.4). Manifest: `aave_v3: harness_built`.
- `tests/test_native_aave_v3.py`: 17 tests covering selectors, signatures, ABI loading, resolve_pool (mocked RPC), ReserveResolution.
- `tests/test_phase4_rotation.py`: 8 tests covering phase4_rotation_enabled, rotate_target, _days_since_last_touched, cold-floats-above-warm, empty returns None, last_touched recorded on success.
- `tests/test_cron_registry_flip.py`: +2 tests (`test_depth_env_sets_prefer_full_registry`, `test_depth_env_does_not_override_existing_prefer_full_registry`).
- TESTS: **568 passed, 6 skipped** (was 537 → +31 net new).
- Phase 4 rotation formula fix: cold programs now float above warm programs by multiplying by `days_since_touched` instead of dividing. This matches the handover intent ("cold programs float").

### v5 pivot — NativeHarness substrate
- Recorded the 2026-06-18 directed audit at `SYSTEM_AUDIT_2026-06-18.md`. Eight structural defects upstream of the gates describe why v4.2.0 stayed at `submit_ready=0`. The gates, trust boundary, RSI, lab notebook, and skill lockdown remain authoritative; the discovery substrate pivots.
- Added `src/night_shift_security/native/__init__.py` (manifest schema + upsert + read) and a new CLI subcommand group `native status`, `native mark`. Manifest lives at `data/security_results/loop/native_harness_status.json`.
- Cron bootstrap (`hermes/scripts/nss-hipif-chain.sh`) now refuses to run the legacy chain when `NSS_HIPIF_PAUSE_FOR_NATIVE=1` (the default) and no target in the native-harness manifest has `status=ready`. Set `NSS_HIPIF_PAUSE_FOR_NATIVE=0` to revert to legacy v4.2 chain.
- Updated SPEC.md version to `5.0.0-draft` with new §0 "Why this version exists"; AUDIT.md records v4.2.0 closure + v5 Pivot section; hermes cron example YAML updated.
- Added `tests/test_native_harness.py` covering: empty state, upsert + ready counter, missing file fallback, garbage file fallback, default path, full round-trip persistence. 6 tests.
- First target = `uniswap_v4` ($15.5M Cantina pot) marked as `mapped` (ABI/IDL/source still required to reach `ready`).
- Tests: **444 passed, 5 skipped** (was 438 → +6 net new).

### 2026-06-19 — v5 fork_validation ABI/IDL bind + Morpho Blue harness start (audit C6 + Phase 3 row 1)
- `src/night_shift_security/validation/fork_validation.py`: `_has_native_bind` accepts Solidity `abi_signature_hash` (10 or 66 chars) OR Solana `selector_or_discriminator` + `source_ref.commit`. `_fork_candidate_set` filters severity-ranked top-N by `_has_native_bind` before the binder runs; falls back to severity-only catalogue anchors for research output.
- `hermes/scripts/nss-hipif-chain-run.py`: `bounty_depth()` now sets `NSS_PREFER_FULL_REGISTRY=1` in the environment. `src/night_shift_security/orchestration/bounty_loop.py`: `run_loop_iteration` reads the env var and passes `prefer_full_registry=True` to `pick_next_target` (C5 wired at the cron layer).
- `src/night_shift_security/native/morpho_blue.py`: first per-target Morpho Blue harness mirroring the uniswap_v4 template. Public surface: `selectors()`, `signatures()`, `load_abi()`, `resolve_market()`, `MarketParams`, `MarketResolution`. Canonical Morpho Blue core functions: `createMarket`, `supply`, `withdraw`, `borrow`, `repay`, `supplyCollateral`, `withdrawCollateral`, `liquidate`, `flashLoan`, `setAuthorization`, plus view functions (`owner`, `feeRecipient`, `position`, `market`, `idToMarketParams`, `isIrmEnabled`, `isLltvEnabled`, `isAuthorized`, `nonce`, `DOMAIN_SEPARATOR`).
- `sources/morpho/repo`: cloned at `55d2d99304fb3fb930c688462ae2ccabb1d533ad` (v1.0.0 tag).
- `tests/test_fork_validation_abi_idl.py`: 8 cases covering `_has_native_bind` (Solidity 4-byte/66-char hash, Anchor selector+commit, missing fields) and `_fork_candidate_set` (bound filtering, top-N, rejected).
- `tests/test_cron_registry_flip.py`: 3 cases covering env var propagation and `prefer_full_registry` passthrough.
- `tests/test_native_morpho_blue.py`: 21 cases covering selectors, keccak parity, signatures, market ID computation, ABI loading, resolve_market (mocked RPC), MarketParams/MarketResolution dataclasses.
- TESTS: **537 passed, 6 skipped** (was 506 / 6 → +31 net new).
- Native manifest: `morpho_blue` joined at `harness_built` alongside `uniswap_v4: ready`.

### 2026-06-19 — v5 first NativeHarness shipped (audit C1)
- Cloned `sources/uniswap_v4/repo` (v4-core @ commit `46c6834698c48bc4a463a86d8420f4eb1d7f3b75`); added `sources/uniswap_v4/repo/` to `.gitignore` next to the Wormhole/Kamino/AuditVault clones.
- Ran `semantic map --slug uniswap_v4 --repo sources/uniswap_v4/repo`: 46 files, 72 entrypoints, 18 value_flows, 1 authority_signal; promoted 66 concrete candidates into `data/security_results/knowledge/concrete_candidates.jsonl` (559 → 625). Coverage spans `PoolManager.{initialize,modifyLiquidity,swap,donate,settle,settleFor,take,mint,burn,transfer,unlock,…}` and all 10 `IHooks` before/after entrypoints plus `StateView.{getSlot0,getLiquidity,getFeeGrowthGlobals}`.
- Added `src/night_shift_security/crypto/__init__.py` — pure-Python Keccak-f1600 helper (no pycryptodome / pysha3 dependency). Cross-checked against canonical Ethereum vectors (`keccak256("") == c5d2460186f7…470`).
- Added `src/night_shift_security/native/uniswap_v4.py` — first per-target NativeHarness. Public surface: `selectors()` / `signatures()` / `load_abi()` / `resolve_pool()` / `PoolKey` / `PoolResolution`. Selectors are **canonical Ethereum Keccak-256** (`modifyLiquidity=0x5a6bcfda`, `swap=0x1998bab9`, `donate=0x234266d7`, `IHooks.beforeSwap=0x3fd9994c`, `StateView.getSlot0=0xc815641c`, etc.). Resolver computes the canonical `PoolId` via `keccak256(abi.encode(PoolKey))[:32]` (matches `PoolIdLibrary.toId`), then calls `StateView.getSlot0(PoolId)` against the deployed `0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227` using only `urllib` from stdlib (no web3.py). Default contract anchor: canonical Ethereum PoolManager `0x000000000004444c5dc75cB358380D2e3dE08A90` (Etherscan Verified, ~48KB bytecode on mainnet).
- Added `tests/test_native_uniswap_v4.py` (13 tests) and `tests/test_crypto_keccak.py` (6 tests) — all passing with no synthetic test doubles.
- Added `foundry/test/UniswapV4PoolManagerHarness.t.sol` — pure-import stub that hard-codes the canonical selectors for parity with the Python harness and runs a live Ethereum fork probe (`vm.createSelectFork(ETH_RPC_URL)`) confirming `PoolManager.code.length > 1000` (`~48KB`) and `StateView.code.length > 100` on Ethereum mainnet at "latest". Compiles under `forge build --force` (no v4-core remappings needed). `forge test -vv` with `ETH_RPC_URL` set → 2 passed, 0 failed.
- `native mark --slug uniswap_v4 --status harness_built --contract-address 0x000000000004444c5dc75cB358380D2e3dE08A90 --source-commit 46c6834698c48bc4a463a86d8420f4eb1d7f3b75`. `ready_count=0` (correct — `ready` waits for C2: a measured delta on a live fork).
## 2026-06-19 — v5 first measured delta shipped (audit C2)
- Added `src/night_shift_security/impact/measured_oracle.py` — `MeasureSpec` + `PreState`/`PostState` dataclasses, `compute_pre_state`, `compute_post_state`, `delta`, `build_evidence_envelope`, `build_finding_payload`, `write_evidence`, with `MEASURED_DELTA_THRESHOLD = 10**6` (1 USDC unit). Uses stdlib `urllib` only (no new packages). Reads canonical Keccak `PoolId` via `uniswap_v4._pool_id`, calls `eth_getBalance` and ERC-20 `balanceOf(address)(uint256)` via JSON-RPC. Negative-result honesty: a non-positive token diff returns `measured_impact=False` with a typed empty `evidence` envelope; never fabricates a positive impact.
- Added `tests/test_measured_oracle.py` (17 tests): threshold boundary, negative-result honesty, `pool_id` mismatch guard, slot0 control assertion (`donate` must move ERC-20 but not slot0), evidence round-trip, finding-payload gate shape, plus 1 RPC-gated live-RPC test (`pytest.importorskip` on `ETHEREUM_RPC_URL`).
- Added `foundry/test/UniV4Measure.t.sol` — real fork probe that calls `PoolManager.initialize(USDC/WETH, fee=999_999, tickSpacing=8192, sqrtPriceX96=2^96)` from a deterministic impersonated `0x...dEaD` EOA (`vm.startPrank`). Records the canonical PoolId, pre/post `sqrtPriceX96` and `tick`. Compiles under `forge build --force` (no v4-core remappings; uses `abi.encodeWithSignature` for ABI encoding).
- Added `scripts/_capture_measurement_json.py` — runs `forge test --match-path test/UniV4Measure.t.sol -vv`, parses the recorded PoolId / `SQRT_PRE` / `SQRT_POST` / `TICK_PRE` / `TICK_POST` values, and emits the canonical evidence file via `measured_oracle.write_evidence`.
- Recorded **first measured delta on a live fork**: `sqrtPriceX96: 0 -> 79228162514264337593543950336` (= 2**96, 1:1 price). Evidence file lives at `data/security_results/impact/uniswap_v4_measured_delta.json` with `schema_version=measured-oracle.v1`. Token-unit deltas are 0 (no ERC-20 movement); the slot0 init is the substrate-binding proof.
- `native mark --slug uniswap_v4 --status ready` -> `ready_count=1`. Cron precondition gate (`nss-hipif-chain.sh`'s embedded pause-check) now exits `0`; the 04:00 cron resume is automatic.
- No new packages installed; `pyproject.toml` untouched.
- Tests: **479 passed, 6 skipped** (was 463 -> +16 net new).

### 2026-06-18 — v5 picker precondition + label split (audit C3+C4+C5+C7)
- Added `src/night_shift_security/bounty/native_picker.py` — typed `PickRefused`/`EmptyManifest`/`NativeStatusIncomplete` exceptions; manifest-backed helpers `native_status_of`, `filter_native_ready`, `pick_native_ready_or_raise`, `has_measured_delta` (reads both `concrete_candidates.jsonl` rows and `impact/<slug>_measured_delta.json` envelopes), `list_pickable_slugs`, `bounty_priority_score`, `rank_pickable_slugs`. State-priority multiplier per handover: `ready=1.0x`, `harness_built`/`paused=2.0x`, `mapped=0.25x`, `missing`/none=`0.0x`. Stdlib-only.
- Patched `src/night_shift_security/orchestration/bounty_loop.py`:
  - `pick_next_target` (audit C3 + C5) now reads the native-harness manifest and refuses missing/`mapped` slugs with a typed exception; `prefer_full_registry=True` extends the curated pool with `scope_registry.json` entries up to the `--max-slugs` cap (default 64). Existing 28-curated test surface keeps silent `None` when no manifest is supplied so legacy callers stay green.
  - `_maybe_mark_saturated` (audit C4) honors `has_measured_delta(slug)` as an escape valve — slugs with a positive `measured_impact_oracle.v1` slot0 or token-unit delta never get marked saturated even if every finding is catalogue-analogue.
  - `_record_run_labels` (audit C7) exports four additive labels: `fork_reproduced_catalog_anchor`, `fork_reproduced_live_program`, `fork_reproduced_value_moving`, `fork_reproduced_novel`. The legacy `fork_reproduced` counter on the run record remains the sum so existing dashboards / alerts stay green.
- Updated `tests/test_bounty_loop.py` fixture for the two pre-existing `pick_next_target` tests so they seed a local manifest with `ready` entries; their original assertion contracts are preserved verbatim.
- Added tests: `tests/test_pick_next_target.py` (9), `tests/test_full_registry_walk.py` (5), `tests/test_saturation_measured_escape.py` (6), `tests/test_fork_repro_labels.py` (5) — **27 new tests, no live RPC required**.
- Validation / fortune gates, RSI, lab notebook, trust boundary, skill lockdown, and the synthetic substrate remain untouched per audit §"What does not need to change".
- Native manifest still `uniswap_v4: ready`, `ready_count=1`; the 04:00 cron remains auto-resumed.
- TESTS: **506 passed, 6 skipped** (was 479 / 6 → +27 net new).

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
