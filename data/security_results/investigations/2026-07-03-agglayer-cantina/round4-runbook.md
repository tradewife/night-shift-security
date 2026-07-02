# Agglayer Cantina — Round 4 operator runbook

**Prereq:** `export PATH="$HOME/.local/bin:$PATH"` (protoc 28.3)

## Primary subsystem pressure

```bash
# Rust balance underflow (PROP-AGG-003) — long compile + SP1
cd sources/agglayer/repo
cargo test -p pessimistic-proof-test-suite e2e_local_pp_overflow_attempt -- --nocapture

# Solidity globalIndex / nullifier (H-IDX partial)
cd sources/agglayer-contracts/repo
forge test --match-contract AgglayerGlobalIndexProbe -q

# GER duplicate-root behavior (H-GER-001)
./node_modules/.bin/hardhat test test/contractsv2/PolygonGlobalExitRootV2.test.ts

# Bridge core + fee-token follow-up (H-FEE-001)
./node_modules/.bin/hardhat test test/contractsv2/BridgeV2.test.ts
# Next: wire FeeOnTransferERC20 deposit vs leaf amount (see strategies/fee-on-transfer-custody.md)

# Encoding parity (already green R1)
./node_modules/.bin/hardhat test test/contractsv2/real-prover-sp1/e2e-verify-proof.test.ts
```

## Promotion gates

- No `submit_ready` until executable repro + NSS `qualifies_for_submission()`.
- Record each run in `runs.jsonl` with exit code and classification.
