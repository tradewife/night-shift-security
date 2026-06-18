# Night Shift Security — v5 Completion Spec

**Version:** 5.1.0-roadmap (draft)  
**Date:** 2026-06-19  
**Authority:** [`SYSTEM_AUDIT_2026-06-18.md`](SYSTEM_AUDIT_2026-06-18.md) phases 1–4 + corrections C1–C9  
**Baseline:** SPEC 5.0.0-draft, **608 passed / 6 skipped**, `ready_count=2`, cron unpaused (Phase 6)

This document is the **completion contract** from the current v5 substrate to a system that can discover, measure, and gate **real** findings against live Immunefi and Cantina programs — with **Solana programs prioritised** for new scope inclusions.

---

## 1. Completion definition

The audit’s real goal (§“The wrong goal model”) is not “clean gates with zero submissions.” Completion means:

| # | Criterion | Measurable exit |
|---|-----------|-----------------|
| G1 | **Substrate** | ≥8 targets at `status=ready` in `native_harness_status.json`, **≥4 of them Solana** |
| G2 | **Measurement** | Every `ready` target has `data/security_results/impact/<slug>_measured_delta.json` with `measured_impact=true` |
| G3 | **Candidates** | Every `ready` target has ≥50 rows in `concrete_candidates.jsonl` with real discriminators + `source_ref.commit` |
| G4 | **Discovery loop** | Cron rotates cold targets (Phase 4 on); saturated slugs do not dominate weekly compute (D5) |
| G5 | **First submission path** | ≥1 finding passes `qualifies_for_submission()` with `impact_oracle.measured=true` and human gate approval |

G1–G4 are engineering completion. G5 is bounty completion. Both are tracked; G5 may lag G4 by weeks of hunt depth.

---

## 2. Audit phase status (as of 2026-06-19)

| Audit phase / correction | Status | Evidence |
|--------------------------|--------|----------|
| **Phase 1** Re-orient | **closed** | v5 pivot accepted; `pick_next_target` native gate (C3); cron pause gate (C8) |
| **Phase 2** First EVM harness | **closed** | `uniswap_v4: ready`, measured slot0 delta |
| **Phase 3** Scale EVM harnesses | **partial** | `aave_v3: ready`; `morpho_blue: harness_built` (zero-delta); Pendle/Compound/Curve **not started** |
| **Phase 4** Reinstate cron | **closed** | Phase 6 dryrun; `NSS_HIPIF_PAUSE_FOR_NATIVE=0`; Phase 4 rotation documented |
| **C1** NativeHarness protocol | **partial** | 3 EVM modules; **0 Solana v5 native modules** |
| **C2** MeasuredImpactOracle | **closed** | `impact/measured_oracle.py` + Foundry probes |
| **C3** Picker precondition | **closed** | `native_picker.py` |
| **C4** Saturation escape | **closed** | `has_measured_delta` + measured-delta evidence |
| **C5** Full registry walk | **closed** | `NSS_PREFER_FULL_REGISTRY=1` in `depth_env()` |
| **C6** ABI/IDL bind | **closed** | `fork_validation._has_native_bind` |
| **C7** Fork label split | **closed** | `{catalog_anchor, live_program, value_moving, novel}` |
| **C8** Cron precondition | **closed** → **unpaused** | Operator applied 2026-06-19 |
| **C9** Day Shift focus | **open** | `day_shift/current.md` still lists P0-1 as open |

### Structural defects (D1–D8) — remaining work

| Defect | Remaining gap | Completion phase |
|--------|---------------|------------------|
| **D1** Fake scope (28/249) | Immunefi Solana programs outside curated set not onboarded | Phase 9 |
| **D2** Fake harness | Solana has KLend *fixture* depth only; no v5 `native/kamino.py` | **Phase 7–8** |
| **D3** Fake impact oracle | Solana probes still fee-only CPI; no SPL/token-account delta oracle | **Phase 8** |
| **D4** Empty concrete candidates | Only wormhole + partial EVM slugs populated | Phase 7–9 per target |
| **D5** Saturating loop | Mitigated by Phase 4 rotation; needs Solana cold targets | Phase 9 |
| **D6** Generic hypothesis generator | Per-target sequence emitters not shipped | Phase 10 |
| **D7** Cron compute concentration | Unpaused; still Wormhole/Kamino-heavy until Solana harnesses ready | Phase 8–9 |
| **D8** Fork tally lies | **closed** (C7) | — |

---

## 3. Solana-first scope priority

Curated Immunefi Solana programs today (`immunefi_registry.py`):

| Rank | Slug | Max bounty | Current NSS state | v5 target |
|------|------|------------|-------------------|-----------|
| **S1** | `jito` | $2.0M | catalogue analogue only | Phase 8 row 2 |
| **S2** | `kamino` | $1.5M | KLend validator harness; fee-only CPI | **Phase 7 row 1** (upgrade first) |
| **S3** | `raydium` | $505K | catalogue only | Phase 8 row 3 |
| **S4** | `orca` | $500K | catalogue only | Phase 8 row 4 |
| **S5** | `onre` | $500K | catalogue only | Phase 9 |
| **S6** | `marinade` | $250K | catalogue only | Phase 9 |

**Wormhole** ($1M, multichain) retains depth passes but is **not** a Solana-native harness priority — EVM + Solana bridge components already have semantic recon; value-moving hunt continues under existing Wormhole RSI.

**Expansion beyond curated 6:** Phase 9 runs `platform sync --all` and ranks **unsynced Solana Immunefi listings** by `max_bounty_usd` for harness onboarding (Drift, Marginfi, Sanctum, etc. when live on platform).

---

## 4. Implementation phases (7 → 12)

### Phase 7 — EVM close-out + Kamino v5 skeleton (1 session)

**Goal:** Finish Phase 3 EVM row 1; start Solana substrate.

| Task | Deliverable | Tests |
|------|-------------|-------|
| Morpho Blue liquid market probe | `morpho_blue: ready` OR documented RPC/subgraph gap | +4 `test_morpho_value_moving` |
| `native/kamino.py` skeleton | Program IDs, top-10 KLend instruction discriminators, `load_idl()`, `resolve_market()` | +17 `test_native_kamino.py` |
| Clone `sources/kamino/repo` | Pin commit in manifest | — |
| `semantic map --slug kamino` | ≥50 `concrete_candidates.jsonl` rows | — |
| Manifest | `kamino: mapped` → `harness_built` | — |

**Exit:** `ready_count` ≥2 (unchanged if Morpho fails); `kamino: harness_built`; pytest ≥622.

---

### Phase 8 — Solana measured-impact oracle + Kamino ready (1–2 sessions)

**Goal:** Ship C2 analogue for Solana (D3). First **Solana** `ready` harness.

| Task | Deliverable |
|------|-------------|
| `impact/solana_measured_oracle.py` | `(pre_token_accounts, post_token_accounts, pre_reserve, post_reserve)` diff; `MEASURED_LAMPORT_THRESHOLD`; SPL `amount` + reserve field deltas |
| `solana/kamino_measure.py` or Anchor test | Cross-slot read of USDC reserve / market state on mainnet RPC (no fixture markers) |
| Evidence | `data/security_results/impact/kamino_measured_delta.json` with `measured_impact=true` (interest accrual, utilization tick, or oracle publish — **not** fee-only CPI) |
| Gate wire | `submission_gates` accepts `impact_oracle.measured` from Solana envelope (read-only patch; no loosening) |
| Promotion | `native mark --slug kamino --status ready` |
| KLend harness | `NSS_KLEND_FIXTURE=0` default in cron; fixture path retained for CI only |

**Exit:** `ready_count=3` (EVM×2 + kamino); first Solana positive measured delta; pytest +20 net.

**Anti-pattern:** Fee-only CPI, fixture markers (`HARNESS_MODE:fixture`), or synthetic `IMPACT_LAMPORTS` without validator tx proof → stays `harness_built`.

---

### Phase 9 — Solana harness scale (Jito, Raydium, Orca) (2–3 sessions)

**Goal:** G1 partial — 4 Solana `ready` targets.

| Row | Slug | Repo / IDL source | Measured probe shape |
|-----|------|-------------------|----------------------|
| 8.1 | `jito` | Jito stake pool / tip payment programs | Stake account or tip vault lamport/SPL delta across epoch boundary |
| 8.2 | `raydium` | Raydium CLMM | Pool vault balance delta across `swap` or fee collection window |
| 8.3 | `orca` | Orca Whirlpools | Whirlpool sqrt price / liquidity delta (mirror UniV4 slot0 pattern) |

Per row (template from EVM Phase 3):

1. `git clone` → `sources/<slug>/repo`
2. `semantic map --slug <slug> --kind <amm|lending|staking>`
3. `src/night_shift_security/native/<slug>.py`
4. `solana/tests/<Slug>Measure.rs` or Python RPC snapshot script
5. `scripts/_capture_<slug>_measurement.py`
6. `impact/<slug>_measured_delta.json`
7. `native mark --status ready`

**Exit:** `ready_count≥5` (2 EVM + 3 Solana minimum); each new slug ≥50 candidates.

---

### Phase 10 — Per-target hypothesis sequences (D6) (1 session)

**Goal:** Replace generic `parameter_spaces` emission for `ready` slugs.

| Task | Deliverable |
|------|-------------|
| `hypothesis/concrete_sequences.py` | Read `concrete_candidates.jsonl`; emit `InstructionSequence` / `CallSequence` with real discriminators |
| Wire into `bounty_loop` depth pass | Only for `native_status≥harness_built` |
| Foundry/Solana PoCgen | One end-to-end sequence → `poc verify` on kamino or uniswap_v4 |

**Exit:** Depth pass on `kamino` uses ≥1 sequence from concrete store (not catalogue grid).

---

### Phase 11 — Full-registry Solana discovery (D1 + D5) (1 session)

**Goal:** Cron discovers new Solana programs automatically.

| Task | Deliverable |
|------|-------------|
| `platform sync --all` at chain start | Already in runner; verify weekly |
| `pick_next_target_v6_phase4` Solana bias | Env `NSS_PREFER_SOLANA=1` boosts `ecosystem=solana` in rotation score |
| `IMMUNEFI_PROGRAMS` expansion | Add top-10 synced Solana slugs from `scope_registry.json` not yet in curated tuple |
| Discovery budget | 80% picks from slugs with `native_status=missing` (D5) |

**Exit:** One nightly run picks a **new** Solana slug; manifest gains `mapped` entry.

---

### Phase 12 — Hunt-to-submit (G5) (ongoing)

**Goal:** First `submit_ready=true`.

| Track | Actions |
|-------|---------|
| Wormhole | Paged Wormholescan corpus; non-mocked accounting violations only |
| Kamino | Live KLend probes past fee-only; oracle staleness / refresh windows |
| EVM ready | UniV4 hook surfaces; Aave reserve edge cases |
| Solana new | Jito MEV boundary; Raydium/Orca CLMM donate/swap paths |

**Exit:** `submission_alert.json` v2 fires; `operator-submit` skill; export to `bounty/submittable/`.

---

## 5. Native manifest roadmap

Target end state for `native_harness_status.json`:

```
ready_count: 8+

EVM ready:     uniswap_v4, aave_v3, morpho_blue, pendle (TBD)
Solana ready:  kamino, jito, raydium, orca
Mapped/build:  compound_v3, marinade, onre, wormhole (bridge depth)
```

| Slug | Chain | Phase | Status today → target |
|------|-------|-------|------------------------|
| uniswap_v4 | ethereum | 2 | ready |
| aave_v3 | ethereum | 3 | ready |
| morpho_blue | ethereum | 3 | harness_built → ready |
| kamino | solana | 7–8 | **missing** → ready |
| jito | solana | 9 | missing → ready |
| raydium | solana | 9 | missing → ready |
| orca | solana | 9 | missing → ready |
| pendle | ethereum | 7+ | missing → ready |
| compound_v3 | ethereum | 7+ | missing → harness_built |
| wormhole | multichain | legacy | semantic recon only; not v5 `ready` gate |

---

## 6. Solana technical contract

Every Solana NativeHarness module MUST expose (mirror `native/uniswap_v4.py`):

```python
def program_ids() -> dict[str, str]: ...
def discriminators() -> dict[str, bytes]: ...  # 8-byte Anchor sighash
def load_idl() -> dict: ...
def resolve_accounts(market_hint: str, rpc_url: str) -> AccountResolution: ...
```

Measured-impact envelope (`impact/solana_measured_oracle.py`):

```json
{
  "schema_version": "measured-oracle-solana.v1",
  "slug": "kamino",
  "spec": { "slot_pre": 0, "slot_post": 0, "program_id": "..." },
  "pre": { "token_accounts": [], "reserve_fields": {} },
  "post": { "token_accounts": [], "reserve_fields": {} },
  "delta": { "spl_amount_deltas": [], "reserve_deltas": {}, "lamport_delta": "0" },
  "measured_impact": true
}
```

**Promotion rule (unchanged from C2):** `ready` only when `measured_impact=true` on live mainnet/devnet RPC reads — never fixture markers.

---

## 7. Cron & operator configuration (applied 2026-06-19)

### Live `nightsoul` profile

| Setting | Value | Where |
|---------|-------|-------|
| Job ID | `343324bfcbb2` | `hermes --profile nightsoul cron list` |
| Mode | `no-agent` | `hermes cron edit ... --no-agent` |
| Script | `nss-hipif-chain.sh` | profile `scripts/` (synced via `install-nightsoul-overlay.sh`) |
| Timeout | `10800` s | `cron.script_timeout_seconds` in profile `config.yaml` |
| Env | see below | repo `.env` (sourced by bootstrap) |

### Production environment variables

```bash
# repo .env (gitignored) — sourced by nss-hipif-chain.sh
NSS_HIPIF_PAUSE_FOR_NATIVE=0
NSS_PHASE4_ROTATION_ENABLED=1
NSS_HIPIF_MODE=deterministic
NSS_HIPIF_BOUNTY_DEPTH=1
NSS_KLEND_FIXTURE=0
HERMES_CRON_SCRIPT_TIMEOUT=10800
```

### Operator maintenance commands

```bash
cd /home/kt/projects/rtp/night-shift-security
bash hermes/install-nightsoul-overlay.sh          # sync scripts + skills
hermes --profile nightsoul config set cron.script_timeout_seconds 10800
hermes --profile nightsoul cron edit 343324bfcbb2 \
  --no-agent --clear-skills --script nss-hipif-chain.sh --prompt ""
# Verify
NSS_HIPIF_MODE=dryrun bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -5
# Expect: pause_for_native=0 bounty_depth=1
```

See also: [`hermes/cron/OPERATOR_APPLY.md`](hermes/cron/OPERATOR_APPLY.md).

---

## 8. Test budget per phase

| Phase | Net new tests | Cumulative baseline |
|-------|---------------|---------------------|
| 6 (shipped) | +14 | 608 / 6 skipped |
| 7 | +14 | 622 |
| 8 | +20 | 642 |
| 9 | +45 (15×3 slugs) | 687 |
| 10 | +12 | 699 |
| 11 | +8 | 707 |

**Rule:** If pytest drops below phase baseline, stop and revert.

---

## 9. Session handoff checklist

Each phase close must update:

1. `data/security_results/lab_notebook/YYYY-MM-DD-v5-phaseN-*.md`
2. `AUDIT.md` § Current v5 Gaps
3. `SPEC.md` §3 baseline test count
4. `CHANGELOG.md`
5. `native_harness_status.json` via `native mark`
6. Night Shift handoff in `day_shift/current.md` when Day Shift opens

---

## 10. Immediate next session (Phase 7 kickoff)

**Priority order:**

1. **Kamino** — `native/kamino.py` skeleton + semantic map (Solana S2; upgrades existing KLend investment)
2. **Morpho Blue** — liquid market probe (EVM Phase 3 row 1 close-out)
3. **Jito** — IDL fetch + program ID manifest entry (`mapped`)

**Do not:**

- Loosen `submission_gates.py` / `evidence_grading.py`
- Mark Solana `ready` on fixture/fee-only CPI
- Re-pause cron without `ready_count` regression plan

---

## 11. References

- [`SYSTEM_AUDIT_2026-06-18.md`](SYSTEM_AUDIT_2026-06-18.md) — eight defects + phases 1–4
- [`SPEC.md`](SPEC.md) v5.0.0-draft — architecture baseline
- [`AGENTS.md`](AGENTS.md) — Phase 6 cron state
- [`data/security_results/lab_notebook/2026-06-19-HANDOVER-v5-phase6-hunt-and-rotate.md`](data/security_results/lab_notebook/2026-06-19-HANDOVER-v5-phase6-hunt-and-rotate.md)
- KLend harness: `solana/run_klend_harness.py`, `solana/klend_probes.py`
- EVM templates: `native/uniswap_v4.py`, `foundry/test/AaveV3Measure.t.sol`