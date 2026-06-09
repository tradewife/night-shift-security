# Night Shift Security

**Parallel research engine for protocol vulnerability and economic attack surface analysis.**

Night Shift Security is the second track under the Night Shift research platform. It applies massive-scale, rigorously validated simulation to discover and stress-test security vulnerabilities and economic attack vectors in DeFi protocols and token designs.

## What it does

- Explores adversarial hypothesis spaces (governance capture, treasury drains, flash-loan oracle manipulation, access control escalation, etc.)
- Runs Darwinian evolution, Monte Carlo stress, CPCV/PBO overfitting detection, and multi-layer validation
- Validates historical exploits on **EVM mainnet forks** (Foundry) and **Solana fixture/validator replay**
- Scores findings by severity, reproducibility, and economic impact — with confidence multipliers for reproduced exploits
- Produces severity-ranked public datasets, monitoring alerts, and bug-bounty submission packs

## Status

**v2.0.2 shipped.** Immunefi-ready path, Kamino live target, shoestring packs, reality-check fields, novel vector catalog, campaign tracking, and LLM eval harness. Solana validator replay: Solend, Cashio, Mango (Slice 3).

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m night_shift_security.cli.main run              # zero-cost default (LLM off)
.venv/bin/python -m night_shift_security.cli.main --config src/night_shift_security/config/shoestring.json run  # zero-RPC bounty pack
.venv/bin/python -m pytest                                         # 179 tests (4 live skipped)
.venv/bin/python -m night_shift_security.cli.main eval             # LLM quality eval (zero-cost mock)
```

See `SPEC.md` for architecture and `BOUNTY_RUN.md` for zero-budget bounty workflows.

## Validation lanes

| Lane | Strict signal | Default CI | Grant-demo mode |
|------|---------------|------------|-----------------|
| EVM | `fork_reproduced` | Mock / catalog fallback | `ETHEREUM_RPC_URL` + Foundry fork tests |
| Solana | `solana_reproduced` | `solana_fixture` via `run_fixture_test.py` | `solana_validator` via `run_validator_replay.py` |

```bash
cd foundry && ./setup.sh && forge test
cd solana && ./setup.sh
```

### Current Solana coverage

| Catalog entry | Strict CI path | Validator clone replay |
|---------------|------------------|------------------------|
| `solend-whale-2022` | `solana_fixture` | **Yes** (slot ~139,896,000) |
| `cashio-2022` | `solana_fixture` | **Yes** (slot ~128,587,000) |
| `mango-markets-2022` | `solana_fixture` | **Yes** (Slice 3) |
| `crema-finance-2022` | `solana_fixture` | Fixture only |

Grant-demo validator run:

```bash
export SOLANA_MAINNET_RPC_URL=<your-mainnet-rpc>
export SOLANA_USE_VALIDATOR=1
SOLANA_EXPLOIT_ID=solend-whale-2022 ./solana/run_validator_test.sh
```

See `solana/README.md` for full harness documentation.

## Ecosystem alignment

Night Shift Security complements — rather than replaces — static analysis and institutional security programs:

- **[Solana Security Standard](https://github.com/JelleoLabs/solana-security-standard)** (JelleoLabs) — rules derived from real incidents; we add dynamic rediscovery and scored reproduction evidence.
- **Solana Foundation STRIDE** — structured threat evaluation; we export reproducible adversarial findings ranked by severity for public-good datasets.

Goal: credible dual-track depth (strong EVM foundation + deliberate Solana expansion) with measurable `fork_reproduced` and `solana_reproduced` counts.

## Repository layout

- `SPEC.md` — technical specification and pipeline reference
- `BOUNTY_RUN.md` — zero-budget Immunefi / grant-demo command guide
- `src/night_shift_security/` — pipeline, templates, validation, export, API
- `foundry/` — EVM harness (Foundry)
- `solana/` — Solana fixture harness (validator path documented for Slice 2)

## Related projects

- **Resilient Token Protocol (RTP)** — https://github.com/tradewife/resilient-token-protocol
- **Night Shift Tokenomics** (parallel track) — https://github.com/tradewife/night-shift-tokenomics
- Website: https://www.resilientprotocol.xyz

## Contact

Kate / tradewife · X: [@trade_wife](https://x.com/trade_wife) · GitHub: [tradewife](https://github.com/tradewife)

---

*Built with the "STFU and Build" ethos. Brutal validation over hype.*