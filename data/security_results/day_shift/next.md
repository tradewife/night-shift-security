# Next session queue

**Active arc: 1inch Smart Contracts Immunefi (2026-07-16). Sessions 1–2 complete — codegraph-x-ray + 4d-chess-sequential pass@k on EVM core. submit_ready=0.**

## Priority 0 — 1inch session 3

Per `docs/1inch.md` and `day_shift/current.md`:

1. Solana adversarial: minimal `safety_deposit` + `public_withdraw`/`public_cancel` on `cross_chain_escrow_src/dst` (complete PROP-1INCH-001).
2. `cross-chain-sdk` E2E integration tests (`evm-to-solana`, `solana-to-evm`) + timestamp skew variants (PROP-1INCH-006 Solana side).
3. Fusion dutch/PDA binding on `solana-fusion-protocol` (PROP-1INCH-009, 010).
4. Fresh-context pass@k k=3 on Solana PROP-001 before expanding to token-plugins/farming.

**Night Shift handoff:** Do not re-run codegraph-x-ray or baseline Escrow suite. Pick up from `data/security_results/investigations/2026-07-16-1inch-smart-contracts/property_fanin.md`.

## Priority 1 — Deferred (after 1inch session 3 or explicit pivot)

**MarginFi v2** (Solana lending) per SPEC §4.4:

- NativeHarness scaffolded at `scaffolded_count=2` (ethena_native + marginfi_v2)
- Remaining: canonical group + USDC bank PDA seed resolution, probe driver re-run, scaffolded→ready promotion

## Closed arcs (do not reopen without trigger)

- **Intuition** — 7 sessions, ~51 hypotheses, honest-zero, arc closed (v6.57.7)
- **Ammalgam DLEX** — honest-zero (2026-07-13)
- **PancakeSwap Infinity** — honest-zero (2026-07-13)
- **Ondo Perps** — surfaces exhausted; residuals in INVESTIGATION_STATUS.md