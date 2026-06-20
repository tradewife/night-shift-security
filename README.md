# Night Shift Security

**Adversarial research engine for DeFi protocol vulnerability and economic attack surface analysis.**

Night Shift Security is the security track under the Night Shift research platform. It generates attack hypotheses at scale, validates them through statistical gates and live fork/validator replay, and runs an autonomous outer loop aimed at Immunefi- and Cantina-grade bounty submissions — with a hard human gate before any external post.

## Status (2026-06-20)

| Field | Value |
|-------|-------|
| **SPEC** | v6.2.0-proposal-session6 (post-v6.1 empirical-calibration pivot) |
| **Architecture** | v4.2.0 substrate (`adversarial_research_architecture.md`) + v6 target rotation + less-audited-program onboarding |
| **Tests** | **783 passed, 11 skipped** in full local run. Harness-specific: `tests/test_native_marginfi.py` 26 passed + 1 skipped. |
| **NativeHarness readiness** | `ready_count=8` (uniswap_v4, morpho_blue, aave_v3, kamino, jito, raydium, orca, reserve). `scaffolded_count=2`: `ethena_native` (v6.1 empirical-calibration honest-zero) + `marginfi_v2` (v6.2 novel-vec probe honest-zero). |
| **Empirical-FNR dataset** | 2 datapoints: Ethena (EVM, uint64 truncation in `verifyNonce`) + Marginfi (Solana, sentinel-default-discovery gap). Both honest-zero under identical gate discipline. Audit-saturation framing is bounded (not asserted). |
| **Primary cron** | `nightsoul` profile: `nss-hipif-chain` daily 04:00; no-agent deterministic full v6 runner through HIPIF gate |
| **Optional agent cron** | `nightsoul` 07:00 agent turn (xAI-OAuth `grok-4.3`) — writes untrusted `auditvault-*.json` proposal via the `auditvault-research` skill |
| **Platform intel** | 208 Immunefi + 52 Cantina live plus Solodit corpus sync (`platform sync` / `platform solodit-sync`) plus Auditware AuditVault corpus (`platform auditvault-sync` — 2383 findings, 826 protocol slug×id pairs); v6 rotation adds less-audited-program priority |
| **Bounty outcome** | **0 `submit_ready`** — gates correct; v6.0.0-draft + v6.1 + v6.2 each produced honest-zero by design. Audit-saturation framing is now empirically grounded by the 2-datapoint `ethena_native` + `marginfi_v2` dataset. |

**Shipped (v6 prefix):** target-rotation engine (Phase 4 + cron unpause), less-audited-program priority ordering, Mandatory Falsification Protocol (SPEC §3.2), `native/ethena.py` + `native/reserve.py` + `native/marginfi.py` + `ReserveFalsificationProbe1.t.sol` + `EthenaMeasure.t.sol` + `EthenaCalibrationProbe.t.sol` artifacts, `tests/test_native_ethena.py` + `tests/test_native_reserve.py` + `tests/test_native_marginfi.py`. Three v6-tier calibration/falsification probes verified end-to-end on real mainnet forks. Two empirical-FNR datapoints recorded (Ethena + Marginfi).

**v6 strategy recap:** the audit-saturation ceiling on the 8 well-defended DeFi protocols (Kamino, UniV4, Aave V3, Raydium, Wormhole, Orca, Jito, Morpho) motivated v6. Recommended v6 targets in priority order: Reserve Protocol ($10M, Cantina, ready, measured-delta recorded), Coinbase ($5M), Ethena ($3M, scaffolded, calibration honest-zero), Marginfi v2 ($250K, scaffolded, novel-vec probe honest-zero), SSV Network ($250K), Pendle ($2M), DeXe Protocol ($500K).

**Next focus:** per `lab_notebook/2026-06-20-session-6-marginfi-onboarding.md`: populate canonical Marginfi v2 group + USDC bank PDA seeds (via SDK resolution or filtered `getProgramAccounts` or explorer lookup), then re-run probe and flip `marginfi_v2` from `scaffolded` to `ready`. Solana-first per SPEC §4.4 remains.

### Next-session parallel requirement (study, link only)

The next session is required to perform an independent deep-read of the reference below as a parallel thread alongside the existing v6 task graph. The link is provided as a single reference point; no prior decomposition from this codebase is to be assumed by the next agent. The next session should produce its own reading-derived proposals for deepening attack-surface discovery, distinct from any earlier conclusions in this repo.

- Reference: <https://blog.monad.xyz/blog/ultrafuzz>

See `SPEC.md` §0.4 for the spec-side statement of this requirement.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -k 'not api_serves_endpoints and not api_paginated_endpoint and not api_auth_rejects_without_key'

# Zero-cost pipeline (LLM off)
.venv/bin/python -m night_shift_security.cli.main run

# Hermes profiles (outer loop)
./hermes/install-profile.sh && ./hermes/install-nightsoul-overlay.sh
hermes --profile nightsoul doctor

# Deterministic bounty-depth night chain (~60–150+ min with RPC + validator)
set -a && source .env && set +a
export NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_FIXTURE=0
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init --phase full
```

## What it does

- **Hypothesis generation** — seven attack templates, Darwinian evolution, bounded LLM expansion (`metadata.trusted=false`)
- **Validation** — self-interrogation conviction reports, Monte Carlo, CPCV/PBO, evidence grading (Levels 0–4), task verifier balance delta
- **External corpus** — Cyfrin Solodit findings sync, Auditware AuditVault advisory corpus sync, pattern JSONL, and untrusted proposal enrichment (never satisfies submission gates)
- **EVM replay** — Foundry mainnet forks (Euler/Nomad catalogue + Wormhole core/token_bridge live targets)
- **Solana replay** — fixture CI, validator clone replay, KLend live harness with CPI probes
- **Autonomous loops** — bounty loop, HIPIF chain, RSI, Coordinator; stops on `submit_ready` + human gate
- **Export** — `bounty/research/` (internal) vs `bounty/submittable/` (human-gated); PoC bundler + IVSS; lab notebook provenance
- **Semantic discovery** — `semantic map`, concrete v4 candidates, SARIF ingestion, failure-trace RSI, fail-closed generated verifiers
- **Agent proposal lane** — optional authenticated `hermes chat` turn (`nightsoul`, `grok-4.3`, `auditvault-research` skill) writes a single untrusted `auditvault-*.json` proposal per run; never executes the chain

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + `hermes/DAY_SOUL.md` | Planned arcs: infra, tests, triage, intel → backlog |
| **Night Shift** | Hermes `nightsoul` cron + repo-managed `night-shift` assets | HIPIF chain: scan → Solodit corpus → semantic recon → concrete candidates → self-interrogation → Wormhole → bridge → KLend live → hunt → failure-trace RSI → refine → gate |

Session plans: `data/security_results/day_shift/current.md`. Lab notebook: `data/security_results/lab_notebook/`.

## Validation lanes

| Lane | Strict signal | CI default | Live / bounty mode |
|------|---------------|------------|-------------------|
| EVM | `fork_reproduced` | Mock / catalogue fallback | `ETHEREUM_RPC_URL` + Foundry fork tests |
| Solana | `solana_reproduced` | `solana_fixture` | `solana_validator` + KLend harness (`klend_require_live`) |

```bash
cd foundry && ./setup.sh && forge test
cd solana && ./setup.sh
```

### Solana catalogue anchors

| Exploit ID | Fixture CI | Validator clone |
|------------|------------|-----------------|
| `solend-whale-2022` | Yes | Yes |
| `cashio-2022` | Yes | Yes |
| `mango-markets-2022` | Yes | Yes |
| `kamino-klend` | Fixture only in CI | **Live harness** (novel surface) |

## Trust boundary

Hermes orchestrates CLI/MCP only. Python gates are authoritative:

- `validate_hypothesis()` on all LLM proposals
- Evidence grading + CPCV + task verifier + credible harness gate
- `submission_alert.json` (schema v2) written only on `submit_ready` — no autonomous external submission; skill `operator-submit` for Kate gate

See `AGENTS.md` (coding agents), `hermes/SOUL.md` (Hermes operator), `SPEC.md` §3 (system audit + gaps), `CHANGELOG.md` (release log). The v4.2-era `AUDIT.md`, `BOUNTY_RUN.md`, `SPEC_V5_COMPLETION.md`, and `SYSTEM_AUDIT_2026-06-18.md` were removed on 2026-06-20; their content has been folded into `SPEC.md` (`§3.1 Strengths`, `§3.2 Current Gaps`, `§14 Version History`) and `CHANGELOG.md` (per-version entries).

## Repository layout

| Path | Purpose |
|------|---------|
| `SPEC.md` | Technical specification, version history, CLI reference, current gaps |
| `CHANGELOG.md` | Release notes aligned with SPEC versions |
| `adversarial_research_architecture.md` | v4.2.0 layered architecture baseline (preserved) |
| `AGENTS.md` | Agent onboarding and workflow |
| `src/night_shift_security/` | Pipeline, validation, orchestration, export |
| `hermes/` | SOUL, skills, cron scripts, HIPIF chain |
| `foundry/` | EVM harness |
| `solana/` | Solana fixture + KLend validator harness |
| `data/security_results/` | Run artifacts, loop state, lab notebook |

## Related projects

- **Resilient Token Protocol** — https://github.com/tradewife/resilient-token-protocol
- **Night Shift Tokenomics** — https://github.com/tradewife/night-shift-tokenomics
- Website: https://www.resilientprotocol.xyz

## Contact

Kate / tradewife — X: [@trade_wife](https://x.com/trade_wife) — GitHub: [tradewife](https://github.com/tradewife)
