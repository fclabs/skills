# Iteration 8: accept.sh, static VC checks, README

Commit SHA: see `git log` entry "Add accept.sh, static VC checks and README" on `main` (a record cannot hold its own SHA).

## Criteria results
Commands from `/Users/fede/devel/fclabs/skills/tests/parallel` with `PYTHONDONTWRITEBYTECODE=1`. The real `claude` was never invoked; no money spent.
- PASS VC-021: `bash accept.sh --pre-live` -> exit 0 (~60 s), `accept: OK`; PASS lines for: run.sh (126/126), bypass flag absent, constants defined, flag usage, ALLOWED_TOOLS contains D4's tools, mkdir-words confined, check_run.py tempfile, README prerequisites (git >= 2.28, Python >= 3.11, coreutils, ALLOWED_TOOLS verbatim, model, version/model lines), README sections, `git status --porcelain` unchanged after a checker run (scratch repo and skills repo); the final line `vc_static: 22/22 checks passed`.
- PASS VC-024 (offline part): inside `vc_static.sh` (10 accept.sh cases with `ACCEPT_NO_SUITES=1`): results dir with 2 `plan` files -> exit 1, output `FAIL results: scenario plan has 2 result files, expected 3`; README without VC lines (TBD) -> exit 1 naming VC-022a and VC-023; wrong hash -> 1; `VC-022a: FAIL` -> 1; `passed:false` with empty violations -> 1 naming `full-2.json`; missing dir -> 1; good README + 3 files per scenario (VC-022b FAIL accepted, red result with violations accepted) -> 0; `--pre-live` with TBD README and 2 files -> 0 with `SKIP README ...`; unknown flag -> 2. Manual: `ACCEPT_NO_SUITES=1 WORK=/nonexistent bash accept.sh` -> exit 1, four FAIL lines.
- PASS regression: `bash selftest/run.sh` -> 126/126; `bash selftest/vc_setup.sh` -> VC-001/VC-002 PASS; `bash selftest/vc_runscenario.sh` -> `VC-018 PASS` (all three run inside `accept.sh --pre-live`/`vc_static.sh`; vc_static confirmed the VC-017 and VC-020 cases by name).
- PASS README sections: `grep -c "^## <heading>$" README.md` -> 1 for each of Purpose, Prerequisites, Running the scenarios, Prompts, Directory layout, Reading the results, Reading a red result, Fixture review (VC-023), Cost, Calibrating the constants, Model, Offline checks, Recorded results, Not covered.
- PASS hygiene: `P='dangerously''-skip'; grep -rl -- "$P" *.sh *.py selftest/*.sh selftest/*.py` -> none; `grep -nE 'mkdir|makedirs|mkdtemp' accept.sh hlib.py check_plan.py` -> none; `find . -name __pycache__` -> none; skills repo `git status --short` shows only the new files plus the two untracked specs.
- PASS artifacts: this record; `CONTEXT.md` updated in place (165 lines, six sections; accept.sh, vc_static.sh, README placeholder lines); `DECISIONS.md` D-025..D-027.

## Files
Added: `tests/parallel/accept.sh` (755), `tests/parallel/selftest/vc_static.sh` (755), `tests/parallel/README.md`, this record. Changed: `CONTEXT.md`, `DECISIONS.md`. Deleted: none.

## Deviations
- None from the Scope. Interpretations: D-025 (`ACCEPT_README`/`ACCEPT_NO_SUITES` env hooks), D-026 (run.sh runs once, shared via `--runlog`), D-027 (placeholder lines anchored in a fenced block). README sections `Reading a red result` and `Offline checks` were added beyond the plan's list because the plan asks for their content (D5/D6 text; the offline commands).

## Gotchas
- `vc_static.sh` run alone (no `--pre-live`) reports 2 FAILs (`claude --version: TBD`, `model: TBD`) until Iteration 9: intended.
- macOS grep lacks `--include`; the scans use `find -name`. `sha256sum` exists here, `shasum -a 256` is the fallback.
- vc_static builds golden cases a second time (for the status-unchanged check), ~3 s.
- `accept.sh` creates only a `mktemp` log, no directories.

## For the next iteration
- Iteration 9 costs money; get explicit user confirmation first. It must overwrite README lines in place (`VC-022a: PASS|FAIL`, `VC-022b: PASS|FAIL`, `VC-023: READY sha256=<hash of fixture/tinyshop-spec.md>`, `claude --version: <v>`, `model: <id>`, `D14 skill-path field: <field>`, `S2 first full run: ...` in Iteration 10) and keep them at line start.
- If `ALLOWED_TOOLS` changes, edit `run_scenario.sh` and the README allowlist block together (vc_static checks verbatim equality). If `PROMPT_FORM` default flips, update the README Prompts section.
- `accept.sh` (no flag) is expected to fail until Iteration 10 leaves 3 results per scenario in `$WORK/results`; use `--pre-live` meanwhile.
- Exit codes: accept.sh 0/1/2; run_scenario.sh 0 result written, 1 smoke crash only, 2 usage/refusal.
