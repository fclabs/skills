#!/usr/bin/env bash
# selftest/vc_setup.sh: verifies VC-001 and VC-002 against ../setup.sh.
# Prints "VC-001 PASS" / "VC-002 PASS", or "VC-00x FAIL: <reason>"; exits non-zero on any failure.
# Uses a temp parent under ${TMPDIR:-/tmp} (must be outside any git work tree) and removes it on exit.
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
SETUP=$HERE/../setup.sh

TMP_PARENT=$(mktemp -d "${TMPDIR:-/tmp}/vc_setup.XXXXXX") || { echo "cannot create temp dir" >&2; exit 1; }
TMP_PARENT=$(cd "$TMP_PARENT" && pwd -P)
trap 'rm -rf "$TMP_PARENT"' EXIT

if [ "$(git -C "$TMP_PARENT" rev-parse --is-inside-work-tree 2>/dev/null || true)" = "true" ]; then
  echo "temp parent $TMP_PARENT is inside a git work tree; set TMPDIR elsewhere" >&2
  exit 1
fi

FAILS=0
fail() { echo "$1 FAIL: $2"; FAILS=$((FAILS + 1)); VC_FAILED=1; }

# ---------------------------------------------------------------- VC-001
check_repo() {
  local d=$1 label=$2 rc out
  out=$("$SETUP" "$d" 2>&1); rc=$?
  [ "$rc" -eq 0 ] || { fail VC-001 "$label: setup.sh exit $rc ($out)"; return; }
  local abs
  abs=$(cd "$d" && pwd -P)

  [ "$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)" = main ] || fail VC-001 "$label: branch is not main"
  [ "$(git -C "$d" rev-list --count HEAD 2>/dev/null)" = 1 ] || fail VC-001 "$label: commit count is not 1"
  [ "$(git -C "$d" log -1 --format=%an 2>/dev/null)" = harness ] || fail VC-001 "$label: author is not harness"
  [ "$(git -C "$d" log -1 --format=%cn 2>/dev/null)" = harness ] || fail VC-001 "$label: committer is not harness"
  [ "$(git -C "$d" config --local user.name 2>/dev/null)" = harness ] || fail VC-001 "$label: local user.name"
  [ "$(git -C "$d" config --local user.email 2>/dev/null)" = harness@example.invalid ] || fail VC-001 "$label: local user.email"
  [ -z "$(git -C "$d" status --porcelain)" ] || fail VC-001 "$label: working tree not clean after setup"

  local f
  for f in READY.md specs/tinyshop-spec.md .gitignore .claude/skills/write-spec-plan/SKILL.md \
           bad-group-plan.md failing-member-plan.md smoke-group-plan.md; do
    [ -e "$d/$f" ] || fail VC-001 "$label: missing $f"
  done
  [ "$(cat "$d/READY.md" 2>/dev/null)" = READY ] || fail VC-001 "$label: READY.md is not the single line READY"
  [ "$(cat "$d/.gitignore" 2>/dev/null)" = "$(printf '__pycache__/\n.claude/worktrees/')" ] || fail VC-001 "$label: .gitignore content"
  [ -L "$d/.claude/skills/write-spec-plan" ] || fail VC-001 "$label: skills entry is not a symlink"

  for f in bad-group-plan.md failing-member-plan.md smoke-group-plan.md; do
    [ -f "$d/$f" ] || continue
    if grep -q '@DIR@' "$d/$f"; then fail VC-001 "$label: $f still contains @DIR@"; fi
    grep -qF "$abs" "$d/$f" || fail VC-001 "$label: $f never mentions $abs"
    local bad
    bad=$(awk -v abs="$abs" '{ for (i = 1; i <= NF; i++) { t = $i
             if (substr(t, 1, 1) == "/" && index(substr(t, 2), "/") > 0 && index(t, abs) != 1) print t } }' "$d/$f" | head -3)
    [ -z "$bad" ] || fail VC-001 "$label: $f has path token(s) outside $abs: $bad"
  done
}

VC_FAILED=0
mkdir "$TMP_PARENT/emptydir"
check_repo "$TMP_PARENT/emptydir" "empty dir"
check_repo "$TMP_PARENT/new/nested/dir" "nonexistent dir"
[ "$VC_FAILED" -eq 0 ] && echo "VC-001 PASS"

# ---------------------------------------------------------------- VC-002
VC_FAILED=0
expect2() {  # expect2 <label> <args...>: setup.sh must exit 2
  local label=$1 rc; shift
  "$SETUP" "$@" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 2 ] || fail VC-002 "$label: exit $rc, expected 2"
}

mkdir "$TMP_PARENT/nonempty"
echo data > "$TMP_PARENT/nonempty/file.txt"
before=$(ls -A "$TMP_PARENT/nonempty")
expect2 "non-empty dir" "$TMP_PARENT/nonempty"
[ "$(ls -A "$TMP_PARENT/nonempty")" = "$before" ] || fail VC-002 "non-empty dir: contents changed"

mkdir "$TMP_PARENT/outer"
git -C "$TMP_PARENT/outer" init -q -b main
mkdir "$TMP_PARENT/outer/sub"
expect2 "empty subdir of git repo" "$TMP_PARENT/outer/sub"
[ -z "$(ls -A "$TMP_PARENT/outer/sub")" ] || fail VC-002 "empty subdir of git repo: contents changed"
outer_before=$(find "$TMP_PARENT/outer" -path "$TMP_PARENT/outer/.git" -prune -o -print | sort)
expect2 "nonexistent subdir of git repo" "$TMP_PARENT/outer/newsub/deeper"
outer_after=$(find "$TMP_PARENT/outer" -path "$TMP_PARENT/outer/.git" -prune -o -print | sort)
[ "$outer_before" = "$outer_after" ] || fail VC-002 "nonexistent subdir of git repo: tree changed"

expect2 "no argument"
expect2 "empty argument" ""
expect2 "two arguments" "$TMP_PARENT/a" "$TMP_PARENT/b"
[ ! -e "$TMP_PARENT/a" ] || fail VC-002 "two arguments: directory created"

[ "$VC_FAILED" -eq 0 ] && echo "VC-002 PASS"

[ "$FAILS" -eq 0 ]
