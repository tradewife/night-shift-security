# Night Shift Security

**Adversarial research engine for DeFi protocol vulnerability and economic attack surface analysis.**

Night Shift Security is the security track under the Night Shift research platform. It generates attack hypotheses at scale, validates them through statistical gates and live fork/validator replay, and runs an autonomous outer loop aimed at Immunefi- and Cantina-grade bounty submissions — with a hard human gate before any external post.

## Status (2026-06-14)

| Field | Value |
|-------|-------|
| **SPEC** | v3.3.0 |
| **Architecture** | v3.1 (`adversarial_research_architecture.md`) |
| **Tests** | **344 passed**, 3 skipped (live RPC/validator optional) |
| **Primary cron** | `nss-hipif-chain` daily 04:00 (Hermes agent + `hipif` skill) |
| **Platform intel** | 208 Immunefi + 52 Cantina live (`platform sync` / `platform diff`) |
| **Bounty outcome** | **0 `submit_ready`** — gates working; novel surface in progress |

**Shipped:** Platform intel + submittable export gates (v3.3.0); HIPIF bounty-depth chain; Operator Layer v3.0 (A–D); Wormhole live/triage forks; KLend CPI probes; Cantina harness (reserve/coinbase); deterministic RSI + Coordinator.

**Next focus:** KLend `live_executed` with measured delta; novel Wormhole exploit with economic impact (not triage surface alone).

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest                                    # 344 passed, 3 skipped

# Zero-cost pipeline (LLM off)
.venv/bin/python -m night_shift_security.cli.main run

# Hermes profile (outer loop)
./hermes/install-profile.sh && hermes --profile night-shift doctor

# Deterministic bounty-depth night chain (~60–150 min with RPC + validator)
set -a && source .env && set +a
export NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_FIXTURE=0
.venv/bin/python hermes/scripts/nss-hipif-chain-run.py --init
```

## What it does

- **Hypothesis generation** — seven attack templates, Darwinian evolution, bounded LLM expansion (`metadata.trusted=false`)
- **Validation** — Monte Carlo, CPCV/PBO, evidence grading (Levels 0–4), task verifier balance delta
- **EVM replay** — Foundry mainnet forks (Euler/Nomad catalogue + Wormhole core/token_bridge live targets)
- **Solana replay** — fixture CI, validator clone replay, KLend live harness with CPI probes
- **Autonomous loops** — bounty loop, HIPIF chain, RSI, Coordinator; stops on `submit_ready` + human gate
- **Export** — `bounty/research/` (internal) vs `bounty/submittable/` (human-gated); PoC bundler + IVSS; lab notebook provenance

## Day Shift vs Night Shift

| Shift | Where | Role |
|-------|-------|------|
| **Day Shift** | Cursor + `hermes/DAY_SOUL.md` | Planned arcs: infra, tests, triage, intel → backlog |
| **Night Shift** | Hermes `night-shift` + cron | HIPIF chain: scan → Wormhole → bridge → KLend live → hunt → RSI → refine → gate |

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
| `AUDIT.md` | System audit — strengths, gaps, priorities (2026-06-14) |
| `CHANGELOG.md` | Release notes aligned with SPEC versions |
| `BOUNTY_RUN.md` | Zero-budget command cookbook |
| `METHODOLOGY.md` | Research loop and evidence standards |
| `adversarial_research_architecture.md` | Layered architecture baseline |
| `SUSTAINABILITY.md` | Bounty payout allocation model |
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