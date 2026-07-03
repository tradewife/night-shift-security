# Session plan — current

**Status: active** (2026-07-04, Lombard Finance cross-layer hard-first phase)

**Arc:** Lombard Finance Immunefi — Primary Target: Solana `lombard_token_pool` + cross-layer EVM/Solana message and asset flows.

**Workspace:** `data/security_results/investigations/2026-07-03-lombard-cross-layer/` (local-only)
**Repos:** `sources/lombard-finance/repo` and `sources/lombard-finance/evm-smart-contracts`
**Prior:** Solana `2026-06-26-v6-24-lombard-solana-bridge` honest-zero, EVM `2026-07-03-lombard-evm-gmp-core` honest-zero.

**This session so far:** codegraph-x-ray → property fan-in → 5 strategies → SBF/IDL build → native structural probes → EVM GMP and fork ACL replay → Crucible scaffold repair → per-file anchor test adjudication.

**Results so far:**
- CodeGraph indexed **390 files / 3,999 nodes / 8,715 edges**.
- Built/captured **11 SBF artifacts + 11 IDLs** in the investigation build artifacts folder.
- Native Lombard focused suite: **19 passed, 1 skipped**.
- EVM GMP probes: **16 passed**.
- EVM mainnet fork ACL probes: **8 passed**.
- Token-pool Rust decode unit: **1 passed**.
- Cargo unit tests: **passing** for `lombard_token_pool`, `consortium`, `bridge`, `mailbox`, `bascule_gmp`, `asset_router`, `lbtc` under `--no-default-features --features localnet`.
- **Aggregate `anchor test`: 149 / 165 passing**, 16 failing — all `before all` hooks conflicting on shared PDAs (`12y3Uh6srjcnfjr7iFTn8vEVhrqf3vs7aAGiBfR61SUU`, `8SFqwq…`, `BqScmy…`) within a single validator session.
- **Per-file `anchor-test-each.sh` run: ALL 11 FILES GREEN** (310 passing: 85 asset_router, 12 bascule.bankrun, 1 bascule, 21 bascule_gmp, 71 bridge, 7 ccip, 17 consortium, 23 consortium_utilities, 54 mailbox, 18 ratio_oracle, 1 registry). Adjudicates the 16 aggregate failures as test-infra cross-pollution, **not protocol bugs**.
- **Crucible dry-run PASS** (`InvalidAccountData` blocker resolved by copying mainnet-feature `lombard_token_pool.so` 686 KB into the scaffold's `target/deploy/`). Log saved under `evidence/crucible-lombard-token-pool-dry-run.log`.
- **Cross-layer divergence / negative-path probes:** new `test/nss/PropEvmCrossLayerDivergence.ts` (5/5) covers PROP-XR-EVM-006 (Mailbox handler-revert try/catch semantics — payload remains re-attemptable) and PROP-XR-EVM-007 (AssetRouter.changeBascule(0) admin disable-mint path). New N1/N2/N3 inside `tests/ccip.ts` cover (a) mailbox.deliver does not gate destination_caller (only token_pool does), (b) re-init at same nonce PDA reverts (init dedupe), (c) sourcePoolAddress without remoteChainConfig reverts on executeOfframp. **ccip.ts full file: 10/10 passing.**

**Key refinement:** `release_or_mint_tokens` calls `mailbox.handle_message` with handler = token-pool `state` PDA, not `pool_signer`. `pool_signer` is only a remaining-account signer used by `bridge.gmp_receive`. Remote `destination_caller` must equal the destination token-pool `state` PDA bytes.

**EVM/Solana divergence (v6.51 round-2 insight):** EVM `Mailbox._deliverAndHandle` wraps `handlePayload(...)` in a try/catch and `handledPayload[payloadHash] = true` is only set on success — so an upstream handler revert leaves the message re-attemptable. Solana `mailbox.handle_message` writes `message_info.status = Handled` *before* `invoke_signed` to the recipient program; if the recipient CPI reverts, Anchor transaction atomicity rewinds the `Handled` write. Both layers still gate duplicate delivery via PDA `init` dedupe keyed by `[MESSAGE_SEED, payload_hash]` — so a mechanical replay cannot pass init in either chain. The two paths differ in *retry semantics*: Solana requires a brand-new tx after the failed `gmp_receive`, EVM allows a fresh `deliverAndHandle` tx to re-enter the still-`Delivered` message.

**Next actions:** validator/bankrun proof for rollback of `mailbox` `Handled`-before-CPI on `bridge.gmp_receive` failure (use the isolated-mailbox.ts + bankrun pattern observed; the 54 mailbox.ts per-file passing includes `gmpReceive rejects when invalid recipient account`); decimal mismatch rollback proof; direct consortium index-bounds replay (likely DoS-only). Hardhat EVM probe for `Mailbox._deliverAndHandle` with revert-throwing handler to confirm EVM re-attempt capability. Crucible stateful sequence fuzzing action set on `release_or_mint_tokens`.

**Night Shift handoff:** prioritize Solana token_pool validator/bankrun durability probe before expanding to lower-value EVM surfaces. `submit_ready` unchanged at 1 (OnRe H1 v6.13); no Lombard cross-layer issue is submission-ready yet.

---

**Status: completed** (2026-07-03, Lombard Finance EVM GMP core — thorough investigation with 24 passing tests, Slither, mainnet fork ACL)

**Arc:** Lombard Finance Immunefi — Primary Target: `GMPBasculeV1` + `Consortium` + `Mailbox` + `AssetRouter` + `BridgeV2`

**Workspace:** `data/security_results/investigations/2026-07-03-lombard-evm-gmp-core/` (local-only)  
**Repo:** `sources/lombard-finance/evm-smart-contracts` (cloned)  
**Prior:** Solana `2026-06-26-v6-24-lombard-solana-bridge` honest-zero

**This session:** codegraph-x-ray → 16 Hardhat NSS probes + 8 mainnet fork ACL probes + Slither analysis (855 results)

**Results:**
- **24/24 Hardhat tests passing** across 3 property suites (PropEvmGmpCore, PropEvmDeepProbes, PropEvmForkAcl)
- **Mainnet fork ACL confirmed** — AssetRouter has MINT_VALIDATOR on GMPBasculeV1, all cross-contract wiring correct
- **Slither** — 855 results, no critical Lombard-specific issues
- **Design observations** (8 noted, none submission-quality)
- **Classification:** engine-level honest-zero. `submit_ready`: false

**Key findings:**
- BasculeV3 `setTrustedSigner` lacks zero-address check (unlike V1/V2). Admin could set to zero, bypassing all proof validation.
- Mailbox `handledPayload` set but never read (redundant)
- All core EVM GMP contracts thoroughly investigated

**Night Shift handoff:** Do not reopen Lombard EVM without new scope additions. Solana `lombard_token_pool` deepen could be productive if cross-layer flows are in scope.

---

**Prior arc (checkpointed):** Aztec Network, Cantina `80e74370-10d8-4e52-8e4b-7294deb7c9ee`

**Primary Target Subsystem:** Governance–Reward–Slashing–Inbox/Escape economic and trust nexus.

**This session (Aztec nexus fresh context):** Ran codegraph/static intelligence, Slither triage, 4 focused fresh-context worker reviews, property fan-in, strategy fan-out, targeted Foundry, and full Aztec L1 Foundry.

**Validation:**
- Targeted Foundry: **865 passed, 0 failed, 3 skipped** (integrated with full Aztec L1 suite)
- Slither: 92 detector entries, no confirmed submission-quality issue

**Interesting behaviors, not yet submission-ready:**
- `GSE.voteWithBonus` keys bonus eligibility to proposal `pendingThrough`, not proposal creation time.
- `EscapeHatch.validateProofSubmission` validates proven tip and archive match, not proof submitter identity.

**Investigation:** `data/security_results/investigations/2026-07-03-aztec-cantina-nexus/` (local-only per AGENTS.md)

**Lab notebook:** `data/security_results/lab_notebook/2026-07-03-aztec-cantina-nexus.md` (local-only per AGENTS.md)

**Exit:** `submit_ready` unchanged at 1 (OnRe H1 v6.13). Next Aztec work should write executable GSE pending-through boundary tests and EscapeHatch free-ride characterization if the operator continues this arc.

**Prior closed arc (Agglayer, 2026-07-03):** 19 attempts, 0 findings. PROP-AGG-003 overflow passes via U512 intermediates. PROP-AGG-001 encoding confirmed matching. PROP-AGG-004 migration starts from empty state on both sides. H-FEE-001 closed. Remaining only SP1 bootstrap proof for non-empty exit tree, requiring SP1 toolchain.

**Night Shift handoff:** Cron may continue to rotate. Lombard EVM closed engine-level honest-zero. Do not reopen without new scope additions.