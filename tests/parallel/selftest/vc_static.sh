#!/usr/bin/env bash
# selftest/vc_static.sh [--pre-live] [--runlog FILE]
# Static and stub-driven VC checks (VC-021 static clauses, accept.sh offline behaviour VC-024) and the
# invocation of the other offline suites (VC-001/002 vc_setup.sh, VC-018 vc_runscenario.sh, and
# selftest/run.sh for the VC-017 / VC-020 cases).
#   --pre-live     tolerate `TBD` in the README's `claude --version:` and `model:` lines (live values are
#                  recorded after the real runs); without it TBD fails.
#   --runlog FILE  output of an earlier `selftest/run.sh` run (accept.sh passes it to avoid a second run);
#                  without it selftest/run.sh is run here.
# Prints "PASS <name>" or "FAIL <name>: <reason>" per check, then a summary; exit 0 only if all pass.
# Nothing is written to the skills repository or $HOME/.cache; the real `claude` is never run.
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
H=$(cd "$HERE/.." && pwd -P)
REPO_ROOT=$(cd "$H/../.." && pwd -P)
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0

PRE_LIVE=0
RUNLOG=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --pre-live) PRE_LIVE=1 ;;
    --runlog) shift; RUNLOG=${1:-} ;;
    *) echo "usage: vc_static.sh [--pre-live] [--runlog FILE]" >&2; exit 2 ;;
  esac
  shift
done

T=$(mktemp -d "${TMPDIR:-/tmp}/vc_static.XXXXXX") || { echo "cannot create temp dir" >&2; exit 1; }
T=$(cd "$T" && pwd -P)
trap 'rm -rf "$T"' EXIT

FAILS=0
TOTAL=0
pass() { TOTAL=$((TOTAL + 1)); echo "PASS $1"; }
fail() { TOTAL=$((TOTAL + 1)); FAILS=$((FAILS + 1)); echo "FAIL $1: $2"; }

RS=$H/run_scenario.sh
README=$H/README.md

source_files() { find "$H" -type f \( -name '*.sh' -o -name '*.py' \) -not -path '*/__pycache__/*' | sort; }

# ---------------------------------------------------------------- VC-021: bypass flag absent
P='dangerously''-skip'
HITS=$(source_files | xargs grep -l -- "$P" 2>/dev/null || true)
if [ -z "$HITS" ]; then pass "VC-021 bypass flag absent from *.sh and *.py"
else fail "VC-021 bypass flag" "found in: $HITS"; fi

# ---------------------------------------------------------------- VC-021: constants and flag usage
CONST_OK=1
for line in 'TIMEOUT_S=1800' 'BUDGET_USD=10' 'MODEL=claude-sonnet-5-5'; do
  grep -qxF -- "$line" "$RS" || { CONST_OK=0; fail "VC-021 constant" "run_scenario.sh lacks the line $line"; }
done
grep -qE '^ALLOWED_TOOLS="[^"]+"$' "$RS" || { CONST_OK=0; fail "VC-021 constant" "run_scenario.sh lacks ALLOWED_TOOLS=\"...\""; }
[ "$CONST_OK" -eq 1 ] && pass "VC-021 constants TIMEOUT_S, BUDGET_USD, MODEL, ALLOWED_TOOLS defined"

USE_OK=1
for s in 'timeout "$TIMEOUT_S"' '--max-budget-usd "$BUDGET_USD"' '--permission-mode acceptEdits' '--allowedTools "$ALLOWED_TOOLS"' '--model "$MODEL"'; do
  grep -qF -- "$s" "$RS" || { USE_OK=0; fail "VC-021 flag usage" "run_scenario.sh does not use: $s"; }
done
[ "$USE_OK" -eq 1 ] && pass "VC-021 constants used with timeout, --max-budget-usd, --permission-mode acceptEdits, --allowedTools, --model"

ALLOWED=$(sed -n -E 's/^ALLOWED_TOOLS="(.*)"$/\1/p' "$RS")
D4_OK=1
for t in Skill SendMessage Agent Read Write Edit Glob Grep 'Bash(git:*)' 'Bash(python:*)' 'Bash(python3:*)' 'Bash(mkdir:*)' \
         'Bash(ls:*)' 'Bash(cat:*)' 'Bash(cp:*)' 'Bash(mv:*)' 'Bash(rm:*)' 'Bash(touch:*)'; do
  case " $ALLOWED " in *" $t "*) ;; *) D4_OK=0; fail "VC-021 ALLOWED_TOOLS" "lacks $t (spec D4)" ;; esac
done
[ "$D4_OK" -eq 1 ] && pass "VC-021 ALLOWED_TOOLS contains every tool of spec D4"

# ---------------------------------------------------------------- VC-021: directory-creation words confined
PAT='mkdir|makedirs|mkdtemp'
BAD=""
for f in $(source_files | xargs grep -lE "$PAT" 2>/dev/null || true); do
  rel=${f#"$H"/}
  case "$rel" in
    setup.sh|run_scenario.sh|check_run.py|selftest/*) ;;
    *) BAD="$BAD $rel" ;;
  esac
done
if [ -z "$BAD" ]; then pass "VC-021 mkdir/makedirs/mkdtemp only in setup.sh, run_scenario.sh, check_run.py, selftest/"
else fail "VC-021 directory-creation words" "found in:$BAD"; fi
grep -n tempfile "$H/check_run.py" >/dev/null 2>&1 \
  && pass "VC-021 check_run.py documents its tempfile copy" \
  || fail "VC-021 tempfile" "check_run.py has no tempfile copy"

# ---------------------------------------------------------------- VC-021: README content
if [ ! -f "$README" ]; then
  fail "VC-021 README" "README.md not found"
else
  R_OK=1
  grep -qE '(git|Git).{0,20}(>=|≥).{0,3}2\.28' "$README" || { R_OK=0; fail "VC-021 README" "does not list git >= 2.28"; }
  grep -qE '(Python|python).{0,20}(>=|≥).{0,3}3\.11' "$README" || { R_OK=0; fail "VC-021 README" "does not list Python >= 3.11"; }
  grep -qi 'coreutils' "$README" || { R_OK=0; fail "VC-021 README" "does not mention GNU coreutils"; }
  grep -qF -- "$ALLOWED" "$README" || { R_OK=0; fail "VC-021 README" "does not list ALLOWED_TOOLS exactly as run_scenario.sh"; }
  grep -qF -- "claude-sonnet-5-5" "$README" || { R_OK=0; fail "VC-021 README" "does not state the model constant"; }
  for key in 'claude --version' 'model'; do
    val=$(sed -n -E "s/^${key}: (.+)$/\\1/p" "$README" | head -n 1)
    if [ -z "$val" ]; then
      R_OK=0; fail "VC-021 README" "no line '${key}: <value>'"
    elif [ "$val" = TBD ] && [ "$PRE_LIVE" -eq 0 ]; then
      R_OK=0; fail "VC-021 README" "line '${key}: TBD' (record the live value, or run with --pre-live)"
    fi
  done
  [ "$R_OK" -eq 1 ] && pass "VC-021 README lists git >= 2.28, Python >= 3.11, GNU coreutils, ALLOWED_TOOLS, claude --version and model lines"
  H_OK=1
  for h in 'Purpose' 'Prerequisites' 'Running the scenarios' 'Prompts' 'Directory layout' 'Reading the results' \
           'Fixture review (VC-023)' 'Cost' 'Calibrating the constants' 'Model' 'Recorded results' 'Not covered' \
           'Reading a red result' 'Offline checks'; do
    [ "$(grep -c -- "^## $h\$" "$README")" -eq 1 ] || { H_OK=0; fail "README heading" "missing section '## $h'"; }
  done
  [ "$H_OK" -eq 1 ] && pass "README has every required section"
fi

# ---------------------------------------------------------------- VC-021: checkers leave repositories unchanged
mkdir "$T/cases"
if python3 "$HERE/make_cases.py" "$T/cases" >/dev/null 2>&1; then
  CASE=$(ls -d "$T/cases"/s2-good-* 2>/dev/null | head -n 1)
  if [ -n "$CASE" ] && [ -d "$CASE/repo" ]; then
    S_BEFORE=$(git -C "$CASE/repo" status --porcelain)
    K_BEFORE=$(git -C "$REPO_ROOT" status --porcelain)
    CMD=$(python3 - "$CASE" "$H" <<'PY'
import json, shlex, sys
from pathlib import Path
case, h = Path(sys.argv[1]), sys.argv[2]
exp = json.loads((case / "expect.json").read_text())
print(shlex.join(["python3", f"{h}/{exp['checker']}", *exp["args"]]))
PY
)
    (cd "$CASE" && eval "$CMD" >/dev/null 2>&1)
    RC=$?
    S_AFTER=$(git -C "$CASE/repo" status --porcelain)
    K_AFTER=$(git -C "$REPO_ROOT" status --porcelain)
    if [ "$RC" -ne 0 ]; then fail "VC-021 checker run" "checker exited $RC on $(basename "$CASE")"
    elif [ "$S_BEFORE" != "$S_AFTER" ]; then fail "VC-021 scratch repo status" "changed by a checker run"
    elif [ "$K_BEFORE" != "$K_AFTER" ]; then fail "VC-021 skills repo status" "changed by a checker run"
    elif [ -n "$(find "$CASE/repo" -name __pycache__ 2>/dev/null)" ]; then fail "VC-021 checker run" "left __pycache__ in the scratch repo"
    else pass "VC-021 git status --porcelain unchanged in the scratch repo and the skills repo after a checker run"; fi
  else
    fail "VC-021 checker run" "no s2-good-* case with a repo was built"
  fi
else
  fail "VC-021 checker run" "make_cases.py failed"
fi

# ---------------------------------------------------------------- VC-024: accept.sh offline behaviour
ACC=$H/accept.sh
FIX_HASH=$( (command -v sha256sum >/dev/null 2>&1 && sha256sum "$H/fixture/tinyshop-spec.md" || shasum -a 256 "$H/fixture/tinyshop-spec.md") | cut -d' ' -f1)

mkres() {  # mkres <dir> [plan-count] : 3 passing files per scenario, <plan-count> for plan
  local d=$1 pc=${2:-3} s k n
  mkdir -p "$d"
  for s in plan full downgrade failing-member; do
    n=3; [ "$s" = plan ] && n=$pc
    for k in $(seq 1 "$n"); do
      printf '{"scenario":"%s","run":%s,"passed":true,"violations":[],"notes":[],"model":"m"}\n' "$s" "$k" > "$d/$s-$k.json"
    done
  done
}
mkreadme() {  # mkreadme <file> <22a> <22b> <23-hash-or-empty>
  {
    echo "$2"; echo "$3"
    [ -n "$4" ] && echo "VC-023: READY sha256=$4" || echo "VC-023: TBD"
    echo "claude --version: 1.2.3"; echo "model: claude-sonnet-5-5"
  } > "$1"
}
acc() {  # acc <readme> <resdir> [flags...] : runs accept.sh with the suites skipped
  local r=$1 d=$2; shift 2
  ACCEPT_README=$r ACCEPT_NO_SUITES=1 bash "$ACC" "$@" "$d" 2>&1
}

mkres "$T/res-ok"
mkres "$T/res-two" 2
mkreadme "$T/readme-ok" "VC-022a: PASS" "VC-022b: FAIL" "$FIX_HASH"
mkreadme "$T/readme-tbd" "VC-022a: TBD" "VC-022b: TBD" ""
mkreadme "$T/readme-badhash" "VC-022a: PASS" "VC-022b: PASS" "$(printf '0%.0s' $(seq 1 64))"
mkreadme "$T/readme-22a-fail" "VC-022a: FAIL" "VC-022b: PASS" "$FIX_HASH"
mkres "$T/res-empty-viol"
printf '{"scenario":"full","run":2,"passed":false,"violations":[],"notes":[],"model":"m"}\n' > "$T/res-empty-viol/full-2.json"
mkres "$T/res-red"
printf '{"scenario":"full","run":2,"passed":false,"violations":["VC-008"],"notes":[],"model":"m"}\n' > "$T/res-red/full-2.json"

OUT=$(acc "$T/readme-ok" "$T/res-ok"); RC=$?
if [ "$RC" -eq 0 ] && ! printf '%s' "$OUT" | grep -q '^FAIL'; then pass "VC-024 accept.sh exits 0 on good README and 3 results per scenario (VC-022b FAIL accepted)"
else fail "VC-024 accept good" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-ok" "$T/res-red"); RC=$?
[ "$RC" -eq 0 ] && pass "VC-024 accept.sh accepts a red result with a non-empty violations list" || fail "VC-024 accept red" "exit $RC: $OUT"

OUT=$(acc "$T/readme-ok" "$T/res-two"); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'FAIL results: scenario plan has 2'; then pass "VC-024 accept.sh exits 1 naming 'plan' for a results dir with 2 plan files"
else fail "VC-024 accept two files" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-tbd" "$T/res-ok"); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'VC-022a' && printf '%s' "$OUT" | grep -q 'VC-023'; then pass "VC-024 accept.sh exits 1 for a README lacking the VC lines"
else fail "VC-024 accept README without VC lines" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-badhash" "$T/res-ok"); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'differs from the current fixture'; then pass "VC-024 accept.sh exits 1 when the VC-023 hash differs from the fixture"
else fail "VC-024 accept wrong hash" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-22a-fail" "$T/res-ok"); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'VC-022a'; then pass "VC-024 accept.sh exits 1 on VC-022a: FAIL"
else fail "VC-024 accept 22a FAIL" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-ok" "$T/res-empty-viol"); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$OUT" | grep -q 'full-2.json'; then pass "VC-024 accept.sh exits 1 for passed:false with empty violations"
else fail "VC-024 accept empty violations" "exit $RC: $OUT"; fi

OUT=$(acc "$T/readme-ok" "$T/does-not-exist"); RC=$?
[ "$RC" -eq 1 ] && pass "VC-024 accept.sh exits 1 for a missing results directory" || fail "VC-024 accept missing dir" "exit $RC: $OUT"

OUT=$(acc "$T/readme-tbd" "$T/res-two" --pre-live); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'SKIP README'; then pass "VC-024 --pre-live skips the README, VC-022/VC-023 and results checks"
else fail "VC-024 --pre-live" "exit $RC: $OUT"; fi

OUT=$(ACCEPT_NO_SUITES=1 bash "$ACC" --bogus 2>&1); RC=$?
[ "$RC" -eq 2 ] && pass "VC-024 accept.sh exits 2 on an unknown flag" || fail "VC-024 accept usage" "exit $RC: $OUT"

# ---------------------------------------------------------------- VC-001/002, VC-018 and run.sh (VC-017, VC-020)
OUT=$(bash "$HERE/vc_setup.sh" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'VC-001 PASS' && printf '%s' "$OUT" | grep -q 'VC-002 PASS'; then pass "VC-001, VC-002 (selftest/vc_setup.sh)"
else fail "VC-001/VC-002" "exit $RC: $(printf '%s' "$OUT" | tail -n 3)"; fi

OUT=$(bash "$HERE/vc_runscenario.sh" 2>&1); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'VC-018 PASS'; then pass "VC-018 (selftest/vc_runscenario.sh)"
else fail "VC-018" "exit $RC: $(printf '%s' "$OUT" | tail -n 3)"; fi

if [ -z "$RUNLOG" ]; then
  RUNLOG=$T/run.log
  bash "$HERE/run.sh" > "$RUNLOG" 2>&1 || fail "selftest/run.sh" "non-zero exit: $(grep -E '^FAIL ' "$RUNLOG" | head -n 3 | tr '\n' ' ')"
fi
if [ ! -f "$RUNLOG" ]; then
  fail "VC-017/VC-020 cases" "run log not found: $RUNLOG"
else
  C_OK=1
  for pfx in run-refuse-skills-repo run-refuse-uncommitted-plan run-nfr001-full-15-ok run-nfr001-full-16-fails run-nfr001-downgrade-6-ok run-nfr001-downgrade-7-fails run-nfr001-failing-member-6-ok run-nfr001-failing-member-7-fails; do
    grep -q "^PASS $pfx" "$RUNLOG" || { C_OK=0; fail "VC-017/VC-020 cases" "no PASS line for a case named $pfx*"; }
  done
  grep -Eq '^selftest: ([0-9]+)/\1 cases passed$' "$RUNLOG" || { C_OK=0; fail "VC-017/VC-020 cases" "run log lacks an all-passed summary"; }
  [ "$C_OK" -eq 1 ] && pass "VC-017 (checker half) and VC-020 cases ran and passed inside selftest/run.sh"
fi

echo "vc_static: $((TOTAL - FAILS))/$TOTAL checks passed"
[ "$FAILS" -eq 0 ]
