# Lab notebook — 2026-06-19 v5 phases 7–12 completion

## Summary

Implemented `SPEC_V5_COMPLETION.md` phases **7–11** in one session. Phase **12 (G5 hunt-to-submit)** remains open — `submit_ready=0` by design until a non-mocked finding passes gates.

## Phase 7 — Kamino skeleton

| Deliverable | Status |
|-------------|--------|
| `native/kamino.py` | Program IDs, top-10 discriminators, `load_idl()`, `resolve_market()` |
| `semantic map --slug kamino` | 153 candidates → `concrete_candidates.jsonl` (778→818 total after seeds) |
| Manifest | `kamino: harness_built` → promoted Phase 8 |

## Phase 8 — Solana measured oracle

| Deliverable | Status |
|-------------|--------|
| `impact/solana_measured_oracle.py` | Reserve field + SPL diff; `capture_cross_slot()` |
| `scripts/_capture_kamino_measurement.py` | Live capture via reserve tx observation |
| Evidence | `impact/kamino_measured_delta.json` — `measured_impact=true` |
| Manifest | `kamino: ready` |

## Phase 9 — Solana harness scale

| Slug | Module | Measured delta | Manifest |
|------|--------|----------------|----------|
| jito | `native/jito.py` (SPL stake pool `SPoo1…`) | `jito_measured_delta.json` | `ready` |
| raydium | `native/raydium.py` (CLMM `CAMMC…`) | `raydium_measured_delta.json` | `ready` |
| orca | `native/orca.py` (Whirlpool) | `orca_measured_delta.json` | `ready` |

## Phase 10 — Concrete sequences

- `hypothesis/concrete_sequences.py` — emits `InstructionSequence`/`CallSequence` → `AttackVector`
- Wired into `generate_target_vectors()` when `depth_pass` or `use_concrete_sequences`
- Pipeline passes `NSS_LOOP_DEPTH_SLUG` match as `depth_pass`

## Phase 11 — Discovery

- `NSS_PREFER_SOLANA=1` — 1.5× rotation score for Solana slugs
- `NSS_DISCOVERY_MISSING_PCT` — boost for `native_status=missing` (default 0.8)
- `IMMUNEFI_PROGRAMS` +5: drift, marginfi, sanctum, meteora, pump
- `nss-hipif-chain.sh` preserves pre-set `NSS_HIPIF_MODE` over `.env` (dryrun fix)

## Completion criteria (G1–G5)

| Criterion | Status |
|-----------|--------|
| G1 ≥8 ready, ≥4 Solana | **6 ready** (2 EVM + 4 Solana) — short of 8 |
| G2 measured delta per ready | **6/6** have `impact/*_measured_delta.json` |
| G3 ≥50 candidates per ready | kamino 153+; others 10 native seed (need semantic map expansion) |
| G4 discovery loop | Phase 4 on; Solana bias shipped |
| G5 first submit | **open** — requires hunt depth / human gate |

## Tests

**678 passed, 7 skipped** (+70 net from 608 baseline).

New files: `test_native_kamino.py` (17), `test_solana_measured_oracle.py` (12), `test_native_jito/raydium/orca.py` (10 each), `test_concrete_sequences.py` (6), `test_prefer_solana.py` (5).

## Blockers for full G1/G5

1. **G1 shortfall:** need morpho positive-delta OR pendle/compound harnesses (+2 EVM ready)
2. **G3 jito/raydium/orca:** clone repos + full semantic map (≥50 rows each)
3. **G5:** bounty hunt — Wormhole accounting / Kamino live probes past fee-only; no gate loosening