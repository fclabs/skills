#!/usr/bin/env bash
# accept.sh [--pre-live] [results-dir]      (spec D9 / VC-024)
# Harness acceptance. Exits 0 iff every check passes:
#   1. selftest/run.sh exits 0 (golden cases, includes the VC-017 / VC-020 cases)
#   2. selftest/vc_static.sh exits 0 (static and stub-driven VCs: 001, 002, 017, 018, 020, 021, accept.sh itself)
#   3. (live) README.md holds `VC-022a: PASS`, a `VC-022b: PASS|FAIL` line and `VC-023: READY sha256=<hash>`
#      whose hash equals the sha256 of fixture/tinyshop-spec.md
#   4. (live) results-dir holds <scenario>-<k>.json for k=1..3 for plan, full, downgrade, failing-member
#   5. (live) every result file with passed:false has a non-empty violations list
# results-dir defaults to $WORK/results; WORK defaults to $HOME/.cache/parallel-skills-test (as run_scenario.sh).
# --pre-live: run only checks 1 and 2 (the offline part) and tolerate `TBD` in the README's `claude --version:`
#             and `model:` lines; checks 3-5 are skipped and said to be.
# Exit codes: 0 accepted, 1 a check failed (the output names it), 2 usage error.
# Test hooks (used by selftest/vc_static.sh): ACCEPT_README=<file> replaces README.md;
#   ACCEPT_NO_SUITES=1 skips checks 1 and 2 (so the live checks can be tested quickly and without recursion).
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0

PRE_LIVE=0
RESULTS_ARG=""
for a in "$@"; do
  case "$a" in
    --pre-live) PRE_LIVE=1 ;;
    -*) echo "usage: accept.sh [--pre-live] [results-dir]" >&2; exit 2 ;;
    *) [ -z "$RESULTS_ARG" ] || { echo "usage: accept.sh [--pre-live] [results-dir]" >&2; exit 2; }
       RESULTS_ARG=$a ;;
  esac
done

WORK=${WORK:-$HOME/.cache/parallel-skills-test}
RESULTS=${RESULTS_ARG:-$WORK/results}
README=${ACCEPT_README:-$HERE/README.md}
FIXTURE=$HERE/fixture/tinyshop-spec.md

FAILS=0
pass() { echo "PASS $1"; }
fail() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# --- offline suites ---------------------------------------------------------------------------
if [ "${ACCEPT_NO_SUITES:-0}" = 1 ]; then
  echo "SKIP offline suites (ACCEPT_NO_SUITES=1)"
else
  RUNLOG=$(mktemp "${TMPDIR:-/tmp}/accept-run.XXXXXX") || { echo "cannot create a temp file" >&2; exit 2; }
  trap 'rm -f "$RUNLOG"' EXIT
  if bash "$HERE/selftest/run.sh" > "$RUNLOG" 2>&1; then
    pass "selftest/run.sh ($(tail -n 1 "$RUNLOG"))"
  else
    fail "selftest/run.sh" "non-zero exit; $(grep -E '^FAIL |selftest:' "$RUNLOG" | head -n 5 | tr '\n' ' ')"
  fi
  SARGS=(--runlog "$RUNLOG")
  [ "$PRE_LIVE" -eq 1 ] && SARGS+=(--pre-live)
  if bash "$HERE/selftest/vc_static.sh" "${SARGS[@]}"; then
    pass "selftest/vc_static.sh"
  else
    fail "selftest/vc_static.sh" "non-zero exit (see FAIL lines above)"
  fi
fi

# --- live checks --------------------------------------------------------------------------------
if [ "$PRE_LIVE" -eq 1 ]; then
  echo "SKIP README VC-022/VC-023 lines and results directory (--pre-live)"
else
  if [ ! -f "$README" ]; then
    fail "README" "not found: $README"
  else
    if grep -Eq '^[[:space:]]*(- )?VC-022a: PASS[[:space:]]*$' "$README"; then
      pass "README VC-022a: PASS"
    else
      fail "README VC-022a" "no line 'VC-022a: PASS'"
    fi
    if grep -Eq '^[[:space:]]*(- )?VC-022b: (PASS|FAIL)[[:space:]]*$' "$README"; then
      pass "README VC-022b line"
    else
      fail "README VC-022b" "no line 'VC-022b: PASS' or 'VC-022b: FAIL'"
    fi
    FIX_HASH=$(sha256_of "$FIXTURE")
    README_HASH=$(sed -n -E 's/^[[:space:]]*(- )?VC-023: READY sha256=([0-9a-f]{64})[[:space:]]*$/\2/p' "$README" | head -n 1)
    if [ -z "$README_HASH" ]; then
      fail "README VC-023" "no line 'VC-023: READY sha256=<hash>'"
    elif [ "$README_HASH" != "$FIX_HASH" ]; then
      fail "README VC-023" "hash $README_HASH differs from the current fixture ($FIX_HASH); re-run the review"
    else
      pass "README VC-023 hash matches the fixture"
    fi
  fi

  if [ ! -d "$RESULTS" ]; then
    fail "results" "directory not found: $RESULTS"
  else
    python3 - "$RESULTS" <<'PY'
import json, sys
from pathlib import Path

d = Path(sys.argv[1])
bad = 0
for s in ("plan", "full", "downgrade", "failing-member"):
    files = [d / f"{s}-{k}.json" for k in (1, 2, 3)]
    have = [f for f in files if f.is_file()]
    if len(have) != 3:
        missing = ", ".join(f.name for f in files if not f.is_file())
        print(f"FAIL results: scenario {s} has {len(have)} result files, expected 3 (missing {missing})")
        bad += 1
        continue
    print(f"PASS results: scenario {s} has 3 result files")
    for f in have:
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"FAIL results: {f.name} is not valid JSON ({e})")
            bad += 1
            continue
        if data.get("passed") is False and not data.get("violations"):
            print(f"FAIL results: {f.name} has passed:false and an empty violations list")
            bad += 1
sys.exit(1 if bad else 0)
PY
    [ "$?" -eq 0 ] || FAILS=$((FAILS + 1))
  fi
fi

if [ "$FAILS" -eq 0 ]; then
  echo "accept: OK"
  exit 0
fi
echo "accept: FAIL ($FAILS failing check(s))"
exit 1
