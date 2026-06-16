# Night Shift Security

**Adversarial research engine for DeFi protocol vulnerability and economic attack surface analysis.**

Night Shift Security is the security track under the Night Shift research platform. It generates attack hypotheses at scale, validates them through statistical gates and live fork/validator replay, and runs an autonomous outer loop aimed at Immunefi- and Cantina-grade bounty submissions — with a hard human gate before any external post.

## Status (2026-06-16)

| Field | Value |
|-------|-------|
| **SPEC** | v4.1.0 |
| **Architecture** | v4.1.0 (`adversarial_research_architecture.md`) |
| **Tests** | **385 passed**, 5 skipped, 3 deselected in sandbox-safe run; focused self-interrogation/pipeline tests: **60 passed** |
| **Primary cron** | `nightsoul` profile: `nss-hipif-chain` daily 04:00; no-agent deterministic full v4 runner through HIPIF gate |
| **Platform intel** | 208 Immunefi + 52 Cantina live (`platform sync` / `platform diff`) |
| **Bounty outcome** | **0 `submit_ready`** — gates stricter; v4 candidates now need measured impact |

**Shipped:** v4 semantic recon, concrete candidate store, target-pinned proposals, Opengrep/SARIF ingestion, fail-closed PoC generation, KLend v2 artifacts, Wormhole economic gates, Failure Trace RSI, and v4.1 self-interrogation conviction reports; plus v3.3 platform intel/export gates and HIPIF bounty-depth chain.

**Next focus:** Bind top v4 Wormhole/KLend candidates to real deployed state and replace fail-closed generated PoCs with measured value-moving repros.

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
- **EVM replay** — Foundry mainnet forks (Euler/Nomad catalogue + Wormhole core/token_bridge live targets)
- **Solana replay** — fixture CI, validator clone replay, KLend live harness with CPI probes
- **Autonomous loops** — bounty loop, HIPIF chain, RSI, Coordinator; stops on `submit_ready` + human gate
- **Export** — `bounty/research/` (internal) vs `bounty/submittable/` (human-gated); PoC bundler + IVSS; lab notebook provenance
- **Semantic discovery** — `semantic map`, concrete v4 candidates, SARIF ingestion, failure-trace RSI, fail-closed generated verifiers

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + `hermes/DAY_SOUL.md` | Planned arcs: infra, tests, triage, intel → backlog |
| **Night Shift** | Hermes `nightsoul` cron + repo-managed `night-shift` assets | HIPIF chain: scan → semantic recon → concrete candidates → Wormhole → bridge → KLend live → hunt → failure-trace RSI → refine → gate |

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

See `AGENTS.md` (coding agents), `hermes/SOUL.md` (Hermes operator), `AUDIT.md` (system audit).

## Repository layout

| Path | Purpose |
|------|---------|
| `SPEC.md` | Technical specification, version history, CLI reference |
| `AUDIT.md` | Current system audit — strengths, gaps, priorities |
| `CHANGELOG.md` | Release notes aligned with SPEC versions |
| `BOUNTY_RUN.md` | Operator command cookbook |
| `adversarial_research_architecture.md` | Current layered architecture baseline |
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
