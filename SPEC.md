# Night Shift Security — Technical Specification

**Version:** 1.1  
**Date:** 2026-06-07  
**Author:** Grok (for Kate / tradewife)  
**Purpose:** Clone the Night Shift research engine architecture for parallel security and vulnerability research. This becomes a distinct but related track focused on surfacing protocol risks before they become exploits (inspired by the recent Zcash exploit news).

---

## Agent Handover (Read This First)

**Workspace:** Open this repo — `/home/kt/projects/rtp/night-shift-security`  
**Remote:** https://github.com/tradewife/night-shift-security  
**Scope:** Security track only. Do **not** edit Night Shift Tokenomics (`/home/kt/projects/rtp/night-shift-tokenomics`) — a separate agent owns that repo per its own spec.

### Current status (2026-06-07)

Phase 5c-Solana Slice 1 shipped on `main`. **81 tests passing.** Foundry 1.7.1 installed.

| Commit | What shipped |
|--------|--------------|
| `ce813e6` | MVP pipeline, governance template, gates, exploit catalog |
| `01f84cd` | 4 attack templates, Darwinian evolution, 11-exploit catalog |
| `5768081` | Monte Carlo stress, Foundry simulator scaffold (mock fallback) |
| `d83cc3a` | CPCV/PBO overfitting detection, mainnet fork validation targets |
| `6de653a` | Public findings export, HTTP API, tokenomics bridge **producer** |
| `f7d4699` | Phase 3: 3 new templates, 16-exploit catalog, disclosure, API polish |
| *(previous)* | Phase 4: Foundry harness (7 tests), catalog seeds, 16/16 rediscovery, monitoring + bounty pipeline |
| `5c6b8e9` | Phase 4 completion + gated rediscovery fixes |
| *(previous)* | Phase 5a: Deduper (Stage 5d) — conservative exact-match deduplication |
| `d062184` | **Phase 5b: Fork scoring multiplier + strict `fork_reproduced` semantics** |
| *(current)* | **Phase 5c-Solana Slice 1: Solana validation lane + `solana_reproduced` + 19-exploit catalog** |

### Package layout (`src/night_shift_security/`)

```
core/          pipeline.py, evaluation, evolution, gates, scoring, results
domain/
  attack_templates/   governance_capture, treasury_drain, flash_loan_oracle, reentrancy,
                      composability_risk, upgradeability_risk, access_control_escalation
  simulators/         mock_simulator (default), foundry_simulator (forge + mock fallback)
data/          schemas.py, exploit_catalog.py (19 ground-truth exploits), fork_targets.py, solana_targets.py
validation/    historical_replay, monte_carlo_stress, foundry_validation, cpcv_stress, fork_validation, solana_validation
export/        dataset.py, loader.py, disclosure.py — severity-ranked JSON/JSONL + embargo redaction
api/           server.py, query.py — stdlib HTTP findings API with pagination/filtering
bridge/        tokenomics.py — exports tokenomics_risk_feed.json (consumer lives in tokenomics repo)
monitoring/    hooks.py — webhook + JSONL alert sinks for high-severity findings
bounty/        pipeline.py — Immunefi-style submission pack export
validation/    + catalog_seeds.py, rpc.py — ground-truth seeds + live RPC detection
cli/           main.py — run | serve | export | disclose | bounty | monitor
foundry/       VulnerableProtocol.sol (7 templates), AttackSimulation.t.sol, ForkHistorical.t.sol, setup.sh
```

### Pipeline as implemented

```
Stage 0: Ground-truth sanity (catalog exploits pass gates with known params)
Stage 1: Attack vector grid search (140 vectors across 7 templates)
Stage 3: Darwinian evolution (+12 candidates)
Stage 4b: CPCV + PBO overfitting detection (top 5 per template)
Stage 5: Monte Carlo stress (top 10)
Stage 5b: Foundry validation (top 5; mock if forge unavailable)
Stage 5c: Mainnet fork validation (catalog EVM anchors + top_n)
Stage 5c′: Fork scoring bonus + re-rank passed candidates
Stage 5c-S: Solana validation (catalog Solana anchors + top_n; fixture strict path)
Stage 5c-S′: Solana scoring bonus (1.10×; max with EVM, no stacking) + re-rank
Stage 2b: Rediscovery test vs 19-exploit catalog (uses pre-bonus vectors)
Stage 5d: Dedupe
Stage 6: Monitoring hooks (webhook / alerts.jsonl)
Stage 6b: Bug-bounty submission pack export
→ findings.json + report.md + public dataset + tokenomics bridge + bounty pack
```

**Last run metrics (Foundry 1.7.1):** 81 tests passing.  
Fork scoring active (1.20× on `fork_reproduced`). Solana scoring active (1.10× on `solana_reproduced`; no multiplier stacking).  
`fork_reproduced` is strict EVM archive replay. `solana_reproduced` is strict fixture or validator replay with impact evidence.  
Live fork/Solana tests skipped without archive RPC / `SOLANA_USE_VALIDATOR`.

### Run locally

```bash
cd /home/kt/projects/rtp/night-shift-security
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m night_shift_security.cli.main          # full pipeline
.venv/bin/python -m night_shift_security.cli.main serve  # API on :8787
.venv/bin/python -m pytest                                           # 81 tests
cd solana && ./setup.sh                                              # Solana fixture harness
export PATH="$HOME/.foundry/bin:$PATH" && cd foundry && ./setup.sh && forge test
.venv/bin/python -m night_shift_security.cli.main disclose --input data/security_results/2026-XX-XX/findings.json --report
.venv/bin/python -m night_shift_security.cli.main bounty --input data/security_results/2026-XX-XX/findings.json
.venv/bin/python -m night_shift_security.cli.main monitor --input data/security_results/2026-XX-XX/findings.json
.venv/bin/python -m night_shift_security.cli.main dedupe --input data/security_results/2026-XX-XX/findings.json --re-export
```

**Optional env for live fork tests:**
```bash
export ETHEREUM_RPC_URL=<your-archive-rpc>
cd foundry && ./setup.sh && forge test
```

**Optional env for Solana grant-demo validator path:**
```bash
export SOLANA_MAINNET_RPC_URL=<your-mainnet-rpc>
export SOLANA_USE_VALIDATOR=1
cd solana && ./setup.sh
.venv/bin/python -m pytest tests/test_solana_live.py -v
```

### Outputs

Per-run (dated): `data/security_results/YYYY-MM-DD/findings.json`, `report.md`  
Always-updated API artifacts:
- `data/security_results/dataset/latest.json` — full severity-ranked feed
- `data/security_results/dataset/feed.json` — minimal API shape
- `data/security_results/dataset/findings.jsonl`
- `data/security_results/bridge/tokenomics_risk_feed.json` — cross-track bridge

**API endpoints** (`night-shift-security serve`):
`/api/v1/health` · `/api/v1/feed?page=1&limit=50&severity=critical` · `/api/v1/findings?template_id=composability_risk` · `/api/v1/findings/{id}` · `/api/v1/bridge/tokenomics`

Optional auth: set `NIGHT_SHIFT_API_KEY`; pass via `X-API-Key` header or `?api_key=`.

### RTP source (extraction reference)

Original Night Shift engine: `/home/kt/projects/tabs/resilient-token-protocol`  
Key file: `research/orchestration/night_shift.py` — patterns were adapted, not copied wholesale (no trading sim, OHLCV, perps, etc.).

### Cross-track bridge (producer side only)

Security **exports** `tokenomics_risk_feed.json` with `risk_patterns[]` (template triggers + penalties).  
Tokenomics has an optional consumer (`security_bridge` config) managed by another agent — do not modify tokenomics from this repo. If the bridge schema changes, coordinate with the tokenomics agent.

### Phase 5 plans/next steps (updated 2026-06-07)

**Completed**
- Phase 5a: Deduper (Stage 5d) — conservative exact canonical matching, 7 drops on catalog↔grid duplicates.
- Phase 5b: Fork scoring multiplier + strict `fork_reproduced` semantics (commit `d062184`).
  - Fork validation is a **confidence multiplier only** (default 1.20×), never a gate.
  - `fork_reproduced` requires live archive EVM replay at the exact historical block + `method == "evm_fork"`.
  - `fork_confirmed` remains for backward compatibility (includes catalog fallback and Solana catalog replay).
  - New fields: `fork_reproduced`, `fork_block_number`, `fork_evidence`, `severity_score_base`.
  - Public dataset and report now surface fork evidence for reproduced historical exploits.
  - 67 tests passing.

**Phase 5c-Solana Slice 1 (shipped)**
- Solana catalog anchors: Mango, Solend whale, Cashio, Crema (+ 15 EVM/other exploits = 19 total).
- Stage 5c-S / 5c-S′: `solana_confirmed` (broad) and `solana_reproduced` (strict fixture or validator).
- Fields: `solana_reproduced`, `solana_slot`, `solana_evidence`, `severity_score_base`; public summary adds `solana_reproduced_count`, `solana_reproduced_exploit_ids`.
- Harness: `solana/` fixture runner (CI default); `solana-test-validator --clone` documented for grant-demo mode.
- 81 tests passing.

**Ecosystem alignment:** Night Shift Security produces reproducible, scored adversarial findings that complement static rulesets (e.g. [Solana Security Standard — JelleoLabs](https://github.com/JelleoLabs/solana-security-standard)) and institutional evaluation programs (e.g. Solana Foundation STRIDE). Our lane adds *dynamic rediscovery + severity-ranked public findings*, not a replacement for lint rules or STRIDE checklists.

**Next (Slice 2):**
1. Expand Solana catalog toward 8–10 incidents; wire validator clone replay for Mango + Solend.
2. Solana-specific template metadata (upgrade authority, PDA treasury) where mock fixtures gap.
3. Grant narrative: dual-track reproducibility counts (EVM + Solana).

Tighter deduplication keying and webhook adapters remain deferred.

### Known limitations / gotchas

- **Foundry not required** — pipeline falls back to `mock_simulator` when `forge` is absent.
- **Fork validation** returns 0 confirmed without a real Ethereum archive RPC URL.
- **CPCV/PBO** is aggressive; many candidates get `DANGER` verdicts — intentional overfitting guard.
- **`data/security_results/`** is gitignored; re-export with `night-shift-security export --input <findings.json>`.
- **Governance fields** on `ContractState` have defaults so non-governance exploit fixtures construct cleanly.
- `fork_reproduced` is EVM-only. `solana_reproduced` is Solana-only (fixture strict path in Slice 1).

### RTP source (extraction reference)

Original Night Shift engine: `/home/kt/projects/tabs/resilient-token-protocol`  
Key file: `research/orchestration/night_shift.py` — patterns were adapted, not copied wholesale.
