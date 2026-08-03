# Next session queue

**v6.70.0-alpenglow-s05-rewards-votepool.** Hard-first S00–S05 closed; `submit_ready=0`.  
Competition window: **2026-08-05 16:00 UTC → 2026-08-19 16:00 UTC**.

## Priority queue

### 1. Alpenglow at/after window open (CRITICAL)

- `git -C sources/agave/repo pull --ff-only`; re-pin `sources/agave/COMMIT`.
- Smoke re-run S00–S05 latent preconditions if HEAD moved.
- Explore any newly unlocked surfaces (avoid #13235 / #13790 / closed `blocking-ag` duplicates).
- Workspace: `data/security_results/investigations/2026-08-02-alpenglow-bounty/`
- Campaign: `campaigns/alpenglow/`
- Pin baseline: `03cdac9f36846f1c927b57e04a164a44bbf99f40` (update after pull)

### 2. Alpenglow latent park (only if new wiring)

| ID | Need for impact |
|----|-----------------|
| ALP-ACC-001 | Own+External same rank or duplicate External past VotePool / self-send |
| ALP-CERT-002-LATENT | Dual Finalized requires conflicting notarize per rank past VotePool |

Do **not** submit latents without production path + impact class. S05 confirmed both Votor and Rewards paths blocked at packet ingress by `keep_vote` self-filter + VotePool per-(rank, vote, slot) dedup.

### 3. Deferred (do not steal Alpenglow window)

| Rank | Target | Notes |
|------|--------|-------|
| 3a | Veilo Superteam | Low EV unless Alpenglow blocked |
| 3b | Pendle / Polymarket | After competition or user pivot |

### Explicitly do not re-open

- BoLD — honest-zero, CLOSED
- Alpenglow public tracker items as novel findings (#14206, #14208, closed `blocking-ag` list)
- Faithful S00–S05 without new commit/evidence

## Local artifacts (not pushed by default)

- `sources/agave/repo/`, `sources/alpenglow/repo/`
- `data/security_results/investigations/2026-08-02-alpenglow-bounty/`
- `data/security_results/lab_notebook/2026-08-02-alpenglow-*.md` and `2026-08-03-alpenglow-*.md`
- `campaigns/alpenglow/`
