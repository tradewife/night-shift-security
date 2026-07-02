# Agglayer Cantina Deep-Dive Setup

Date: 2026-07-03

## Scope Snapshot

- Bounty: `https://cantina.xyz/bounties/3aaad22b-52ee-4bb2-bed2-4be53b0993cc`
- Contracts clone: `sources/agglayer-contracts/repo`
- Rust node/proof clone: `sources/agglayer/repo`
- Bridge-and-call clone: `sources/lxly-bridge-and-call/repo`
- Primary target subsystem: pessimistic proof verification plus `AgglayerManager`, `AgglayerBridge`, `AgglayerGER`, `AgglayerGateway`, and cross-component settlement roots.

## Source Revisions

- `agglayer-contracts`: shallow clone from GitHub on 2026-07-03.
- `agglayer`: shallow clone from GitHub on 2026-07-03.
- `lxly-bridge-and-call`: shallow clone from GitHub on 2026-07-03, archived/deprecated, secondary only.

## Local Analysis Artifacts

- CodeGraph index initialized for contracts and Rust repos.
- CodeGraph outputs are in `codegraph/`.
- No unauthorized mainnet interaction was performed.

## Current Assumptions

- Cantina exact pinned commit and exclusions still need authenticated confirmation.
- Mainnet addresses in the handoff and source `CLAUDE.md` are treated as reference deployments until bytecode verification is run.
- Source-only observations are not submission evidence. Promotion requires an executable local/fork reproducer plus NSS submission gates.
