# Iteration 4: check_run.py core

Commit SHA: see `git log` entry "Add check_run.py core modes, refusals, cost check and golden cases" on `main` (a record cannot hold its own SHA).

## Criteria results
Commands from `/Users/fede/devel/fclabs/skills/tests/parallel` with `PYTHONDONTWRITEBYTECODE=1`.
- PASS VC-017 (checker half): `bash selftest/run.sh` -> cases `run-refuse-skills-repo` and `run-refuse-skills-repo-downgrade` (skills layout) and `run-refuse-uncommitted-plan` (full, plan untracked) PASS with exit 2 and the expected message; `run-missing-plan-in-repo-ok-for-downgrade` shows the plan-commit rule applies to `full` only.
- PASS VC-018 (checker parts): same run: `summary-true-true-false-exits-0`, `summary-true-false-false-exits-1`, `summary-two-files-exits-2` (union printed), `summary-all-pass-prints-none`, `summary-ignores-other-scenarios`, `summary-missing-dir-exits-2`, `summary-bad-result-file-exits-2`; `run-good-result-notes` and `run-good-result-run-number` validate the BR-004 shape incl. `notes` and `model` (also `check_run.py ... --result-out r.json; cat r.json`); `mark-failed-full-run-2-skipped` writes `passed: false`, violation `skipped`, `model ""`; also error/plan/failing-member variants and 3 exit-2 cases.
- PASS VC-020: `run-nfr001-full-15-ok`/`-16-fails`, `downgrade-6-ok`/`-7-fails`, `failing-member-6-ok`/`-7-fails`, `counts-calls-not-messages`, `task-tool-name-counts`, `subagent-calls-not-counted` (+ `-other`); all assert `subagents: N` in the output. Manual: `check_run.py repo plan.md --transcript transcript.jsonl --run 1 --scenario full` on the 16-agent case -> `NFR-001: 16 ...`, exit 1.
- PASS VC-016 (run half, partial): `run-usage-missing-transcript` exit 2; manual command exits 2 with `transcript not found`. The `Merge iteration` -> `VC-014` half stays for Iteration 6.
- PASS constants: `grep -n 'MAX_AGENTS_S2\|MAX_AGENTS_OTHER' check_run.py` -> lines 31, 32 (=15, =6) and use in `max_agents`.
- PASS regression: `bash selftest/run.sh` -> `selftest: 69/69 cases passed` (30 plan + 39 new); `bash selftest/vc_setup.sh` -> VC-001 PASS, VC-002 PASS.
- PASS hygiene: `grep -rEn 'mkdir|makedirs|mkdtemp' hlib.py check_plan.py check_run.py` -> none; `P='dangerously''-skip'; grep -rln -- "$P" *.py *.sh selftest/*` -> none; `python3 -c "import hlib, check_plan, check_run"` ok; `find . -name __pycache__` -> none. `git status --porcelain` shows only this iteration's files plus the two untracked spec files.
- PASS artifacts: this record, `CONTEXT.md` rewritten, `DECISIONS.md` D-009..D-011.

## Files
Added: `tests/parallel/check_run.py`, this record. Changed: `tests/parallel/hlib.py` (transcript helpers appended), `tests/parallel/selftest/make_cases.py` (builders + 39 cases), `tests/parallel/selftest/run.sh` (extended expect.json keys; also touched, not listed in the plan's Touches), `CONTEXT.md`, `DECISIONS.md`. Deleted: none.

## Deviations
- `selftest/run.sh` was edited (plan Touches for Iteration 4 omit it) because summary and mark-failed cases need `append_result_out`/`result_file`/`output_contains`; the change is backward compatible (D-011).
- No 3-iteration plan appears anywhere in this iteration; the case plans reuse `base7()` (D-007 not triggered).
- Extra cases beyond the plan: usage-error variants, `Task` tool name, per-message counting, missing result event, run number, summary edge cases.

## Gotchas
- Shell here refuses compound commands and git env var mentions; run `bash selftest/run.sh` plainly. `grep --include` is unsupported by the local ugrep with this form; use file globs.
- Run cases need `repo/` with the plan committed only for `full`; `build_repo` uses `-c user.*` and `GIT_CONFIG_GLOBAL=/dev/null`, nothing global.
- Notes: `subagents: N` is both a note in the result file and a dedicated stdout line (not duplicated as `note:`).
- Exact note for denials: `permission_denials: <json.dumps(list, sort_keys=True)>`.

## For the next iteration
- Add checks with `@check("VC-008", ("full",))` etc. in `check_run.py`; use `hlib.agent_calls`, `group_by_message`, `text_blocks`, `tool_results` and `git(ctx.repo, ...)`.
- `ctx.plan` is an `hlib.Plan` (iterations with `.goal`, `.touches`, `.group`); the Commit -> iteration helper and Member-Agent attribution do not exist yet (Iteration 5 builds them, in `check_run.py`).
- VC-013's tempfile copy is the one place `check_run.py` may create a directory; keep it in a `finally` cleanup.
- Cases: use `_run_case(scenario, transcript, exit, violations, repo_kw=...)`; extend `build_repo` (or add a sibling builder) for realistic histories. Known-good S2 cases must exit 0 under all registered checks, so each bad case must trip exactly one VC.
- The existing `_run_case` repo has a single commit; NFR-001 cases for `full` stay valid because new `full` checks will need richer repos: expect to update those cases' repos/plan when VC-008..011 are registered.
