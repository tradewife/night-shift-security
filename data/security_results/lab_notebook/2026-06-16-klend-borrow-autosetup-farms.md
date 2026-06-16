# Lab entry - KLend borrow autosetup and Farms clone

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Kamino KLend
- lane: Solana validator-backed oracle borrow probe

## Observation

The KLend oracle borrow probe had already moved from bad instruction data (`Custom 102`) to incomplete account metas (`Custom 3002`). I continued the source-derived account wiring for `borrow_obligation_liquidity_v2`.

## System Change

- Replaced the borrow probe's generic account specs with source-ordered KLend account metas.
- Derived the vanilla obligation PDA and user metadata PDA from KLend seeds.
- Derived the user's USDC ATA and added an automatic setup path for `init_user_metadata`, `init_obligation`, and ATA creation.
- Added USDC/SOL mints to the cloned data-account set.
- Cloned the Kamino Farms executable program and verified it alongside KLend/KVault/oracle programs.
- Fixed optional `None` accounts to use the KLend program id as read-only, matching the local KLend interface.
- Added failure classifiers for Anchor `3007`/`3009` and KLend lending errors `6007`/`6009`.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest \
  tests/test_klend_tx.py \
  tests/test_klend_live_probes.py \
  tests/test_klend_probes.py \
  tests/test_klend_harness.py \
  tests/test_validator_profiles.py -q
```

Result: `26 passed`.

Live command:

```bash
set -a && source .env && set +a
export NSS_KLEND_FIXTURE=0 NSS_HIPIF_BOUNTY_DEPTH=1 NSS_KLEND_AUTO_SETUP=1
export KLEND_PROBE=oracle_staleness_borrow
.venv/bin/python solana/run_klend_harness.py
```

Latest observed markers:

```text
CLONED_PROGRAMS:KLend2g3...,KvauGMsp...,HFn8GnP...,FarmsPZp...
PROBE_TX_CONFIRMED:1
PROBE_STATUS:on_chain_error:{"InstructionError": [0, {"Custom": 6009}]}
MEASURED_DELTA_LAMPORTS:0
PROTOCOL_DELTA_LAMPORTS:0
```

Latest JSONL:

```text
failure_class=reserve_stale
setup.confirmed=true
setup.failed_on_chain=false
programs_verified includes FarmsPZpWu9i7Kky8tPN37rs2TpmMrAZrC7S7vJa91Hr
```

The immediately prior run hit `Custom 6007` (`MathOverflow`) after the same executable-program fix; this is recorded as a classified `math_overflow` path. Both are KLend lending-level checks, not account meta or Anchor executable failures.

## Decision

This is not submit-ready. It is a meaningful harness advancement: the probe now initializes the borrower-side accounts and reaches KLend lending logic with zero protocol delta. The next productive step is to prepend real `refresh_reserve` / `refresh_obligation` instructions with source-derived oracle remaining accounts, then rerun the borrow path against refreshed reserve and obligation state.

