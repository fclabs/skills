# Iteration 7: run_scenario.sh

Commit SHA: see `git log` entry "Add run_scenario.sh with exit mapping, plan commit and stub-driven VC-018 tests" on `main` (a record cannot hold its own SHA).

## Criteria results
Commands from `/Users/fede/devel/fclabs/skills/tests/parallel` with `PYTHONDONTWRITEBYTECODE=1`. The real `claude` was never invoked; no money spent.
- PASS VC-018: `bash selftest/vc_runscenario.sh` -> one PASS line per check, last line `vc_runscenario: all checks passed (VC-018 PASS)`, exit 0. Covered: crashing claude (checker stub returning 0) -> `error`, checker not called; checker exit 3 -> `error` (downgrade, failing-member, and plan with no commit); checker 0/1 keep the checker's result, exit 0 without a file -> `error`; `full 1` with no plan-1.json / `passed: false` / absent dir / no state -> `skipped`, claude not invoked; failed plan commit (stray file, or no plan written) -> `plan-1.json` rewritten `error`, following `full 1` skipped; argv/env per scenario (plan, full, downgrade, failing-member, smoke): prompt starts with `/<skill> <abs path>`, `READY`, `/review-spec` negation, `/verify-spec` skip (S2-S4, smoke), D3 sentence only for failing-member, `--output-format stream-json`, `--verbose`, `--model`, `--permission-mode acceptEdits`, `--allowedTools`, `--max-budget-usd`, env `PYTHONDONTWRITEBYTECODE=1`, cwd = scratch repo; existing dir -> exit 2 and `--force` -> exit 0 for plan, downgrade, failing-member, smoke; repeat `full 1` -> exit 2 with and without `--force`, output names `plan 1 --force`; `plan 1 --force` deleted `full-1.json`, `plan-1-full.jsonl`, replaced `plan-1.json`/dir, left K=2 files; smoke with crashing stub -> exit 1, no result file.
- PASS VC-017 (run_scenario half): same script; dirty tree after the plan commit -> `plan-1.json` `['error']`; success case: HEAD subject `Add plan`, `specs/tinyshop-plan.md` tracked, `git status --porcelain` empty, 2 commits.
- PASS VC-021 (partial): `grep -nE '^(TIMEOUT_S|BUDGET_USD|MODEL|ALLOWED_TOOLS)=' run_scenario.sh` -> lines 13-16 with the specified values; `timeout "$TIMEOUT_S"`, `--max-budget-usd "$BUDGET_USD"`, `--permission-mode acceptEdits`, `--allowedTools "$ALLOWED_TOOLS"`, `--model "$MODEL"` present (also asserted in the test). `P='dangerously''-skip'; grep -rn -- "$P" *.py *.sh selftest/*` -> no match. mkdir-words: `grep -rlE 'mkdir|makedirs|mkdtemp' *.py *.sh selftest/*` -> `setup.sh`, `selftest/make_cases.py`, `run_scenario.sh`, `selftest/vc_setup.sh`, `selftest/vc_runscenario.sh` (all allowed).
- PASS regression: `bash selftest/run.sh` -> `selftest: 126/126 cases passed`; `bash selftest/vc_setup.sh` -> `VC-001 PASS`, `VC-002 PASS`.
- PASS NFR-002 (stub): copy of the harness inside a throw-away git repo; claude stub modifies it -> `error` result (smoke: exit 1). The real skills repo `git status --porcelain` was unchanged by the test script (asserted) and showed only the new files plus the two untracked spec files; `find . -name __pycache__` -> none; `$HOME/.cache/parallel*` absent.
- PASS artifacts: this record; `CONTEXT.md` rewritten (153 lines, six sections: CLI, constants, layout, prompts, env overrides, stub conventions); `DECISIONS.md` D-020..D-024.

## Files
Added: `tests/parallel/run_scenario.sh` (mode 755), `tests/parallel/selftest/vc_runscenario.sh`, this record. Changed: `CONTEXT.md`, `DECISIONS.md`. Deleted: none.

## Deviations
- None from the Scope. Interpretations are D-020..D-024 (smoke dir `smoke-<k>`, missing result file after checker 0/1 -> `error`, plan commit only when the plan checker exited 0, `full --force` refused even when fresh, extra `Work non-interactively.` prompt clause).

## Gotchas
- `$((++N))` inside `$(...)` loses the increment (subshell); the test's `rs` helper increments before the call.
- macOS bash 3.2: no `mapfile`; the argv assertions use an inline `python3` block.
- `timeout` must be on PATH (here `/opt/homebrew/bin/timeout`); `run_scenario.sh` exits 2 without it.
- The test needs `$TMPDIR` outside any git work tree (same as `vc_setup.sh`); full run ~25 s.
- `WORK` is resolved with `pwd -P` so prompt paths equal `setup.sh`'s substituted paths (macOS `/private/var`).

## For the next iteration
- Iteration 8 (`accept.sh`, `selftest/vc_static.sh`, README): `vc_static.sh` should call `bash selftest/vc_runscenario.sh` and `bash selftest/vc_setup.sh`; the README quotes the prompts from `run_scenario.sh` (see CONTEXT.md Public interfaces) and the constants verbatim; VC-021's mkdir grep must now allow `run_scenario.sh`, `selftest/*`, `check_run.py`, `setup.sh`.
- Iteration 9: if `/skill args` is unresolved by `claude -p`, flip the `PROMPT_FORM` default in `run_scenario.sh` (one line) and update the README; add any needed tool to `ALLOWED_TOOLS` (single place; the stub test reads it from the script). Add `--check-skill-source` to the checker call when D14 is finished. Reconcile the stream-json shape; `run_scenario.sh` does not parse transcripts.
- Exit-code contract for README/accept.sh: 0 result written, 1 smoke crash only, 2 usage/refusal; `full K` repeat requires `plan K --force`.
