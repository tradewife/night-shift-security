# KAST / m_ext sidecar setup (v6.27)

Date: 2026-06-27  
Target: KAST M0 Solana M Extensions  
Bounty: https://immunefi.com/bug-bounty/KAST/information/  
Repo: `https://github.com/m0-foundation/solana-m-extensions`  
Pinned commit: `c12a23acd8baeba92d4d9f64feb47837ddccca09`

## Scope slice

Primary hard-first surface:

- `programs/m_ext/`
- feature-gated variants: `scaled-ui`, `no-yield`, `crank`
- migration lane: `no-yield + migrate`
- Earn Program CPI boundary: `earn` dependency pinned at `972e896`
- secondary router: `programs/ext_swap/`

Explicitly deprioritized until the core invariants are executable:

- broad CLI/deployment scripts
- peripheral whitelisting admin flows in `ext_swap`
- generic acknowledged issues without variant escalation

## Build substrate

Built with:

- Anchor CLI `0.31.1` via `~/.avm/bin/anchor-0.31.1`
- Solana toolchain initialized by Anchor as `2.1.0`

Exported sidecar artifacts:

- `sources/kast/target/deploy/ext_swap.so`
- `sources/kast/target/deploy/m_ext_scaled_ui.so`
- `sources/kast/target/deploy/m_ext_no_yield.so`
- `sources/kast/target/deploy/m_ext_crank.so`
- `sources/kast/target/deploy/m_ext_no_yield_migrate.so`
- IDLs under `sources/kast/idls/`
- types under `sources/kast/types/`
- provenance in `sources/kast/source_manifest.json`

## Variant constraints from source

`programs/m_ext/src/lib.rs` enforces:

1. Exactly one of `scaled-ui`, `no-yield`, `crank`
2. `migrate + crank` is invalid unless `wm` is also enabled

This means the executable matrix is not just parameter variation. Each variant is a distinct program image with different instruction surfaces and state layouts.

## Public signals / exclusions

Acknowledged ineligible issues from the bounty handoff:

- unsupported mint extensions
- trunc / floor off-by-one around multiplier indexing
- retroactive fee application in crank
- pending yield loss when earners are removed
- `CloseMintAuthority + PermanentDelegate` activated on ext mint

The campaign objective is to find **generalizations or adjacent exploitable consequences**, not resubmit the excluded literals.

## Audit baseline

On-disk PDFs:

- `adevar_m_extensions_audit_report.pdf`
- `adevar_v2_audit.pdf`
- `halborn_m_extensions_audit_report.pdf`
- `halborn_v2_audit.pdf`
- `ottersec_m_extensions_audit_report.pdf`

Audit PDFs are advisory only until reproduced against the pinned source and built artifacts.
