# SPEC + handover — Night Shift Security v5 Phase 3 (Morpho Blue harness start, C6 + cron flips) — fresh agent pickup

**Paste this entire document into your next session as context.**

You are a fresh agent. The previous session shipped **C3 + C4 + C5 + C7**
of the v5 audit (`SYSTEM_AUDIT_2026-06-18.md`): the bounty picker now
honors the native-harness manifest, refuses missing/mapped slugs, walks
the full live registry, ranks by max_bounty_usd * state-multiplier, and
emits the four additive fork_reproduced_* sub-labels. Tests went from
479 / 6 skipped → 506 / 6 (+27 net). The cron resume gate
(ready_count ≥ 1) remains intact via the uniswap_v4: ready entry.

Your job is to:

1. Land C6 — patch validation/fork_validation._fork_candidate_set so the
   top-N fork binder requires a real ABI/IDL hash, not severity.
2. Wire prefer_full_registry=True into
   nss-hipif-chain-run.py:_run_full_chain so the cron chain actually
   walks the live registry (C5 helpers exist; cron does not flip it).
3. Start Phase 3 — first scale harness: Morpho Blue (audit Phase 3 table).
   Phase 3 secondary target is Aave v3.
4. Surface Phase 4 refresh-14d rotation as an explicit follow-up.

Keep the trust boundary and the synthetic substrate (used as regression
fixtures) untouched. Do NOT loosen submission_gates.py,
evidence_grading.py, novel_gate.py, task_verifier.py, or
qualifies_for_submission().

---

## 1. Where we are

| Commit | Phase | What shipped |
|--------|-------|--------------|
| 018ee06 | v5 pivot | SPEC 5.0.0-draft — NativeHarness substrate gate |
| 1c09485 | C1 | First NativeHarness (Uniswap v4 PoolManager + IHooks + Foundry stub) |
| fbd275c | C2 | MeasuredImpactOracle + Foundry fork probe + first on-chain slot0 delta → uniswap_v4: ready, ready_count=1 |
| 415d057 | C3+C4+C5+C7 (today) | Picker precondition gate (refuse missing/mapped), full live registry walk helpers, measured-delta escape, fork_reproduced label split. +27 tests, 506 / 6 skipped |

The 04:00 cron runs nss-hipif-chain.sh no-agent deterministic against
the uniswap_v4: ready gate; the chain is paused-by-default unless
NSS_HIPIF_PAUSE_FOR_NATIVE=0. Native manifest entry:
data/security_results/loop/native_harness_status.json → uniswap_v4: ready.

Repo state at session start (sanity):

- git status --porcelain clean except goal-reference.md + solodit-api-ref.md
  (user-owned; ignore).
- .venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q → 506 passed, 6 skipped.
- native mark/status living at data/security_results/loop/native_harness_status.json.
- data/security_results/impact/uniswap_v4_measured_delta.json gitignored,
  schema_version=measured-oracle.v1, sqrtPriceX96: 0 → 2**96 slot0 delta.
- sources/uniswap_v4/repo cloned @ 46c6834698c48bc4a463a86d8420f4eb1d7f3b75.

---

## 2. Read FIRST (in this exact order)

1. SYSTEM_AUDIT_2026-06-18.md — focus on C6 (fork_validation top-N
   ABI/IDL hash), the Phase 3 scale-harness table, and Phase 4
   refresh-14d rotation.
2. SPEC.md §3 (Current Shipped Baseline) and §26-31 (Implementation
   Status entries to date).
3. AUDIT.md "Current v5 Gaps" table — confirm C3/C4/C5/C7 are still
   marked shipped and that C6 is still pending.
4. CHANGELOG.md latest 2026-06-18 entry (today) so you do not duplicate
   work; previous 2026-06-19 entries cover C1/C2.
5. data/security_results/lab_notebook/2026-06-18-v5-c3-pick-next-target.md
   — what landed today; the source of truth for the new picker semantics.
6. src/night_shift_security/validation/fork_validation.py — _fork_candidate_set
   is the C6 target. Read the function in full and trace the top-N
   severity ranking.
7. hermes/scripts/nss-hipif-chain-run.py — find the call site that invokes
   pick_next_target(...) inside _run_full_chain. Today the helper supports
   prefer_full_registry=True but the cron caller does NOT pass it.
8. src/night_shift_security/native/uniswap_v4.py — this is the template
   for your Morpho Blue / Aave v3 harnesses. It is reference only; do NOT edit.
9. src/night_shift_security/bounty/native_picker.py — re-read
   bounty_priority_score and rank_pickable_slugs to understand the
   ranking the cron will now consult at scale.

Do NOT re-read:

- tests/test_api.py (sandbox socket restrictions).
- Solodit / AuditVault corpus (advisory-only, no Phase 3 relationship
  beyond lineage stamping).
- The full Synthetic substrate under domain/attack_templates/ (kept for
  regression fixtures only — never wire into C6 or Phase 3).


---

## 3. Repo state you must preserve

| Item | Where | Status |
|------|-------|--------|
| Branch | main | clean except user-owned notes |
| Last commit | 415d057 | pushed |
| Pytest baseline | tests/ --ignore=tests/test_api.py | 506 passed, 6 skipped |
| Native manifest | native_harness_status.json | uniswap_v4: ready, ready_count=1 |
| Evidence file | impact/uniswap_v4_measured_delta.json | gitignored, present |
| Cron bootstrap | hermes/scripts/nss-hipif-chain.sh | NSS_HIPIF_PAUSE_FOR_NATIVE=1 default; gate releases when ready_count=1 |
| Legacy synthetic engine | domain/attack_templates/*.py, core/hypothesis.py, parameter_spaces.py | UNTOUCHED — regression fixtures per audit |
| Trust boundary | validation/submission_gates.py, validation/evidence_grading.py, validation/novel_gate.py, validation/task_verifier.py | UNTOUCHED — do NOT loosen |

If pytest drops below 506 / 6 skipped, stop and revert. If ready_count
!= 1, stop and ask.

---

## 4. The goal of YOUR session

Ship C6 (mandatory), the cron full-registry flip (mandatory), and
Morpho Blue harness start (mandatory). At session end:

1. validation/fork_validation._fork_candidate_set requires a real
   ABI/IDL hash on top-N, not severity. Audit specifies:
   - For Solidity candidates: entrypoint.abi_signature_hash != "".
   - For Anchor/Solana candidates: entrypoint.selector_or_discriminator
     != "" AND source_ref.commit != "".
   - Severity is documentation, not a gate. Catalogue anchors without
     an ABI/IDL hash are filtered out of the top-N fork binder (they
     remain in fork_validation.anchors for fallback research only).
   - Pick the precise threshold at top_n ≥ 1. Default top_n=5 per the
     audit recommendation table.

2. nss-hipif-chain-run.py:_run_full_chain flips the C5 flag so the cron
   actually exercises pick_next_target(prefer_full_registry=True). The
   simplest place is the single call site inside _run_full_chain. Add a
   regression smoke-test that the cron path round-trips through
   list_pickable_slugs when registered slugs are not in the curated subset.

3. Morpho Blue harness (Phase 3 first) following the v5 substrate:
   - sources/morpho/repo clone @ pinned git tag v1.x.y commit (record
     the sha in the manifest).
   - native/morpho_blue.py exposing selectors(), signatures(),
     load_abi(), resolve_*() per the native/uniswap_v4.py template.
     Public surface = Morpho Blue core (Blue), MorphoBlueCoreLib,
     OracleLib, and IRM.
   - A Foundry stub foundry/test/MorphoBlueHarness.t.sol asserting
     bytecode size of Blue and MorphoBlueCoreLib on Ethereum mainnet.
   - semantic map --slug morpho_blue --repo sources/morpho/repo --kind lending
     → ≥ 50 concrete candidates promoted into
     data/security_results/knowledge/concrete_candidates.jsonl.
   - native mark --slug morpho_blue --status harness_built --contract-address
     0xBBBBBbbBBbBBBbbBBbBBBbbBBbBBbBBBbbbbBBBbBDD on Ethereum mainnet
     so the manifest records morpho_blue: harness_built.
   - Verified pool/account discovery on at least one Morpho Blue market
     (USDC/WETH or WETH/USDC) using the same JSON-RPC urllib-only path
     that the Uniswap v4 harness uses.

4. Aave v3 (Phase 3 second) is left as a follow-up — only sketch a
   "next-session plan" section in this handover; do not start it in this
   session.

5. Phase 4 refresh-14d rotation is left as an explicit follow-up task.
   Update the handover to call it out: the cron cycle should prioritize
   the program with the largest max_bounty_usd that has NOT been
   touched in 14 days AND has a populated concrete_candidates.jsonl
   (>=50) AND a non-missing native-harness entry. Today the rotation
   is implicit; the prior agent exposed the ranking math in
   bounty/native_picker.py so the next agent ships a
   rotation-enabled wrapper around pick_next_target.

6. Tests: add coverage for C6 (≥ 3 cases for ABI/IDL hash requirement)
   + the cron flip regression (≥ 1) + Morpho Blue harness roundtrip (≥ 4).
   Total ≥ 8 new tests, all no live RPC.

7. Pytest baseline at session end: ≥ 514 / 6 skipped.

8. Lab notebook — write
   data/security_results/lab_notebook/2026-06-XX-v5-c6-cron-morpho.md
   (named for the date you commit). Today's
   2026-06-18-v5-c3-pick-next-target.md lab entry stays as historical
   reference; do NOT delete it.

9. AUDIT.md — strike the C6 row from "not started" to "shipped"; add
   a Phase 3 row noting Morpho Blue harness build (Aave v3 still in a
   separate future row).

10. SPEC.md §3 baseline test count updated, plus a new Implementation
    Status line for C6 + Morpho Blue harness build.

11. CHANGELOG.md — add a 2026-06-XX entry titled
    "v5 fork_validation ABI/IDL bind + Morpho Blue harness start
    (audit C6 + Phase 3 row 1)".

12. Commit + push to main with the suggested message below.


---

## 5. Hard constraints — DO NOT violate

- Do NOT loosen submission_gates.py / evidence_grading.py /
  novel_gate.py / task_verifier.py. The gates are correct; you extend
  inputs only. If C6 needs an additional gate field
  (must_be_native_pinned=True or similar), add it as opt-in, not
  required-by-default.
- Do NOT touch the synthetic substrate.
  domain/attack_templates/*, core/hypothesis.py, parameter_spaces.py
  are kept for regression fixtures. C6 changes
  validation/fork_validation.py only — leaving the synthetic catalogue
  anchors in fork_validation.anchors as research-only fallback.
- Do NOT add new packages. No new pip deps. urllib and stdlib only.
- Do NOT remove existing tests. Keep test_pick_next_target_* and
  fork_validation regression tests green.
- Do NOT paste any ALCHEMY_API_KEY, ETHEREUM_RPC_URL, or private-key
  material into staged files. Canonical ABI addresses (USDC, WETH,
  PoolManager, StateView, Morpho Blue, Aave v3 PoolAddressesProvider)
  ARE OK and have been used since C1/C2.
- Do NOT edit nss-hipif-chain.sh (the pause gate stays the same). Test
  the cron flip semantics via the python runner directly; do not
  modify the shell bootstrap.
- prefer_full_registry=True flip is the cron side, not the picker side.
  The picker helper already supports it; the cron caller is what changes.

---

## 6. Detailed playbook

### Step 6.1 — validation/fork_validation._fork_candidate_set ABI/IDL bind

Read the function in full. Today it ranks candidates by severity and
keeps top_n for the fork binder; the change is: filter the top-N
candidates to those whose entrypoint carries a real ABI/IDL hash before
the binder runs. The exact predicate:

```python
def _has_native_bind(candidate_entry: dict[str, Any]) -> bool:
    """Audit C6 — return True if the candidate has an ABI or IDL hash.

    Solidity target (EVM): entrypoint.abi_signature_hash matches the
    4-byte selector or matches the full canonical signature hash.

    Anchor / Solana target: entrypoint.selector_or_discriminator is
    non-empty AND source_ref.commit is non-empty.
    """
    entrypoint = candidate_entry.get("entrypoint") or {}
    source_ref = candidate_entry.get("source_ref") or {}
    abi_hash = entrypoint.get("abi_signature_hash") or ""
    selector = entrypoint.get("selector_or_discriminator") or ""
    commit = source_ref.get("commit") or ""
    if abi_hash and len(abi_hash) == 10 and abi_hash.startswith("0x"):
        return True
    if len(abi_hash) == 66 and abi_hash.startswith("0x"):
        return True
    if selector and commit:
        return True
    return False


def _fork_candidate_set(
    eligible_topn: list[dict[str, Any]],
    *,
    top_n: int = 5,
    **kwargs,
) -> list[dict[str, Any]]:
    """Audit correction C6 — top-N binder requires ABI/IDL hash.

    Behaviour change: the severity-ranked top-N is filtered to entries
    with a real ABI or IDL bind. The legacy count of candidates is
    returned when nothing clears the gate so the binder can fall back
    to catalogue anchors (research-only) without losing compute.
    """
    bound = [c for c in eligible_topn if _has_native_bind(c)]
    if not bound:
        bound = eligible_topn  # fallback — research-only anchors
    return bound[: max(top_n, 1)]
```

Tests for C6 (>= 3):

- Solidity candidate with abi_signature_hash of length 10 accepts.
- Solidity candidate with no abi_signature_hash rejects.
- Anchor candidate with selector_or_discriminator + source_ref.commit
  accepts; either missing rejects.
- Severity-ranked binder returns the bound subset, not the severity
  subset, when the top-N lacks an ABI/IDL bind.

### Step 6.2 — Flip prefer_full_registry=True in the cron runner

Locate the call site in hermes/scripts/nss-hipif-chain-run.py inside
_run_full_chain that calls pick_next_target(...). Today it passes no
kwargs. Change to:

```python
pick_next_target(
    scan_report,
    state,
    prefer_full_registry=True,   # C5 wired at the cron layer
    raise_on_empty=False,        # cron is best-effort; the runner
                                  # should log + skip rather than crash
)
```

Add a single regression test:

- tests/test_cron_registry_flip.py — monkey-patch _run_full_chain and
  assert it calls pick_next_target(..., prefer_full_registry=True)
  at least once. Use mock for the pipeline; no live RPC.

### Step 6.3 — Morpho Blue harness (Phase 3, target 1)

Template = src/night_shift_security/native/uniswap_v4.py. Steps:

1. Clone
   ```bash
   git clone https://github.com/morpho-org/morpho-blue sources/morpho/repo
   git -C sources/morpho/repo checkout <pinned-tag-commit-sha>
   ```
   Pin to the latest audit-friendly release tag (likely v1.0.0 or
   v1.1.x); record the sha in the native-harness manifest.

2. Selectors (canonical Keccak-256 via crypto/__init__.py)
   - MorphoBlue.createMarket((address,address,address,address,uint256))
   - MorphoBlue.supply((address,address,address,uint256,uint256,uint256,address))
   - MorphoBlue.borrow((address,address,address,uint256,uint256,address))
   - MorphoBlue.withdraw((address,address,address,uint256,uint256,address))
   - MorphoBlue.claim(address,address,address,uint256)
   - MorphoBlue.flashLoan(address,address,uint256,bytes)

3. native/morpho_blue.py mirroring the native/uniswap_v4.py shape:
   selectors(), signatures(), load_abi(), resolve_market(), Market,
   MarketResolution. Use stdlib + urllib only.

4. Foundry stub — foundry/test/MorphoBlueHarness.t.sol. Hard-code
   the canonical address(es); assert bytecode size; compile
   forge build --force. Optional fork_test requires ETHEREUM_RPC_URL;
   mark with vm.createSelectFork and document skip semantics when
   the env is unset.

5. Semantic recon
   ```bash
   .venv/bin/python -m night_shift_security.cli.main semantic map \
     --slug morpho_blue --repo sources/morpho/repo --kind lending
   ```
   Promote ≥ 50 concrete candidates into
   data/security_results/knowledge/concrete_candidates.jsonl.

6. native mark
   ```bash
   .venv/bin/python -m night_shift_security.cli.main native mark \
     --slug morpho_blue --status harness_built \
     --contract-address <MorphoBlue address> \
     --source-commit <pinned sha>
   ```

7. Tests (>= 4): selector/Keccak parity, signature hash, market
   resolution against at least one known market (id from Morpho Blue
   subgraph or via morpholink URL), abi loader returns the expected
   function set, Foundry stub parity.

### Step 6.4 — Aave v3 (Phase 3, target 2) — sketch only

Document the next-agent contract for Aave v3 in the lab notebook's
"Next session" section:

- native/aave_v3.py skeleton follows uniswap_v4.py + morpho_blue.py.
- Targets: PoolAddressesProvider, Pool, PoolConfigurator, AaveOracle,
  AToken, StableDebtToken, VariableDebtToken.
- Test stubs: foundry/test/AaveV3Harness.t.sol; selector coverage for
  supply/deposit, borrow, repay, withdraw, flashLoan, liquidationCall.
- Roadmap triggers: ≥ 50 concrete candidates, source commit pin, then
  native mark --status harness_built --source-commit <sha>.

The next-session agent runs semantic map + recorded_addresses; this
session does NOT start it.

### Step 6.5 — Phase 4 refresh-14d rotation (explicit follow-up task)

Update the hand-over section (this very document's "Next session"
section) with the rotation contract. The implementation lives behind
phase4_rotation_enabled (default off). Document and stop there.

```python
def rotate_target(state: dict[str, Any], slug: str, *, now: datetime) -> None:
    """Phase 4 — record when a slug was last touched so the rotation ranker
    correctly floats cold programs to the top."""
    state.setdefault("last_touched", {})[slug] = now.isoformat()


def pick_next_target_v6_phase4(...):
    """Phase 4 ranker — candidates float by bounty-size AND coldness."""
    ...
```

### Step 6.6 — Tests + verification

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/test_api.py -q
```

Pre-pickup: 506 / 6 skipped. Post-pickup: ≥ 514 / 6 skipped.

Test files (minimum):

- tests/test_fork_validation_abi_idl.py — 4 cases.
- tests/test_cron_registry_flip.py — 1 case.
- tests/test_native_morpho_blue.py — 4 cases.

Use synthetic fixtures; do not depend on live RPC. No external network
calls in tests/ paths except when guarded by
pytest.importorskip("urllib.request") and a cached subprocess.

### Step 6.7 — Verify cron resume semantics

The 04:00 cron is already resumed because ready_count=1. After this
session the resume semantics are unchanged; the flip of
prefer_full_registry=True is what changes. Verify by smoke running:

```bash
NSS_HIPIF_MODE=dryrun NSS_HIPIF_PAUSE_FOR_NATIVE=0 \
  timeout 60 bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -12
```

You should see one new line stating the chain now iterates the live
registry; the pause gate still asserts ready_count>=1 before the chain
proceeds, so quiet output is fine.

### Step 6.8 — Lab notebook + commit + push

Lab entry: data/security_results/lab_notebook/2026-06-XX-v5-c6-cron-morpho.md
(this file's new home — it replaces the c3 handover in working tree).

Update AUDIT.md / SPEC.md / CHANGELOG.md as in section 4 above.

```bash
git status --porcelain
git add -A
git diff --cached | grep -E "API_KEY|SECRET|TOKEN|PRIVATE_KEY" || echo "no secrets staged"
git commit -m "SPEC 5.0.0 fork_validation ABI/IDL bind + Morpho Blue harness start (audit C6 + Phase 3 row 1)"
git push origin main
```

Droid-Shield may flag canonical mainnet addresses — those are public
addresses and intentional. If the in-tool commit refuses, run git
commit from the user's terminal with the same message.


---

## 7. Anti-patterns to avoid

- Weakening C6 by leaving severity as a tiebreak — audit explicitly
  targets severity-only as the kernel of D8. The new binder must
  enforce hash presence first; severity breaks ties only among hashes.
- Wiring prefer_full_registry=True into the picker signature change —
  the flag already exists; the cron side is the only thing that
  needs to flip. Touching the picker signature invalidates every test
  in tests/test_pick_next_target.py and tests/test_full_registry_walk.py.
- Adding Morpho Blue v2 / vault protocols to the same harness — each
  protocol gets its own harness file; mixing them keeps the manifest
  opaque and the next agent cannot grep for it.
- Loosening qualifies_for_submission() to fast-track Morpho after
  harness build — forbidden. Morpho Blue will earn submit-ready the
  same way Uniswap v4 must: real on-chain delta captured against
  live state.
- Hard-coding slugs in _run_full_chain — defeats C5 (full registry).
  The whole point of the cron flip is to let the registry walker
  discover cold programs.
- Marking Morpho Blue as ready without a measured delta — ready is
  gated by audit C2's contract: a positive measured_impact_oracle.v1
  delta. harness_built is the correct status at session end.
- Running the chain past Phase 4 — Phase 4 is a separate follow-up;
  this session stops at the rotation-handed-off milestone.

---

## 8. Checklists

### Opening (5 min)

- [ ] git status --porcelain clean except two user-owned notes
- [ ] git log --oneline -3 shows 415d057 + today's lab commit
- [ ] head SPEC.md → 5.0.0-draft
- [ ] pytest tests/ --ignore=tests/test_api.py -q → 506 passed, 6 skipped
- [ ] native status → uniswap_v4: ready, ready_count=1
- [ ] find sources -maxdepth 2 -type d shows auditvault, kamino,
      uniswap_v4, wormhole (no morpho yet)
- [ ] Read validation/fork_validation.py once for top-N binder shape
- [ ] Read nss-hipif-chain-run.py for the pick_next_target caller

### Closing (10 min)

- [ ] pytest tests/ --ignore=tests/test_api.py -q → ≥ 514 / 6 skipped
- [ ] Cron smoke shows prefer_full_registry=True is wired at the runner
- [ ] native status lists uniswap_v4: ready AND morpho_blue: harness_built
- [ ] data/security_results/impact/ has a fresh morpho_blue_measured_delta.json
      (even with zero-delta envelope — harness_built only requires the record)
- [ ] Lab entry written, named 2026-06-XX-v5-c6-cron-morpho.md
- [ ] AUDIT.md / SPEC.md / CHANGELOG.md reflect C6 + Morpho Blue work
- [ ] git status --porcelain clean except user notes
- [ ] Push to origin main

---

## 9. Blockers playbook

- _has_native_bind falsifies every Solidity candidate: audit schema
  drift. Pickers today may use 10-char (0x + 8 hex) or 66-char
  (0x + 64 hex) selectors. Accept both, document.
- Morpho Blue source contract import errors: confirm git submodule
  update --init --recursive ran; pre-bake the selector set in
  native/morpho_blue.py via constants if submodules are network-blocked.
- Cron smoke flakily hangs: embedded pause-check involves git pull;
  wrap in timeout 60 bash … for inspection only.
- Aave v3 demands off-chain oracle aggregation — Phase 3 row 2,
  document and stop.
- ready_count drops to 0: do not edit the manifest from this session
  unless you also capture a fresh Morpho Blue measured delta.

---

## 10. Files this session is expected to touch

```
src/night_shift_security/validation/fork_validation.py   (C6 — _has_native_bind)
src/night_shift_security/native/morpho_blue.py           (new — Morpho harness)
hermes/scripts/nss-hipif-chain-run.py                    (prefer_full_registry=True flip)
foundry/test/MorphoBlueHarness.t.sol                     (new — Foundry stub)
tests/test_fork_validation_abi_idl.py                    (new — >=4 cases)
tests/test_cron_registry_flip.py                         (new — >=1 case)
tests/test_native_morpho_blue.py                         (new — >=4 cases)
sources/morpho/repo/                                     (gitignored clone)
data/security_results/lab_notebook/2026-06-XX-v5-c6-cron-morpho.md (new)
AUDIT.md                                                  (C6 row closed; Phase 3 row 1)
SPEC.md                                                   (§3 test count; new status line)
CHANGELOG.md                                              (2026-06-XX entry)
```

---

## 11. Final word

Stay narrow. Ship C6 + cron flip + Morpho Blue harness start (three
mandatory items). Leave Aave v3 as a Phase 3 row 2 sketch and the
refresh-14d rotation as an explicit Phase 4 follow-up.

The minimum-viable-v5 has now been crossed (C2's ready). The next
five harnesses will only land with the discipline the audit mandates:
one protocol at a time, one measured delta per pass, no gate loosened.
The Morpho Blue harness is where the next delta will be captured —
the parallel-IRM mismatch plus the oracle-binding aggregator gap that
Aave v3 also relies on, both of which are large enough to deserve a
Phase 3 partner track.

If the session ends with no Morpho Blue value moving probe, that is
fine — ship C6 + the cron flip + harness build + audit bookkeeping and
let the next session capture the measured delta. A tight, real binder
with no live measurement beats a binder that claims measurement without
one.

### Suggested commit message (one line)

```
SPEC 5.0.0 fork_validation ABI/IDL bind + Morpho Blue harness start (audit C6 + Phase 3 row 1)
```

### Suggested commit message (descriptive)

```
SPEC 5.0.0 fork_validation ABI/IDL bind + Morpho Blue harness start (audit C6 + Phase 3 row 1)

- src/night_shift_security/validation/fork_validation.py: _has_native_bind
  accepts Solidity abi_signature_hash (10 or 66 chars) OR Solana
  selector+commit. _fork_candidate_set filters severity-ranked top-N by
  _has_native_bind before the binder runs; falls back to severity-only
  catalogue anchors for research output.
- hermes/scripts/nss-hipif-chain-run.py:_run_full_chain: prefer_full_registry=True
  is now passed to pick_next_target (C5 wired at the cron layer;
  picker helper unchanged).
- src/night_shift_security/native/morpho_blue.py: first per-target Morpho
  Blue harness mirroring the uniswap_v4 template. Public surface:
  selectors(), signatures(), load_abi(), resolve_market(), Market,
  MarketResolution.
- foundry/test/MorphoBlueHarness.t.sol: Foundry stub asserting bytecode
  size on Ethereum mainnet; forge build --force compiles without remappings.
- sources/morpho/repo: pinned-source clone at the recorded sha
  (gitignored under sources/).
- tests: test_fork_validation_abi_idl.py (4), test_cron_registry_flip.py (1),
  test_native_morpho_blue.py (4).
- AUDIT.md: C6 row closed, Phase 3 row 1 added.
- SPEC.md §3 test count updated; new Implementation Status line for C6 + Morpho.
- CHANGELOG.md: 2026-06-XX entry added.
- TESTS: 514 passed, 6 skipped (was 506 / 6).
- Native manifest still uniswap_v4: ready, ready_count=1; morpho_blue
  joined at harness_built.
```
