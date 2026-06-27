# Strategy — DVN Positive / Negative Quorum Sequence

**Covers:** PROP-PKT-002, PROP-PKT-003, PROP-PKT-008, PROP-PKT-010

## Codegraph-hardening focus

- Promote from codec-only checks to stateful quorum consumption checks.
- Exercise the exact `verify -> commitVerification -> verify` lifecycle on the pinned ULN302 fixture.

## Sequences

1. Positive control: single-DVN verify, then commit, then confirm endpoint channel insertion.
2. Negative control: commit again without fresh verify, expect `LZ_ULN_Verifying`.
3. Cross-header negative: verify header A, attempt commit on header B with same payload hash, expect `LZ_ULN_Verifying`.

## Expected false positives

- Fixture miswiring of default ULN config
- Header construction mismatch vs `PacketV1Codec`
