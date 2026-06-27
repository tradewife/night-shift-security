# Strategy: ext_swap follow-up after core stabilization

Properties:

- `PROP-KAST-011`
- `PROP-KAST-012`

## Aim

Keep the router secondary until core `m_ext` invariants are executable, then check whether whitelisting and 1:1 assumptions break under mixed extension variants.

## Sequence families

1. `initialize_global -> whitelist -> swap`
2. `swap` between no-yield and scaled-ui extensions
3. `swap` with migrate-enabled extension metadata
4. malformed extension/global/whitelist accounts during `swap`

## Parameter focus

- mixed variant images
- mismatched extension mints
- stale or substituted whitelist/global accounts

## Expected false-positive classes

- swap failures caused by uninitialized partner extensions
- variant combinations the product never whitelists in practice

## Candidate signal

Promote only if whitelist bypass, arbitrary unwrap/mint, or non-1:1 accounting emerges after valid core extension setup.
