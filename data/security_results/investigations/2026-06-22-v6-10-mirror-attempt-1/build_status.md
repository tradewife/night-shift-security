# v6.10 Mirror Build - Engineering Status

Author: orchestrator (Principal On-Chain Forensic Investigator mode)
Status: BLOCKED on Solana platform-tools toolchain. The invalid placeholder program ID was fixed (`G9cZAWjKwksrb2fRxD3DxULMn6o6r4BhhxXNxxdXfrnA`) and Anchor now gets past the earlier `String is the wrong size` parser failure. SBF build still cannot resolve hashbrown `edition2024` under platform-tools Cargo 1.79.

## Approaches attempted (in order)

1. cargo build-sbf with default toolchain (1.79.0 via platform-tools) - blocked by transitive `hashbrown == 0.17.1` requiring `edition2024` Cargo which 1.79 does not have.
2. RUSTUP_TOOLCHAIN=nightly override before cargo build-sbf - toolchain substitution lost inside platform-tools subshell.
3. rust-toolchain.toml = nightly - same.
4. rust-toolchain.toml = 1.89.0-sbpf-solana-v1.52 - cargo-build-sbf's platform-tools script forces 1.79 again.
5. Pinned workspace hashbrown = 0.15.2 with `[patch.crates-io]` to a local stub at /tmp/hashbrown-0.15.2 - created the stub; not yet verified; high risk of breaking downstream API surface (anchor-lang pulls hashbrown HashMap internals).

## Realistic evaluation

The engineering cost of forcing SBF to compile via cargo-build-sbf is multi-hour. Mirror Path B alone was already a multi-hour task; the toolchain divergence alone has eaten a session worth of intensity with no substrate signal produced.

Two outcomes remain reasonable for v6.10:
- (A) Switch to **Marginfi Path B**. The marginfi substrate (sources/marginfi/repo/) already has a working cargo-fuzz engine compiled green in v6.7 (840M iterations). Plumb ixs_sysvar + flash-loan Actions is the only remaining gap. If even that path is blocked, this is the cleanest honest-zero data point for engine-level empirical-FNR.
- (B) Bypass cargo-build-sbf and use `anchor 0.31.1 build` after solving the Anchor.toml deserialization; let the cargo.locked deps transitively resolve. We've already v0.31.1-compatible deps aligned; only need to find an Anchor.toml config the parser accepts.

Recommendation: take path A. It exercises the proposal's fallback clause explicitly, generates substrate evidence instead of more engineering errors, and preserves the engineering time for a future session that has a stronger Rust+Solana toolchain baseline.

## 2026-06-22 correction pass

- Replaced invalid placeholder ID `MirrorKLendXXXXXXXXXXXXXXXXXXXXXXXXXXXXxx` with valid Solana pubkey `G9cZAWjKwksrb2fRxD3DxULMn6o6r4BhhxXNxxdXfrnA` in both `declare_id!` and `Anchor.toml`.
- Added `[profile.release] overflow-checks = true`.
- Re-ran `anchor build`: no more `String is the wrong size`; remaining blocker is hashbrown `edition2024` under platform-tools Cargo 1.79.

## What was emitted anyway

- sources/kamino/klend_mirror/ - directory tree (no functional state).
- sources/kamino/klend_mirror/{Anchor.toml, Cargo.toml, rust-toolchain.toml, programs/klend_mirror/Cargo.toml, programs/klend_mirror/src/lib.rs} - mirrored program skeleton, will compile only after toolchain resolution.
- data/security_results/investigations/2026-06-22-v6-10-mirror-attempt-1/{setup.md, property_fanin.md} - campaign scaffold (kept).
- /tmp/hashbrown-0.15.2 - stub crate; do not clean up: it's gitignored context that might be re-used.
