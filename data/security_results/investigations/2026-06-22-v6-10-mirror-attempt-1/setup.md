# v6.10 Ultrafuzz Campaign - Setup Notes

session: v6.10 (Day Shift 2026-06-22)
target: Kamino KLend flash-loan surface (mirror program only; deployed mainnet BPF rejected every standard anchor-lang sighash variant for `initLendingMarket` in v6.9 per `discriminator_probe.json`).

orchestrator: Principal On-Chain Forensic Investigator (LLM in the loop; multiple fresh-context attempts per Ultrafuzz post).

campaign_root: data/security_results/investigations/2026-06-22-v6-10-mirror-attempt-1
mirror_repo: sources/kamino/klend_mirror
existing_harness: sources/kamino/klend/tests/flash_loan_fuzz.ts (compiles green with deps @coral-xyz/anchor ^0.31.1 + @solana/spl-token ^0.4.6 + ts-mocha ^10).

mode_of_operation:
  - Hypothesis first (property fan-in), executable second, evidence always.
  - Run each strategy K attempts with fresh payer keypair + fresh reserve + fresh local validator boot where practical.
  - Preserve every failure as tx_sig + instruction_data + pre/post account deltas + replay_command.
  - Never overwrite a failing test.
  - Adjudicate each candidate before promotion; `qualifies_for_submission()` is the only path into `submittable/`.

constraints:
  - Do NOT touch user-owned untracked dirs (`sources/drift/`, `sources/reserve/repo/`).
  - Do NOT modify the deployed mainnet BPF or mainnet reserve accounts.
  - Do NOT auto-submit, push, or loosen submission gates.
  - Do NOT bump `submit_ready` beyond what gates support.

fallback_paths:
  - If mirror coverage is false-positive-only or honest-zero with no substrate defect surface: switch to Marginfi Path B (ixs_sysvar, flash-loan actions, cargo-fuzz).
  - Marginfi source lives in sources/kamino/klend_mirror/../marginfi - keep mirror work isolated under mirror/ to avoid cross-contaminating the real substrate.
