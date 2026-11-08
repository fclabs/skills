#!/usr/bin/env bash
# run_scenario.sh <scenario> <k> [--force]
#   scenario: plan | full | downgrade | failing-member | smoke
# Runs one headless Claude Code session in a scratch repo, calls the checker,
# maps the exit codes (spec D8, D10, D13) and, after a passing S1, commits the plan.
# Exit: 0 once a result is written (any verdict; smoke: once its transcript is written),
#       1 if a smoke run crashes/times out/is budget-killed, 2 for usage errors or refusals.
# Env overrides: WORK, CLAUDE_BIN, CHECK_PLAN, CHECK_RUN, PROMPT_FORM (slash|skill).
# --mark-failed and --summary always use the real check_run.py.
set -uo pipefail

# --- constants (provisional until a full S2 run is measured; see README) ----------
TIMEOUT_S=1800
BUDGET_USD=10
MODEL=claude-sonnet-5-5
ALLOWED_TOOLS="Skill SendMessage Agent Read Write Edit Glob Grep Bash(git:*) Bash(python:*) Bash(python3:*) Bash(mkdir:*) Bash(ls:*) Bash(cat:*) Bash(cp:*) Bash(mv:*) Bash(rm:*) Bash(touch:*)"

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=$(cd "$HERE/../.." && pwd -P)
export GIT_OPTIONAL_LOCKS=0
export PYTHONDONTWRITEBYTECODE=1

usage() {
  echo "usage: run_scenario.sh <plan|full|downgrade|failing-member|smoke> <k> [--force]" >&2
  exit 2
}
refuse() { echo "run_scenario.sh: $*" >&2; exit 2; }

# --- arguments ----------------------------------------------------------------------
[ "$#" -ge 2 ] && [ "$#" -le 3 ] || usage
SCENARIO=$1
K=$2
FORCE=0
if [ "$#" -eq 3 ]; then
  [ "$3" = "--force" ] || usage
  FORCE=1
fi
case "$SCENARIO" in
  plan|full|downgrade|failing-member|smoke) ;;
  *) usage ;;
esac
case "$K" in
  ''|*[!0-9]*) usage ;;
esac
[ "$K" -ge 1 ] || usage
K=$((10#$K))

PROMPT_FORM=${PROMPT_FORM:-slash}
case "$PROMPT_FORM" in slash|skill) ;; *) refuse "PROMPT_FORM must be slash or skill" ;; esac

CLAUDE_BIN=${CLAUDE_BIN:-claude}
command -v "$CLAUDE_BIN" >/dev/null 2>&1 || refuse "claude executable not found: $CLAUDE_BIN"
command -v timeout >/dev/null 2>&1 || refuse "GNU coreutils 'timeout' not found (macOS: brew install coreutils, put its gnubin on PATH)"

if [ -n "${CHECK_PLAN:-}" ]; then CHECK_PLAN_CMD=("$CHECK_PLAN"); else CHECK_PLAN_CMD=(python3 "$HERE/check_plan.py"); fi
if [ -n "${CHECK_RUN:-}" ]; then CHECK_RUN_CMD=("$CHECK_RUN"); else CHECK_RUN_CMD=(python3 "$HERE/check_run.py"); fi
REAL_CHECK_RUN=(python3 "$HERE/check_run.py")

# --- paths ----------------------------------------------------------------------------
WORK=${WORK:-$HOME/.cache/parallel-skills-test}
mkdir -p "$WORK" || refuse "cannot create WORK=$WORK"
WORK=$(cd "$WORK" && pwd -P)
RESULTS=$WORK/results
TRANSCRIPTS=$WORK/transcripts

case "$SCENARIO" in
  plan|full) DIRNAME=plan-$K ;;
  *)         DIRNAME=$SCENARIO-$K ;;
esac
DIR=$WORK/$DIRNAME
RESULT=$RESULTS/$SCENARIO-$K.json
TRANSCRIPT=$TRANSCRIPTS/$DIRNAME-$SCENARIO.jsonl

mark_failed() {  # mark_failed <scenario> <violation>
  "${REAL_CHECK_RUN[@]}" --mark-failed --scenario "$1" --run "$K" \
    --result-out "$RESULTS/$1-$K.json" --violation "$2"
}

# --- refusals / re-run rules (D13): all before anything is created ----------------------
if [ "$SCENARIO" = full ]; then
  if [ -e "$RESULT" ]; then
    refuse "full $K already has a result ($RESULT); to repeat it run: run_scenario.sh plan $K --force"
  fi
  [ "$FORCE" -eq 0 ] || refuse "full never takes --force; run: run_scenario.sh plan $K --force"
else
  if [ -e "$DIR" ] || [ -L "$DIR" ]; then
    [ "$FORCE" -eq 1 ] || refuse "$DIR already exists (use --force to delete it and its result and transcript)"
  fi
fi

mkdir -p "$RESULTS" "$TRANSCRIPTS" || refuse "cannot create $RESULTS and $TRANSCRIPTS"

if [ "$FORCE" -eq 1 ]; then
  rm -rf "$DIR"
  rm -f "$RESULT" "$TRANSCRIPT"
  if [ "$SCENARIO" = plan ]; then
    rm -f "$RESULTS/full-$K.json" "$TRANSCRIPTS/plan-$K-plan.jsonl" "$TRANSCRIPTS/plan-$K-full.jsonl"
  fi
fi

# --- full: D8 skip unless S1 run K passed -------------------------------------------------
if [ "$SCENARIO" = full ]; then
  PLAN_RESULT=$RESULTS/plan-$K.json
  S1_OK=0
  if [ -d "$DIR" ] && [ -f "$PLAN_RESULT" ] \
     && python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("passed") is True else 1)' "$PLAN_RESULT" 2>/dev/null; then
    S1_OK=1
  fi
  if [ "$S1_OK" -eq 0 ]; then
    echo "run_scenario.sh: S1 run $K did not pass; marking full $K skipped" >&2
    mark_failed full skipped
    exit 0
  fi
else
  bash "$HERE/setup.sh" "$DIR" || { rc=$?; echo "run_scenario.sh: setup.sh failed ($rc) for $DIR" >&2; exit 2; }
fi

# --- prompts (the only place they are defined; README documents them) ----------------------
SPEC=$DIR/specs/tinyshop-spec.md
PLAN=$DIR/specs/tinyshop-plan.md
READY="The spec is already READY; do not run /review-spec."
SKIP_VERIFY="Skip the final /verify-spec step."
D3="If a member's blocker is not fixed after one retry, stop and report; do not re-run the group sequentially."

invoke() {  # invoke <skill> <path>
  if [ "$PROMPT_FORM" = skill ]; then printf 'Use the %s skill on %s.' "$1" "$2"; else printf '/%s %s' "$1" "$2"; fi
}

case "$SCENARIO" in
  plan)
    PROMPT="$(invoke write-spec-plan "$SPEC") $READY Write the plan to $PLAN. Work non-interactively." ;;
  full)
    PROMPT="$(invoke implement-spec-plan "$PLAN") $READY $SKIP_VERIFY Work non-interactively." ;;
  downgrade)
    PROMPT="$(invoke implement-spec-plan "$DIR/bad-group-plan.md") $READY $SKIP_VERIFY Work non-interactively." ;;
  failing-member)
    PROMPT="$(invoke implement-spec-plan "$DIR/failing-member-plan.md") $READY $SKIP_VERIFY $D3 Work non-interactively." ;;
  smoke)
    PROMPT="$(invoke implement-spec-plan "$DIR/smoke-group-plan.md") $READY $SKIP_VERIFY Work non-interactively." ;;
esac

# --- headless run ----------------------------------------------------------------------------
SKILLS_STATUS_BEFORE=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)

(
  cd "$DIR" || exit 1
  timeout "$TIMEOUT_S" "$CLAUDE_BIN" -p "$PROMPT" \
    --output-format stream-json --verbose \
    --model "$MODEL" \
    --permission-mode acceptEdits \
    --allowedTools "$ALLOWED_TOOLS" \
    --max-budget-usd "$BUDGET_USD" > "$TRANSCRIPT"
)
CLAUDE_RC=$?

SKILLS_STATUS_AFTER=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)

FAIL_REASON=""
if [ "$CLAUDE_RC" -ne 0 ]; then
  FAIL_REASON="claude (or timeout) exited $CLAUDE_RC"
elif [ "$SKILLS_STATUS_BEFORE" != "$SKILLS_STATUS_AFTER" ]; then
  FAIL_REASON="the skills repository changed during the run (NFR-002)"
fi

if [ -n "$FAIL_REASON" ]; then
  echo "run_scenario.sh: $SCENARIO $K: $FAIL_REASON" >&2
  if [ "$SCENARIO" = smoke ]; then
    exit 1
  fi
  mark_failed "$SCENARIO" error
  exit 0
fi

if [ "$SCENARIO" = smoke ]; then
  echo "smoke run finished; transcript: $TRANSCRIPT"
  exit 0
fi

# --- checker ------------------------------------------------------------------------------------
if [ "$SCENARIO" = plan ]; then
  "${CHECK_PLAN_CMD[@]}" "$PLAN" --run "$K" --transcript "$TRANSCRIPT" --result-out "$RESULT"
else
  case "$SCENARIO" in
    full)           PLAN_ARG=$PLAN ;;
    downgrade)      PLAN_ARG=$DIR/bad-group-plan.md ;;
    failing-member) PLAN_ARG=$DIR/failing-member-plan.md ;;
  esac
  "${CHECK_RUN_CMD[@]}" "$DIR" "$PLAN_ARG" --transcript "$TRANSCRIPT" --run "$K" \
    --scenario "$SCENARIO" --result-out "$RESULT"
fi
CHECK_RC=$?

if [ "$CHECK_RC" -ne 0 ] && [ "$CHECK_RC" -ne 1 ]; then
  echo "run_scenario.sh: checker exited $CHECK_RC; marking $SCENARIO $K error" >&2
  mark_failed "$SCENARIO" error
  exit 0
fi
if [ ! -f "$RESULT" ]; then
  echo "run_scenario.sh: checker wrote no result file; marking $SCENARIO $K error" >&2
  mark_failed "$SCENARIO" error
  exit 0
fi

# --- BR-002: after a passing S1 the harness (not the session) commits the plan --------------------
if [ "$SCENARIO" = plan ] && [ "$CHECK_RC" -eq 0 ]; then
  COMMIT_OK=1
  git -C "$DIR" add specs || COMMIT_OK=0
  if [ "$COMMIT_OK" -eq 1 ]; then
    git -C "$DIR" -c commit.gpgsign=false commit -q --no-verify -m "Add plan" || COMMIT_OK=0
  fi
  if [ "$COMMIT_OK" -eq 1 ] && [ -n "$(git -C "$DIR" status --porcelain)" ]; then
    COMMIT_OK=0
  fi
  if [ "$COMMIT_OK" -eq 0 ]; then
    echo "run_scenario.sh: plan commit step failed or left a dirty tree; marking plan $K error" >&2
    mark_failed plan error
  fi
fi
exit 0
