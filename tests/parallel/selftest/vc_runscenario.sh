#!/usr/bin/env bash
# selftest/vc_runscenario.sh: stub-driven checks of ../run_scenario.sh (VC-018, run_scenario half of VC-017).
# Stubs: a fake `claude` and a fake checker, injected through CLAUDE_BIN / CHECK_PLAN / CHECK_RUN, with WORK
# pointed at a temp dir. Nothing is written to the skills repository or to $HOME/.cache; the real `claude` is never run.
#
# Stub conventions (environment variables read by the stubs):
#   claude stub:  STUB_LOG=<prefix>   (required) writes <prefix>.argv (one argument per line), .env, .pwd
#                 STUB_MODE=ok|crash  crash prints a partial line and exits 1
#                 STUB_WRITE_PLAN=1   writes specs/tinyshop-plan.md in its cwd (the scratch repo)
#                 STUB_STRAY=1        also writes an untracked stray.txt (dirty tree after the plan commit)
#                 STUB_TOUCH=<file>   appends to <file> (used to dirty a fake skills repository)
#   checker stub: STUB_CHK_LOG=<file> (required) appends its argv; STUB_CHK_RC=0|1|3 (default 0) is its exit code;
#                 on 0 or 1 it writes the --result-out file (passed true / violations ["VC-999"]) unless STUB_CHK_NOFILE=1
# Prints "PASS <name>" or "FAIL <name>: <reason>" per check, then a summary; exit 0 only if all pass.
set -uo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
HARNESS=$(cd "$HERE/.." && pwd -P)
REPO_ROOT=$(cd "$HARNESS/../.." && pwd -P)
RS=$HARNESS/run_scenario.sh

T=$(mktemp -d "${TMPDIR:-/tmp}/vc_runscenario.XXXXXX") || { echo "cannot create temp dir" >&2; exit 1; }
T=$(cd "$T" && pwd -P)
trap 'rm -rf "$T"' EXIT
if [ "$(git -C "$T" rev-parse --is-inside-work-tree 2>/dev/null || true)" = "true" ]; then
  echo "temp dir $T is inside a git work tree; set TMPDIR elsewhere" >&2
  exit 1
fi
unset STUB_LOG STUB_MODE STUB_WRITE_PLAN STUB_STRAY STUB_TOUCH STUB_CHK_LOG STUB_CHK_RC STUB_CHK_NOFILE PROMPT_FORM
export PYTHONDONTWRITEBYTECODE=1

# the constants under test, read from the script itself
eval "$(grep -E '^(TIMEOUT_S|BUDGET_USD|MODEL|ALLOWED_TOOLS)=' "$RS")"

SKILLS_BEFORE=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)

mkdir "$T/bin"
cat > "$T/bin/claude-stub" <<'EOF'
#!/usr/bin/env bash
L=${STUB_LOG:?STUB_LOG not set}
printf '%s\n' "$@" > "$L.argv"
env | sort > "$L.env"
pwd -P > "$L.pwd"
[ -z "${STUB_WRITE_PLAN:-}" ] || printf '# stub plan\n' > specs/tinyshop-plan.md
[ -z "${STUB_STRAY:-}" ] || echo stray > stray.txt
[ -z "${STUB_TOUCH:-}" ] || echo changed >> "$STUB_TOUCH"
if [ "${STUB_MODE:-ok}" = crash ]; then echo '{"type":"partial"}'; exit 1; fi
printf '%s\n' '{"type":"system","subtype":"init","model":"stub-model"}'
EOF
cat > "$T/bin/check-stub" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "${STUB_CHK_LOG:?STUB_CHK_LOG not set}"
out=""; scen=plan; run=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --result-out) out=$2; shift ;;
    --scenario) scen=$2; shift ;;
    --run) run=$2; shift ;;
  esac
  shift
done
rc=${STUB_CHK_RC:-0}
if [ "$rc" -le 1 ] && [ -z "${STUB_CHK_NOFILE:-}" ]; then
  if [ "$rc" -eq 0 ]; then p=true; v='[]'; else p=false; v='["VC-999"]'; fi
  printf '{"scenario":"%s","run":%s,"passed":%s,"violations":%s,"notes":[],"model":"stub"}\n' "$scen" "$run" "$p" "$v" > "$out"
fi
exit "$rc"
EOF
chmod +x "$T/bin/claude-stub" "$T/bin/check-stub"

FAILS=0
ok() { echo "PASS $1"; }
bad() { echo "FAIL $1: $2"; FAILS=$((FAILS + 1)); }

NW=0
newwork() { NW=$((NW + 1)); W=$T/work$NW; LOGP=$T/log$NW; CHK=$T/chk$NW.log; }

# rs <args...>: run run_scenario.sh with the stubs; sets RC and OUT
RUNS=0
rs() {
  RUNS=$((RUNS + 1))
  LASTLOG=$LOGP.$RUNS
  OUT=$(WORK="$W" CLAUDE_BIN="$T/bin/claude-stub" CHECK_PLAN="$T/bin/check-stub" CHECK_RUN="$T/bin/check-stub" \
        STUB_LOG="$LASTLOG" STUB_CHK_LOG="$CHK" bash "$RS" "$@" 2>&1)
  RC=$?
}

# jq-free JSON access: jget <file> <python expression over d>
jget() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); v=eval(sys.argv[2]); print(" ".join(map(str, v)) if isinstance(v, tuple) else v)' "$1" "$2" 2>/dev/null; }

expect() {  # expect <name> <actual> <expected>
  if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "got '$2', expected '$3'"; fi
}

# ============================================================ VC-018: error mapping
newwork
STUB_MODE=crash STUB_CHK_RC=0 rs downgrade 1
R=$W/results/downgrade-1.json
expect "crashing claude (checker stub would return 0): exit 0" "$RC" 0
expect "crashing claude: result violations == [error], passed false" "$(jget "$R" 'd["violations"], d["passed"], d["scenario"], d["run"]')" "['error'] False downgrade 1"
[ ! -e "$CHK" ] && ok "crashing claude: checker not invoked" || bad "crashing claude: checker not invoked" "checker log exists"

newwork
STUB_CHK_RC=3 rs failing-member 1
expect "checker exit 3: exit 0" "$RC" 0
expect "checker exit 3: result violations == [error]" "$(jget "$W/results/failing-member-1.json" 'd["violations"], d["passed"]')" "['error'] False"

newwork
STUB_CHK_RC=3 rs plan 1
expect "plan checker exit 3: plan-1.json error, no plan commit" \
  "$(jget "$W/results/plan-1.json" 'd["violations"]') $(git -C "$W/plan-1" rev-list --count HEAD)" "['error'] 1"

newwork
STUB_CHK_RC=1 rs downgrade 1
STUB_CHK_RC=0 rs downgrade 2
expect "checker exit 1 keeps the checker's result, run exits 0" "$(jget "$W/results/downgrade-1.json" 'd["violations"]') $RC" "['VC-999'] 0"
expect "checker exit 0 keeps the checker's result" "$(jget "$W/results/downgrade-2.json" 'd["passed"]')" "True"
STUB_CHK_RC=0 STUB_CHK_NOFILE=1 rs downgrade 3
expect "checker exit 0 without a result file -> error" "$(jget "$W/results/downgrade-3.json" 'd["violations"]') $RC" "['error'] 0"

# ============================================================ VC-018: full skip (D8)
skip_case() {  # skip_case <name> <setup-fn>
  newwork
  mkdir -p "$W/results"
  "$2"
  rs full 1
  if [ "$RC" -eq 0 ] && [ "$(jget "$W/results/full-1.json" 'd["violations"], d["passed"]')" = "['skipped'] False" ] \
     && [ ! -e "$LASTLOG.argv" ]; then
    ok "full K skipped: $1 (claude not invoked)"
  else
    bad "full K skipped: $1" "rc=$RC out=$OUT"
  fi
}
s_nojson() { mkdir -p "$W/plan-1"; }
s_failed() { mkdir -p "$W/plan-1"; echo '{"scenario":"plan","run":1,"passed":false,"violations":["VC-003"],"notes":[],"model":""}' > "$W/results/plan-1.json"; }
s_absent() { echo '{"scenario":"plan","run":1,"passed":true,"violations":[],"notes":[],"model":""}' > "$W/results/plan-1.json"; }
s_nothing() { :; }
skip_case "plan-k.json missing, directory present" s_nojson
skip_case "plan-k.json passed false" s_failed
skip_case "directory absent (passed true)" s_absent
skip_case "no plan-k state at all" s_nothing

# ============================================================ prompts/argv + plan commit + full + repeat rules
check_argv() {  # check_argv <name> <logprefix> <scenario-key> <dir>
  python3 - "$2" "$3" "$4" "$MODEL" "$ALLOWED_TOOLS" "$BUDGET_USD" <<'PY'
import sys
log, key, d, model, tools, budget = sys.argv[1:7]
argv = open(log + ".argv").read().split("\n")[:-1]
env = open(log + ".env").read().split("\n")
errs = []
def pair(flag, val):
    if not any(argv[i] == flag and argv[i + 1] == val for i in range(len(argv) - 1)):
        errs.append(f"missing {flag} {val}")
if len(argv) < 2 or argv[0] != "-p":
    errs.append("argv does not start with -p <prompt>")
else:
    p = argv[1]
    target = {"plan": d + "/specs/tinyshop-spec.md", "full": d + "/specs/tinyshop-plan.md",
              "downgrade": d + "/bad-group-plan.md", "failing-member": d + "/failing-member-plan.md",
              "smoke": d + "/smoke-group-plan.md"}[key]
    skill = "write-spec-plan" if key == "plan" else "implement-spec-plan"
    if not p.startswith(f"/{skill} {target}"):
        errs.append(f"prompt does not start with '/{skill} {target}': {p[:120]}")
    if "READY" not in p or "/review-spec" not in p:
        errs.append("prompt lacks the READY / no /review-spec clause")
    if key == "plan":
        if f"{d}/specs/tinyshop-plan.md" not in p.replace(target, ""):
            errs.append("plan prompt lacks the plan destination")
        if "/verify-spec" in p:
            errs.append("plan prompt mentions /verify-spec")
    elif "/verify-spec" not in p:
        errs.append("prompt lacks the /verify-spec skip")
    d3 = "if a member's blocker is not fixed after one retry, stop and report; do not re-run the group sequentially"
    if (d3 in p.lower()) != (key == "failing-member"):
        errs.append("D3 sentence presence wrong for " + key)
pair("--output-format", "stream-json")
if "--verbose" not in argv:
    errs.append("missing --verbose")
pair("--model", model)
pair("--permission-mode", "acceptEdits")
pair("--allowedTools", tools)
pair("--max-budget-usd", budget)
if "PYTHONDONTWRITEBYTECODE=1" not in env:
    errs.append("env lacks PYTHONDONTWRITEBYTECODE=1")
if open(log + ".pwd").read().strip() != d:
    errs.append("cwd is not the scratch repo")
bypass = "dangerously" "-skip"
if any(bypass in a for a in argv):
    errs.append("bypass flag present")
print("; ".join(errs))
sys.exit(1 if errs else 0)
PY
}
argv_case() {  # argv_case <name> <key> <dir>
  local msg
  if msg=$(check_argv "$1" "$LASTLOG" "$2" "$3"); then ok "argv/env: $1"; else bad "argv/env: $1" "$msg"; fi
}

newwork
STUB_WRITE_PLAN=1 rs plan 1
D=$W/plan-1
expect "plan 1 (passing) exit 0" "$RC" 0
argv_case "plan" plan "$D"
expect "plan commit: subject Add plan, plan tracked, tree clean" \
  "$(git -C "$D" log -1 --format=%s) $(git -C "$D" ls-files specs/tinyshop-plan.md) [$(git -C "$D" status --porcelain)] $(git -C "$D" rev-list --count HEAD)" \
  "Add plan specs/tinyshop-plan.md [] 2"
expect "plan check call carries plan path, --run, --transcript, --result-out" \
  "$(grep -c "^$D/specs/tinyshop-plan.md --run 1 --transcript $W/transcripts/plan-1-plan.jsonl --result-out $W/results/plan-1.json\$" "$CHK")" 1
expect "plan result kept as written by the checker (passed true)" "$(jget "$W/results/plan-1.json" 'd["passed"]')" True
[ -s "$W/transcripts/plan-1-plan.jsonl" ] && ok "plan transcript written to transcripts/plan-1-plan.jsonl" || bad "plan transcript" "missing"

rs full 1
expect "full 1 after passing plan 1: exit 0, result written" "$RC $(jget "$W/results/full-1.json" 'd["scenario"]')" "0 full"
argv_case "full" full "$D"
expect "full check call: <dir> <plan> --scenario full" \
  "$(grep -c "^$D $D/specs/tinyshop-plan.md --transcript $W/transcripts/plan-1-full.jsonl --run 1 --scenario full --result-out $W/results/full-1.json\$" "$CHK")" 1
rs full 1
RC1=$RC; O1=$OUT
rs full 1 --force
if [ "$RC1" -eq 2 ] && [ "$RC" -eq 2 ] && printf '%s\n%s\n' "$O1" "$OUT" | grep -c 'plan 1 --force' | grep -qx 2; then
  ok "repeat full 1 exits 2 with and without --force, naming 'plan 1 --force'"
else
  bad "repeat full 1" "rc=$RC1/$RC out=$O1 | $OUT"
fi

# plan K --force deletes plan-K, results plan/full-K and K's transcripts; other K untouched
STUB_WRITE_PLAN=1 rs plan 2
rs full 2
touch "$D/marker"
STUB_WRITE_PLAN=1 STUB_CHK_RC=1 rs plan 1 --force
expect "plan 1 --force: exit 0, old dir/result/full result/transcripts replaced or deleted" \
  "$RC [$([ -e "$D/marker" ] && echo marker)] $(jget "$W/results/plan-1.json" 'd["passed"]') [$([ -e "$W/results/full-1.json" ] && echo full1)] [$([ -e "$W/transcripts/plan-1-full.jsonl" ] && echo tfull)]" \
  "0 [] False [] []"
expect "plan 1 --force leaves K=2 files alone" \
  "$([ -e "$W/results/plan-2.json" ] && echo a)$([ -e "$W/results/full-2.json" ] && echo b)$([ -e "$W/transcripts/plan-2-full.jsonl" ] && echo c)$([ -d "$W/plan-2" ] && echo d)" abcd

# ============================================================ plan-commit failure (VC-017 run_scenario half)
newwork
STUB_WRITE_PLAN=1 STUB_STRAY=1 rs plan 1
expect "dirty tree after plan commit -> plan-1.json rewritten as error, exit 0" \
  "$RC $(jget "$W/results/plan-1.json" 'd["violations"], d["passed"]')" "0 ['error'] False"
newwork
STUB_CHK_RC=0 rs plan 1
expect "plan commit step fails (plan file never written) -> error" "$(jget "$W/results/plan-1.json" 'd["violations"]')" "['error']"
rs full 1
expect "full 1 after an errored plan 1 is skipped" "$(jget "$W/results/full-1.json" 'd["violations"]')" "['skipped']"

# ============================================================ downgrade / failing-member / smoke argv, re-run, force
for sc in downgrade failing-member smoke; do
  newwork
  rs "$sc" 1
  expect "$sc 1: first run exit 0" "$RC" 0
  argv_case "$sc" "$sc" "$W/$sc-1"
  touch "$W/$sc-1/marker"
  rs "$sc" 1
  expect "$sc 1 again (dir exists): exit 2, nothing started" "$RC $([ -e "$LASTLOG.argv" ] && echo ran)" "2 "
  rs "$sc" 1 --force
  expect "$sc 1 --force: exit 0 and old dir replaced" "$RC [$([ -e "$W/$sc-1/marker" ] && echo marker)]" "0 []"
done
newwork
rs smoke 1
expect "smoke writes transcripts/smoke-1-smoke.jsonl and no result file" \
  "$([ -s "$W/transcripts/smoke-1-smoke.jsonl" ] && echo t)$([ -e "$W/results/smoke-1.json" ] && echo r)" t
rs plan 1
rs plan 1
expect "plan 1 again (dir exists): exit 2" "$RC" 2

newwork
STUB_MODE=crash rs smoke 1
expect "smoke with a crashing claude: exit 1, no result file" "$RC [$(ls "$W/results" 2>/dev/null)]" "1 []"

# ============================================================ NFR-002: skills repository changed during a run
FAKE=$T/fakeskills
mkdir -p "$FAKE/tests/parallel/selftest" "$FAKE/skills/write-spec-plan" "$FAKE/skills/implement-spec-plan"
cp "$HARNESS/run_scenario.sh" "$HARNESS/setup.sh" "$HARNESS/check_run.py" "$HARNESS/hlib.py" "$FAKE/tests/parallel/"
cp -R "$HARNESS/fixture" "$FAKE/tests/parallel/fixture"
echo x > "$FAKE/skills/write-spec-plan/SKILL.md"; echo x > "$FAKE/skills/implement-spec-plan/SKILL.md"
git -C "$FAKE" init -q -b main
git -C "$FAKE" add -A
git -C "$FAKE" -c user.name=t -c user.email=t@example.invalid -c commit.gpgsign=false commit -q -m init
newwork
OUT=$(WORK="$W" CLAUDE_BIN="$T/bin/claude-stub" CHECK_PLAN="$T/bin/check-stub" CHECK_RUN="$T/bin/check-stub" \
      STUB_LOG="$LOGP.1" STUB_CHK_LOG="$CHK" STUB_TOUCH="$FAKE/skills/touched.txt" bash "$FAKE/tests/parallel/run_scenario.sh" downgrade 1 2>&1)
RC=$?
expect "skills repo status changed during the run -> error, checker not invoked" \
  "$RC $(jget "$W/results/downgrade-1.json" 'd["violations"]') [$([ -e "$CHK" ] && echo ran)]" "0 ['error'] []"
OUT=$(WORK="$W" CLAUDE_BIN="$T/bin/claude-stub" STUB_LOG="$LOGP.2" STUB_TOUCH="$FAKE/skills/touched2.txt" \
      bash "$FAKE/tests/parallel/run_scenario.sh" smoke 1 2>&1)
expect "skills repo changed during a smoke run -> exit 1" "$?" 1

# ============================================================ usage errors and options
newwork
usage_case() {
  rs "$@"
  expect "usage: run_scenario.sh $* -> exit 2" "$RC" 2
}
usage_case
usage_case plan
usage_case bogus 1
usage_case plan 0
usage_case plan x
usage_case plan 1 --bogus
usage_case plan 1 --force extra
usage_case full 1 --force
[ ! -e "$W/plan-1" ] && ok "usage errors create no scratch dir" || bad "usage errors create no scratch dir" "plan-1 exists"
newwork
OUT=$(WORK="$W" CLAUDE_BIN="$T/bin/does-not-exist" bash "$RS" plan 1 2>&1); RC=$?
expect "missing claude executable -> exit 2, nothing created" "$RC $([ -e "$W/plan-1" ] && echo created)" "2 "
newwork
PROMPT_FORM=skill rs smoke 1
if grep -qx "Use the implement-spec-plan skill on $W/smoke-1/smoke-group-plan.md\\. The spec is already READY; do not run /review-spec\\. Skip the final /verify-spec step\\. Work non-interactively\\." "$LASTLOG.argv"; then
  ok "PROMPT_FORM=skill uses the 'Use the <skill> skill on <path>' form"
else
  bad "PROMPT_FORM=skill" "$(sed -n 2p "$LASTLOG.argv")"
fi
newwork
PROMPT_FORM=bogus rs plan 1
expect "invalid PROMPT_FORM -> exit 2" "$RC" 2

# ============================================================ VC-021 (run_scenario half): constants and flags
BYPASS='dangerously''-skip'
expect "constants: TIMEOUT_S/BUDGET_USD/MODEL as specified" "$TIMEOUT_S $BUDGET_USD $MODEL" "1800 10 claude-sonnet-5-5"
expect "constants: ALLOWED_TOOLS matches the D4 list" "$ALLOWED_TOOLS" \
  "Skill SendMessage Agent Read Write Edit Glob Grep Bash(git:*) Bash(python:*) Bash(python3:*) Bash(mkdir:*) Bash(ls:*) Bash(cat:*) Bash(cp:*) Bash(mv:*) Bash(rm:*) Bash(touch:*)"
expect "constants defined as ^NAME= lines (4)" "$(grep -cE '^(TIMEOUT_S|BUDGET_USD|MODEL|ALLOWED_TOOLS)=' "$RS")" 4
USES=0
grep -q 'timeout "\$TIMEOUT_S"' "$RS" && grep -q -- '--max-budget-usd "\$BUDGET_USD"' "$RS" && grep -q -- '--permission-mode acceptEdits' "$RS" \
  && grep -q -- '--allowedTools "\$ALLOWED_TOOLS"' "$RS" && grep -q -- '--model "\$MODEL"' "$RS" && USES=1
expect "constants are used with timeout, --max-budget-usd, --permission-mode acceptEdits, --allowedTools, --model" "$USES" 1
expect "bypass flag text absent from run_scenario.sh and this script" "$(cat "$RS" "$HERE/vc_runscenario.sh" | grep -c -- "$BYPASS")" 0

# ============================================================ repo untouched
SKILLS_AFTER=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)
expect "skills repository git status unchanged by this script" "$([ "$SKILLS_BEFORE" = "$SKILLS_AFTER" ] && echo same)" same

if [ "$FAILS" -eq 0 ]; then echo "vc_runscenario: all checks passed (VC-018 PASS)"; else echo "vc_runscenario: $FAILS check(s) failed"; fi
[ "$FAILS" -eq 0 ]
