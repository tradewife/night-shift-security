# Strategy: authority transitions and Earn CPI boundary

Properties:

- `PROP-KAST-007`
- `PROP-KAST-008`
- `PROP-KAST-009`
- `PROP-KAST-010`
- `PROP-KAST-016`

## Aim

Attack trust boundaries rather than arithmetic:

- admin transfer / accept / revoke
- wrap authority additions/removals
- earn authority changes
- CPI account substitution against the Earn Program
- migration path invariants
- Token-2022 authority extension composition (`CloseMintAuthority`, `PermanentDelegate`)

## Sequence families

1. `transfer_admin -> accept_admin -> revoke_admin_transfer`
2. `add_wrap_authority -> wrap -> remove_wrap_authority -> wrap`
3. `set_earn_authority -> add_earn_manager -> claim_for`
4. `migrate_m` with mismatched or partially initialized accounts
5. CPI replay with substituted earn/global/recipient accounts
6. `add_wrap_authority/remove_wrap_authority` under ext mint authority-extension combinations

## Parameter focus

- stale pending admin states
- removed wrap authorities attempting follow-on wrap
- mismatched signer and PDA ownership
- migration contexts with variant/account-layout skew
- close-authority or permanent-delegate combinations that could broaden mint/burn/claim reach

## Expected false-positive classes

- admin-only paths that require privileged malfeasance
- migration-only layouts unsupported by the chosen feature image
- CPI failures caused solely by incomplete harness setup

## Candidate signal

Promote only if a non-privileged or wrong-privileged actor gains control, claims value, bypasses the intended CPI/account binding, or inherits mint/claim powers through an unintended extension-authority composition.
