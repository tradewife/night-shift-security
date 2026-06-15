#!/usr/bin/env bash
# Install the Night Shift Security v4 overlay into the broader NightSoul profile.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_ROOT="${HERMES_ROOT:-$HOME/.hermes}"
PROFILE_NAME="${1:-nightsoul}"
PROFILE_DIR="$HERMES_ROOT/profiles/$PROFILE_NAME"
SOUL="$PROFILE_DIR/SOUL.md"
OVERLAY="$REPO/hermes/NIGHTSOUL_NSS_V4.md"
START="<!-- NSS_V4_OVERLAY_START -->"
END="<!-- NSS_V4_OVERLAY_END -->"

echo "==> Installing NSS v4 overlay"
echo "    repo:    $REPO"
echo "    profile: $PROFILE_DIR"

if [ ! -d "$PROFILE_DIR" ]; then
  echo "ERROR: Hermes profile not found: $PROFILE_DIR" >&2
  exit 1
fi

if [ ! -f "$SOUL" ]; then
  echo "ERROR: SOUL.md not found: $SOUL" >&2
  exit 1
fi

if [ ! -f "$OVERLAY" ]; then
  echo "ERROR: overlay not found: $OVERLAY" >&2
  exit 1
fi

mkdir -p "$PROFILE_DIR/skills" "$PROFILE_DIR/scripts" "$PROFILE_DIR/cron"

backup="$SOUL.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp "$SOUL" "$backup"
echo "==> Backed up SOUL.md to $backup"

tmp="$(mktemp)"
awk -v start="$START" -v end="$END" '
  $0 == start { skip = 1; next }
  $0 == end { skip = 0; next }
  skip != 1 { print }
' "$SOUL" > "$tmp"

{
  cat "$tmp"
  printf "\n%s\n" "$START"
  cat "$OVERLAY"
  printf "%s\n" "$END"
} > "$SOUL"
rm -f "$tmp"

echo "==> Linking NSS skills"
for skill_dir in "$REPO"/hermes/skills/*/; do
  name="$(basename "$skill_dir")"
  ln -sfn "$skill_dir" "$PROFILE_DIR/skills/$name"
  echo "    skills/$name"
done

echo "==> Installing NSS scripts"
for script in "$REPO"/hermes/scripts/*.sh; do
  base="$(basename "$script")"
  install -m 755 "$script" "$PROFILE_DIR/scripts/$base"
  echo "    scripts/$base"
done

echo "==> Installing NSS cron prompt copy"
install -m 644 "$REPO/hermes/cron/nss-hipif-chain.prompt.md" \
  "$PROFILE_DIR/cron/nss-hipif-chain.prompt.md"

echo ""
echo "Done. Verify with:"
echo "  hermes --profile $PROFILE_NAME doctor"
