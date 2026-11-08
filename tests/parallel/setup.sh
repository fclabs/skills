#!/usr/bin/env bash
# setup.sh <dir>: create a fresh scratch git repo holding the tinyshop fixture.
# Exit 0 on success, 2 on usage errors/refusals (nothing is changed then).
set -euo pipefail

usage() { echo "usage: setup.sh <dir>" >&2; exit 2; }

[ "$#" -eq 1 ] && [ -n "$1" ] || usage
DIR=$1

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$HERE/../.." && pwd -P)
SKILLS_DIR=$REPO_ROOT/skills
FIXTURE_DIR=$HERE/fixture

# --- refusals: all checks run before anything is created -------------------
if [ -e "$DIR" ] || [ -L "$DIR" ]; then
  [ -d "$DIR" ] || { echo "setup.sh: $DIR exists and is not a directory" >&2; exit 2; }
  if [ -n "$(ls -A "$DIR")" ]; then
    echo "setup.sh: $DIR is not empty" >&2; exit 2
  fi
  ANCESTOR=$DIR
else
  ANCESTOR=$(dirname "$DIR")
  while [ ! -d "$ANCESTOR" ]; do
    if [ -e "$ANCESTOR" ]; then
      echo "setup.sh: $ANCESTOR is not a directory" >&2; exit 2
    fi
    ANCESTOR=$(dirname "$ANCESTOR")
  done
fi
if [ "$(git -C "$ANCESTOR" rev-parse --is-inside-work-tree 2>/dev/null || true)" = "true" ]; then
  echo "setup.sh: $DIR is inside a git work tree" >&2; exit 2
fi
if [ ! -d "$SKILLS_DIR" ] || [ ! -f "$FIXTURE_DIR/tinyshop-spec.md" ]; then
  echo "setup.sh: skills or fixture directory missing under $REPO_ROOT" >&2; exit 2
fi

# --- build ------------------------------------------------------------------
CREATED=0
[ -d "$DIR" ] || CREATED=1
ABS=""
cleanup() {
  # Failure after creation: leave nothing behind.
  if [ -n "$ABS" ] && [ -d "$ABS" ]; then
    if [ "$CREATED" -eq 1 ]; then
      rm -rf "$ABS"
    else
      find "$ABS" -mindepth 1 -delete
    fi
  fi
}
trap 'cleanup' ERR

mkdir -p "$DIR"
ABS=$(cd "$DIR" && pwd -P)
cd "$ABS"

git init -q -b main
git config user.name harness
git config user.email harness@example.invalid

mkdir -p specs .claude/skills
cp "$FIXTURE_DIR/tinyshop-spec.md" specs/tinyshop-spec.md
echo READY > READY.md

for s in "$SKILLS_DIR"/*/; do
  ln -s "${s%/}" ".claude/skills/$(basename "$s")"
done

ESC=$(printf '%s' "$ABS" | sed -e 's/[\\&|]/\\&/g')
for t in "$FIXTURE_DIR"/*.md.tmpl; do
  out=$(basename "$t" .tmpl)
  sed -e "s|@DIR@|$ESC|g" "$t" > "$out"
done

printf '%s\n' '__pycache__/' '.claude/worktrees/' > .gitignore

git add -A
git -c commit.gpgsign=false commit -q --no-verify -m "Initial scratch repo"
trap - ERR
