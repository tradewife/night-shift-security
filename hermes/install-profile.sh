#!/usr/bin/env bash
# Install Night Shift Security Hermes profile (night-shift).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_ROOT="${HERMES_ROOT:-$HOME/.hermes}"
PROFILE_NAME="night-shift"
PROFILE_DIR="$HERMES_ROOT/profiles/$PROFILE_NAME"
GROK_AUTH="$HOME/.grok/auth.json"

echo "==> Night Shift Hermes profile install"
echo "    repo:    $REPO"
echo "    profile: $PROFILE_DIR"

if ! command -v hermes >/dev/null 2>&1; then
  echo "ERROR: hermes CLI not found. Install from https://github.com/NousResearch/hermes-agent" >&2
  exit 1
fi

if [ ! -f "$GROK_AUTH" ]; then
  echo "WARN: $GROK_AUTH missing — run Grok/Hermes OAuth login before cron jobs." >&2
fi

if [ ! -d "$PROFILE_DIR" ]; then
  echo "==> Creating profile $PROFILE_NAME"
  hermes profile create "$PROFILE_NAME" --no-skills --no-alias \
    --description "Night Shift Security — adversarial research orchestration (NSS-only)"
fi

mkdir -p "$PROFILE_DIR/skills" "$PROFILE_DIR/scripts" "$PROFILE_DIR/cron" "$PROFILE_DIR/memories"

echo "==> Linking SOUL.md"
ln -sfn "$REPO/hermes/SOUL.md" "$PROFILE_DIR/SOUL.md"

echo "==> Seeding lab notebook memory"
if [ ! -f "$PROFILE_DIR/memories/MEMORY.md" ]; then
  cp "$REPO/hermes/MEMORY.seed.md" "$PROFILE_DIR/memories/MEMORY.md"
else
  echo "    (keeping existing memories/MEMORY.md)"
fi

echo "==> Installing config.yaml"
if [ ! -f "$PROFILE_DIR/config.yaml" ]; then
  cp "$REPO/hermes/config.yaml.template" "$PROFILE_DIR/config.yaml"
else
  echo "    (keeping existing config.yaml — compare with hermes/config.yaml.template)"
fi

echo "==> Linking Grok OAuth"
if [ -f "$GROK_AUTH" ]; then
  ln -sfn "$GROK_AUTH" "$PROFILE_DIR/auth.json"
else
  echo "    skipped auth.json symlink (no Grok OAuth yet)"
fi

echo "==> Installing skills"
for skill_dir in "$REPO"/hermes/skills/*/; do
  name="$(basename "$skill_dir")"
  ln -sfn "$skill_dir" "$PROFILE_DIR/skills/$name"
  echo "    skills/$name"
done

echo "==> Installing cron scripts"
for script in "$REPO"/hermes/scripts/*.sh; do
  base="$(basename "$script")"
  install -m 755 "$script" "$PROFILE_DIR/scripts/$base"
  echo "    scripts/$base"
done

mkdir -p "$REPO/data/security_results/hermes_proposals"

echo ""
echo "Done. Next steps:"
echo "  hermes --profile $PROFILE_NAME doctor"
echo "  cd $REPO && hermes --profile $PROFILE_NAME"
echo "  See hermes/cron/jobs.example.yaml for cron recipes"