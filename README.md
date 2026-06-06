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

**Phase 5c-Solana Slice 1 shipped.** 81 tests passing. Pipeline covers 19 historical exploits (4 Solana-native anchors).

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m night_shift_security.cli.main   # full pipeline
.venv/bin/python -m pytest                        # 81 tests
```

See `SPEC.md` for full architecture, pipeline stages, and agent handover.

## Validation lanes

| Lane | Strict signal | Default CI | Grant-demo mode |
|------|---------------|------------|-----------------|
| EVM | `fork_reproduced` | Mock / catalog fallback | `ETHEREUM_RPC_URL` + Foundry fork tests |
| Solana | `solana_reproduced` | `solana/run_fixture_test.py` | `SOLANA_USE_VALIDATOR=1` + `solana-test-validator --clone` |

```bash
cd foundry && ./setup.sh && forge test
cd solana && ./setup.sh
```

## Ecosystem alignment

Night Shift Security complements — rather than replaces — static analysis and institutional security programs:

- **[Solana Security Standard](https://github.com/JelleoLabs/solana-security-standard)** (JelleoLabs) — rules derived from real incidents; we add dynamic rediscovery and scored reproduction evidence.
- **Solana Foundation STRIDE** — structured threat evaluation; we export reproducible adversarial findings ranked by severity for public-good datasets.

Goal: credible dual-track depth (strong EVM foundation + deliberate Solana expansion) with measurable `fork_reproduced` and `solana_reproduced` counts.

## Repository layout

- `SPEC.md` — technical specification and pipeline reference
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