# Parallel plan and execution test harness

## Purpose

`write-spec-plan` and `implement-spec-plan` support parallel iteration groups (disjoint `Touches`, worktree
isolation, merge, reconcile). This harness is a repeatable end-to-end test for the skill maintainer: plan a
fixture spec (`tinyshop`) with `/write-spec-plan`, execute plans with `/implement-spec-plan`, and assert on the
plan file, the git history and the session transcript. Run it after editing either skill.

It has four live scenarios plus two one-off checks:

| Scenario | `run_scenario.sh` token | What it exercises |
|---|---|---|
| S1 plan-only | `plan K` | `/write-spec-plan` on the fixture; `check_plan.py` (VC-003..007, VC-025) |
| S2 full execution | `full K` | `/implement-spec-plan` on the S1 plan of run K; `check_run.py` (VC-008..013) |
| S3 downgrade | `downgrade K` | executor downgrades a wrong group (`bad-group-plan.md`); VC-014 |
| S4 failing member | `failing-member K` | executor handling of a failing group member; VC-015 |
| smoke (VC-022) | `smoke 1` | one headless group run on `smoke-group-plan.md`; no result file |
| VC-023 | manual command below | `/review-spec` on the fixture must say READY |

Each scenario runs in a fresh scratch repo built by `setup.sh`; the skills repository is never touched. The
skills under test are the ones in this repository (`setup.sh` symlinks `skills/*` into the scratch repo's
`.claude/skills/`).

## Prerequisites

- git >= 2.28 (`git init -b`).
- Python >= 3.11, reachable as both `python3` (the harness) and `python` (the fixture's commands and the S4 plan's
  criteria). Checkers are stdlib only.
- GNU coreutils `timeout`. On macOS: `brew install coreutils` and put its `gnubin` directory on `PATH`.
- `claude` (Claude Code) on `PATH`, a build whose Agent tool accepts `isolation: "worktree"`, and an account that
  may spawn subagents.
- User-level (`~/.claude/skills`) and plugin copies of `write-spec-plan` and `implement-spec-plan` absent or
  disabled during runs; otherwise the checker reports `skill-source` (spec D14).
- Never in use: the bypass-permissions flag (`--dangerously-skip-permissions`). Runs use
  `--permission-mode acceptEdits` plus an explicit allowlist.

## Running the scenarios

From this directory (`tests/parallel/`). All of these spend real model money except where noted; see Cost.

```
bash run_scenario.sh plan 1              # S1 run 1: setup, /write-spec-plan, check_plan.py, plan commit
bash run_scenario.sh full 1              # S2 run 1: continues in the S1 run 1 repo, only if S1 run 1 passed
bash run_scenario.sh downgrade 1         # S3 run 1
bash run_scenario.sh failing-member 1    # S4 run 1
bash run_scenario.sh smoke 1             # VC-022 smoke run (transcript only)
```

Each scenario is judged by 3 runs (K = 1, 2, 3) and passes when at least 2 pass (spec D6).

Exit codes of `run_scenario.sh`: 0 once a result is written (whatever the verdict; for `smoke`, once its transcript
is written); 1 only when a `smoke` run crashes, times out, is budget-killed, or changes the skills repository; 2 for
usage errors and refusals.

Re-run rules (spec D13):

- `plan K`, `downgrade K`, `failing-member K`, `smoke K`: if `$WORK/<dir>` exists the script exits 2; `--force`
  deletes the directory, its result and its transcript first.
- `plan K --force` also deletes `results/full-K.json` and K's `plan`/`full` transcripts.
- `full K` never takes `--force`. A repeat `full K` (its result file exists) exits 2 and tells you to run
  `plan K --force`, which repeats S1 and then you run `full K` again. If S1 run K did not pass (or its directory is
  absent) `full K` writes a result with violation `skipped` and does not invoke `claude`.
- A non-zero exit of `timeout` or `claude`, a checker exit other than 0 or 1, a missing result file, or a change in
  the skills repository's `git status --porcelain` during the run produces a result with violation `error`.

Environment overrides: `WORK`, `CLAUDE_BIN`, `CHECK_PLAN`, `CHECK_RUN` (the last three are for the stub-driven
tests), and `PROMPT_FORM=slash|skill` (default `slash`; `skill` selects the fallback prompt form below, for builds
where `claude -p "/skill args"` is not resolved).

## Prompts

The prompts are defined only in `run_scenario.sh`. Each is one line; `<dir>` is the absolute scratch directory.
The shared clause is `The spec is already READY; do not run /review-spec.` (spec D2).

- plan: `/write-spec-plan <dir>/specs/tinyshop-spec.md` + READY clause + `Write the plan to <dir>/specs/tinyshop-plan.md.` + `Work non-interactively.`
- full: `/implement-spec-plan <dir>/specs/tinyshop-plan.md` + READY clause + `Skip the final /verify-spec step.` + `Work non-interactively.`
- downgrade: the same on `<dir>/bad-group-plan.md`.
- failing-member: the same on `<dir>/failing-member-plan.md`, with the D3 sentence before `Work non-interactively.`
- smoke: the same on `<dir>/smoke-group-plan.md`.

The D3 sentence (spec D3): `If a member's blocker is not fixed after one retry, stop and report; do not re-run the group sequentially.`

Fallback form (`PROMPT_FORM=skill`): the invocation `/<skill> <path>` is replaced by `Use the <skill> skill on <path>.`

Every headless command is:

```
timeout $TIMEOUT_S claude -p "<prompt>" --output-format stream-json --verbose --model $MODEL \
  --permission-mode acceptEdits --allowedTools "$ALLOWED_TOOLS" --max-budget-usd $BUDGET_USD > <transcript>
```

with `PYTHONDONTWRITEBYTECODE=1`, the working directory set to the scratch repo, and stdout as the transcript the
checkers read.

The allowlist (`ALLOWED_TOOLS` in `run_scenario.sh`, the only definition; this list must match it exactly):

```
Skill SendMessage Agent Read Write Edit Glob Grep Bash(git:*) Bash(python:*) Bash(python3:*) Bash(mkdir:*) Bash(ls:*) Bash(cat:*) Bash(cp:*) Bash(mv:*) Bash(rm:*) Bash(touch:*)
```

Any tool a live group run turns out to need is added there, in this list, and noted under Recorded results.

## Directory layout

`WORK` defaults to `$HOME/.cache/parallel-skills-test`.

```
$WORK/plan-K/                       scratch repo of S1 run K (reused by S2 run K)
$WORK/downgrade-K/                  S3 scratch repo
$WORK/failing-member-K/             S4 scratch repo
$WORK/smoke-K/                      smoke scratch repo
$WORK/results/<scenario>-K.json     one result per run (plan, full, downgrade, failing-member); smoke writes none
$WORK/transcripts/<dir>-<scenario>.jsonl     e.g. plan-1-plan.jsonl, plan-1-full.jsonl, smoke-1-smoke.jsonl
```

Transcripts live outside the scratch repo so it stays clean. After a passing S1, `run_scenario.sh` (not the
session) commits `specs/tinyshop-plan.md` to `main` with the message `Add plan`.

## Reading the results

A result file is `{"scenario", "run", "passed", "violations", "notes", "model"}`. Each violation is a VC id,
`NFR-001`, `skill-source`, `skipped` or `error`. Notes carry `subagents: N`, the init event's model, any
`permission_denials`, the non-gating FR-014 / VC-012 findings (spec D12), and the unmerged-branch line of S4.

```
python3 check_run.py --summary $WORK/results --scenario full    # also: plan, downgrade, failing-member
```

It prints the union of the violations of that scenario's files and exits 0 iff at least 2 files have
`passed: true`; exit 2 if fewer than 3 files exist, exit 1 otherwise. Checkers can also be run by hand:

```
python3 check_plan.py <plan.md> --run 1 [--transcript t.jsonl] [--result-out r.json]
python3 check_run.py <repo> <plan.md> --transcript t.jsonl --run 1 --scenario {full,downgrade,failing-member} [--result-out r.json]
```

Exit codes of both: 0 ok, 1 violations (each violated id is printed), 2 usage or unparseable input.

## Reading a red result

A red S2 is not necessarily a harness bug. By spec D5 the plans use absolute paths into the main checkout while
worktree members run in another checkout, and VC-010 expects every member's record to be committed on its own
member branch; a failure there (and VC-022b FAIL) is a real skill defect the harness has found. The 2-of-3 rule
(spec D6) accepts a defect that shows in about 1 of 3 runs; that trade-off is taken deliberately to bound cost.
Green live scenarios are not required for acceptance (spec D9).

## Fixture review (VC-023)

Run once whenever `fixture/tinyshop-spec.md` changes. In a fresh scratch directory (so the skills are installed):

```
bash setup.sh /tmp/vc023-dir      # any new directory outside a git repo
cd /tmp/vc023-dir
timeout 1800 claude -p "/review-spec specs/tinyshop-spec.md" --output-format stream-json --verbose \
  --model claude-sonnet-5-5 --permission-mode acceptEdits --allowedTools "<the allowlist above>" \
  --max-budget-usd 10 > review.jsonl
shasum -a 256 specs/tinyshop-spec.md   # or sha256sum; compare with the fixture's hash
```

Pass rule: the last orchestrator-level assistant text in `review.jsonl` contains `Overall Verdict` followed by
`READY`, and the sha256 of the spec in the scratch directory is unchanged (equal to the fixture's, so no fix-loop
edits were made). Then record `VC-023: READY sha256=<hash>` below. `accept.sh` fails if the hash differs from
the current fixture's. The command uses the same `timeout` and `--max-budget-usd` values as the scenarios.

## Cost

Worst case for one full harness pass: 12 scenario runs (3 per scenario x 4) + the smoke run + the VC-023 review run
= 14 live runs, each capped at `--max-budget-usd 10`, so about $140. The constants `TIMEOUT_S=1800`,
`BUDGET_USD=10` and the agent caps `MAX_AGENTS_S2=15`, `MAX_AGENTS_OTHER=6` (in `check_run.py`) are provisional.

## Calibrating the constants

After the first full S2 run, record its wall time and spend (the `result` event of
`$WORK/transcripts/plan-1-full.jsonl` carries `total_cost_usd` and `duration_ms`) on the `S2 first full run:` line
below, then update `MAX_AGENTS_S2`, `MAX_AGENTS_OTHER` (`check_run.py`), `TIMEOUT_S` and `BUDGET_USD`
(`run_scenario.sh`) from the measurement and adjust the cost figure above. Each is a named constant; `selftest/`
asserts against the names, not the literals.

## Model

`run_scenario.sh` passes `--model "$MODEL"` with `MODEL=claude-sonnet-5-5`, the model the maintainer uses for these
skills. To change it, edit the single `MODEL=` line at the top of `run_scenario.sh` (and the `model:` line below).
Each result file records the model id reported by the transcript's init event.

## Offline checks

These cost nothing, never call the real `claude` and write nothing into the skills repository or
`$HOME/.cache` (they need `$TMPDIR` outside any git work tree and `timeout` on `PATH`). From this directory:

```
bash selftest/run.sh              # golden cases for both checkers (about 30 s)
bash selftest/vc_setup.sh         # VC-001, VC-002
bash selftest/vc_runscenario.sh   # VC-018, run_scenario half of VC-017 (stub claude, about 25 s)
bash selftest/vc_static.sh        # static VC-021 clauses, accept.sh behaviour; also runs the suites above
bash accept.sh --pre-live         # all of the offline checks in one go
```

`accept.sh [--pre-live] [results-dir]` is the harness acceptance (spec D9, VC-024). It exits 0 iff `selftest/run.sh`
and `selftest/vc_static.sh` pass, this README holds `VC-022a: PASS`, a `VC-022b: PASS` or `VC-022b: FAIL` line and
a `VC-023: READY sha256=<hash>` line whose hash matches the current fixture, `results-dir` (default
`$WORK/results`) holds `<scenario>-1..3.json` for plan, full, downgrade and failing-member, and every result with
`passed: false` has a non-empty `violations`. Exit 1 names the failing check (for example a scenario with only 2
files); exit 2 is a usage error. `--pre-live` runs only the offline part (and tolerates `TBD` in the
`claude --version:` and `model:` lines) so it can be used before any live run.

## Recorded results

Overwrite the placeholder lines after the live runs (the lines are matched at the start of a line):

```
VC-022a: TBD
VC-022b: TBD
VC-023: TBD
claude --version: TBD
model: TBD
D14 skill-path field: TBD
S2 first full run: TBD
```

- `VC-022a: PASS|FAIL`: harness validity. Both `plan 1` and `smoke 1` load their skill from `<dir>/.claude/skills`,
  the transcript field carrying the loaded skill's path is identified (the `D14 skill-path field:` line), the
  stream-json shape matches the checkers, and neither run's `result` event has non-empty `permission_denials`.
  Must be `PASS` for `accept.sh`. Also note here the sample of the stream-json shape, the wall time and spend, and
  any tool added to the allowlist.
- `VC-022b: PASS|FAIL`: skill behaviour. The two group-C members' records are present on their member branches
  (or the merge's second parents). A FAIL is a skill defect (spec D5); S2 is then expected red until it is fixed.
- `VC-023: READY sha256=<hash>`: see Fixture review.
- `claude --version: <value>` and `model: <value>`: the known-good pair of the passing smoke run (spec NFR-003);
  update them after any later passing run.
- `D14 skill-path field: <value>`: the transcript field with the loaded skill's path, or the documented fallback
  (the init event's skill and plugin listings).
- `S2 first full run: <wall time, spend>`: see Calibrating the constants.

## Not covered

Skill behaviours this harness does not exercise: a member writing outside its `Touches`, the merge-conflict
fallback, test failure in the reconcile step, interactive mode, and the `/verify-spec` verdict (the S2-S4 prompts
skip it). The `SendMessage` retry path is exercised only incidentally by S4 (spec D3) and is not asserted. Out of
scope: prose quality of plans and docs beyond the structural checks, other skills, wall-clock speedup measurement
and CI integration (runs spend model tokens).
