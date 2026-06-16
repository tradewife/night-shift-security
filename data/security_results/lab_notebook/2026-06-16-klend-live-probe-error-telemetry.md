# Lab entry — KLend live probe error telemetry

- date: 2026-06-16
- operator mode: autonomous orchestrator
- target: Kamino KLend
- lane: live Solana validator probes

## Observation

Ran the current KLend live probe matrix with `.env` loaded, `NSS_KLEND_FIXTURE=0`, and `NSS_HIPIF_BOUNTY_DEPTH=1`.

Probe results:

- `oracle_staleness_borrow`: tx landed, `MEASURED_DELTA_LAMPORTS:0`, `PROTOCOL_DELTA_LAMPORTS:0`
- `flash_loan_collateral_loop`: tx landed, `MEASURED_DELTA_LAMPORTS:0`, `PROTOCOL_DELTA_LAMPORTS:0`
- `reserve_isolation_drain`: tx landed, `MEASURED_DELTA_LAMPORTS:0`, `PROTOCOL_DELTA_LAMPORTS:0`
- `liquidation_solvency_gap`: local validator/RPC refusal before confirmation; infrastructure noise, not protocol evidence

The JSONL records showed the landed transactions had `failed_on_chain=true`, but stdout emitted `PROBE_STATUS:ok` because the probe transport completed successfully. That made the recursive loop less useful: the next action is not "try again", it is "decode and satisfy the on-chain failure precondition."

## System Change

Updated live KLend probe telemetry to preserve and print the exact Solana transaction status error:

- `chain_error` in `data/security_results/klend/probe_results.jsonl`
- `PROBE_CHAIN_ERROR:<json>` in validator stdout
- `PROBE_STATUS:on_chain_error:<json>` for failed-on-chain transactions

This does not relax any gate. `HARNESS_MODE:live_executed` still requires a real probe execution with measured delta above threshold. Failed-on-chain, zero-delta transactions remain non-submittable research evidence.

## Verification

Focused tests:

```bash
.venv/bin/python -m pytest \
  tests/test_klend_live_probes.py \
  tests/test_klend_probes.py \
  tests/test_klend_harness.py -q
```

Result: `12 passed`.

Live oracle probe verification:

```bash
set -a && source .env && set +a
export NSS_KLEND_FIXTURE=0 NSS_HIPIF_BOUNTY_DEPTH=1
export KLEND_PROBE=oracle_staleness_borrow
.venv/bin/python solana/run_klend_harness.py
```

Observed marker:

```text
PROBE_STATUS:on_chain_error:{"InstructionError": [0, {"Custom": 102}]}
PROBE_CHAIN_ERROR:{"InstructionError": [0, {"Custom": 102}]}
MEASURED_DELTA_LAMPORTS:0
PROTOCOL_DELTA_LAMPORTS:0
```

Latest JSONL records now include `chain_error`.

## Decision

Treat the current KLend probes as blocked on transaction/account preconditions, not as value-moving findings.

## Follow-up: source-derived instruction data

Cloned the official KLend source locally at `sources/kamino/klend/` as a research reference.

The generated interface shows:

- borrow probe should use `borrow_obligation_liquidity_v2`, not `borrow_obligation_liquidity`
- liquidation probe should use `liquidate_obligation_and_redeem_reserve_collateral_v2`
- borrow/flash/redeem instructions require one serialized `u64` argument after the discriminator
- liquidation v2 requires three serialized `u64` arguments after the discriminator

Updated `klend_v2.instruction_data_for_probe()` accordingly.

Live verification moved the oracle probe failure:

- before: `Custom 102` (`InstructionDidNotDeserialize`)
- after: `Custom 3002` (`AccountNotEnoughKeys`)

Latest JSONL now records:

```text
failure_class=account_metas_incomplete
instruction.name=borrow_obligation_liquidity_v2
MEASURED_DELTA_LAMPORTS=0
```

This confirms the probe is now past instruction deserialization and blocked on account meta construction.

Next productive work:

- Add account-state/introspection around the failing instruction so probes can distinguish missing obligation/user-token setup from true invariant failure.
- Build source-derived account meta layouts for `borrow_obligation_liquidity_v2`, including obligation, reserve mint, fee receiver, user destination token account, sysvar instructions, optional referrer/farm accounts, and remaining refresh accounts.
- Keep zero-delta failed-on-chain probes out of submission flow.
