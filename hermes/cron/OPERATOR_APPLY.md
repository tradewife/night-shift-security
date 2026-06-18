# Hermes cron — operator apply (v5 Phase 6+)

Apply after Phase 6 lands in `main`. Documents the live `nightsoul` profile state.

## Prerequisites

```bash
cd /home/kt/projects/rtp/night-shift-security
git pull
bash hermes/install-nightsoul-overlay.sh
hermes --profile nightsoul doctor
```

## 1. Script timeout (required)

The HIPIF chain runs 60–150+ minutes. Hermes defaults to 120s and kills the job.

```bash
hermes --profile nightsoul config set cron.script_timeout_seconds 10800
```

Verify: `grep script_timeout_seconds ~/.hermes/profiles/nightsoul/config.yaml` → `10800`.

## 2. Production environment (repo `.env`)

Add to `/home/kt/projects/rtp/night-shift-security/.env` (gitignored):

```bash
NSS_HIPIF_PAUSE_FOR_NATIVE=0
NSS_PHASE4_ROTATION_ENABLED=1
NSS_HIPIF_MODE=deterministic
NSS_HIPIF_BOUNTY_DEPTH=1
NSS_KLEND_FIXTURE=0
HERMES_CRON_SCRIPT_TIMEOUT=10800
NSS_PREFER_SOLANA=1
NSS_DISCOVERY_MISSING_PCT=0.8
```

`nss-hipif-chain.sh` sources repo `.env` on every run.

## 3. Cron job (nss-hipif-chain)

```bash
hermes --profile nightsoul cron list
# Job ID: 343324bfcbb2 (verify on your machine)

hermes --profile nightsoul cron edit 343324bfcbb2 \
  --no-agent \
  --clear-skills \
  --script nss-hipif-chain.sh \
  --prompt ""
```

Expected `cron list` line:

- Mode: `no-agent`
- Script: `nss-hipif-chain.sh`
- Workdir: `/home/kt/projects/rtp/night-shift-security`

## 4. Dryrun verification

```bash
cd /home/kt/projects/rtp/night-shift-security
NSS_HIPIF_MODE=dryrun bash hermes/scripts/nss-hipif-chain.sh 2>&1 | head -6
```

Must show:

- `pause_for_native=0`
- `bounty_depth=1`
- `script_timeout=10800`

## 5. Native harness precondition

Cron runs only when `native_harness_status.json` has `ready_count ≥ 1`.  
Phase 6+optional (2026-06-19): `ready_count=7` — `uniswap_v4`, `aave_v3`, `morpho_blue`, `kamino`, `jito`, `raydium`, `orca`.

```bash
.venv/bin/python -m night_shift_security.cli.main native status
```

## 6. Re-sync after repo updates

After `git pull` changes `hermes/scripts/`:

```bash
bash hermes/install-nightsoul-overlay.sh
```

Do **not** hand-edit `~/.hermes/profiles/nightsoul/scripts/nss-hipif-chain.sh` — overlay install overwrites it.

## Applied (2026-06-19)

| Step | Status |
|------|--------|
| `install-nightsoul-overlay.sh` | done |
| `cron.script_timeout_seconds=10800` | done |
| `.env` production NSS vars | done |
| `cron edit 343324bfcbb2` no-agent | done |
| Dryrun `pause_for_native=0` | verified |

Next scheduled run: `hermes --profile nightsoul cron list` → `nss-hipif-chain` next_run_at.