# CONTEXT (rewritten in place each iteration)

Plan: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test-plan.md
Spec: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test.md
Harness dir: /Users/fede/devel/fclabs/skills/tests/parallel/ (paths below are relative to it)
Plan decision ids are `D-NNN`; spec decisions are written `spec D5`.

## Current state
- Done: Iteration 1 (fixtures), group A (Iteration 2 `setup.sh`, Iteration 3 `hlib.py` + `check_plan.py` + plan golden cases), reconciled.
- `bash selftest/run.sh` passes 30/30 plan cases; `bash selftest/vc_setup.sh` prints VC-001/VC-002 PASS.
- No `check_run.py`, `run_scenario.sh`, `accept.sh` or README yet. Next: Iteration 4 (`check_run.py` core).
- `fixture/tinyshop-spec.md` has not been run through `/review-spec` (Iteration 9).

## File map
- `fixture/tinyshop-spec.md`: fixture spec `tinyshop` (ids are its own; FR/VC-001..009 plus VC-010, BR-001/002; Open Questions: None). Reads as an ordinary product spec.
- `fixture/bad-group-plan.md.tmpl`: S3 plan, 4 iterations; 2 and 3 in group `A`, both touching `pyproject.toml`.
- `fixture/failing-member-plan.md.tmpl`: S4 plan, 5 iterations; 2-4 group `B` = pricing, inventory, shipping; iteration 2 has contradictory criteria (`price_cents([]) == 0` and `== -1`).
- `fixture/smoke-group-plan.md.tmpl`: VC-022 plan, 4 iterations; 2-3 group `C` = pricing, inventory.
- `setup.sh`: `setup.sh <dir>` builds the scratch repo (FR-001/002).
- `selftest/vc_setup.sh`: verifies VC-001/VC-002 using temp dirs.
- `hlib.py`: shared helpers (plan parsing, Touches/Group/Depends rules, Findings, BR-004 result writer, exit codes, stream-json reader). Stdlib only.
- `check_plan.py`: S1 checker, VC-003..007 and VC-025.
- `selftest/make_cases.py`: builds golden cases `<outdir>/<case>/{plan.md,expect.json,...}`; one `case_<name>()` function per case returning `Case(files, expect)`.
- `selftest/run.sh`: builds cases in a temp dir, runs each, asserts exit code, exact violation set, result-file shape, stdout names ids; exit 0 only if all pass. A case whose checker file is missing FAILS.
- Artifact dir (`specs/01-parallel-skills-test-plan-artifacts/`): `CONTEXT.md`, `DECISIONS.md`, `iterations/01..03`.

## Public interfaces
`setup.sh <dir>`:
- Exit 0 created. Exit 2, changing nothing, on: no/empty/extra argument; non-empty `<dir>`; `<dir>` not a directory; `<dir>` (or nearest existing ancestor) inside a git work tree. Other non-zero = failure (partial output removed).
- Result: repo on `main`, repo-local `user.name=harness` / `user.email=harness@example.invalid`, one commit "Initial scratch repo" by `harness` containing `specs/tinyshop-spec.md`, `READY.md` (`READY`), `.claude/skills/<name>` absolute symlinks to each dir of this repo's `skills/`, `bad-group-plan.md`, `failing-member-plan.md`, `smoke-group-plan.md` (templates with `@DIR@` replaced by `pwd -P` of `<dir>`), `.gitignore` (`__pycache__/`, `.claude/worktrees/`).
- Symlinks come from the script's own location (a worktree copy links that worktree's skills).

`hlib`:
- `class HarnessError(Exception)` (exit-2 conditions); `EXIT_OK/EXIT_FAIL/EXIT_USAGE = 0/1/2`; `SHARED_RESOURCES`, `RESULT_KEYS`.
- `split_sections(text) -> list[tuple[str,str]]`; `field_text(body, label) -> str|None`; `split_row(line) -> list[str]`; `find_table(body) -> (header, rows)|None`.
- `parse_touches(raw, prefixes=(), artifact_name="") -> list[str]`; `strip_prefix(path, prefixes) -> str`; `paths_overlap(a, b) -> bool`; `matches_shared(path, shared=SHARED_RESOURCES) -> str|None`.
- `parse_group(raw|None) -> str|None`; `parse_depends(raw|None) -> set[int]`; `transitive_deps(deps: dict[int,set[int]], n) -> set[int]`.
- `parse_plan(path) -> Plan` (HarnessError if missing/empty/undecodable); `Plan(path,text,artifact_name,header,rows,cols,iterations)` with `.by_n(n)`; `Iteration(n,name,body,goal,touches,depends_field,group_field,row,table_group,table_depends,has_group_col)` with properties `.group`, `.depends`; `scratch_prefixes(path)`.
- `Findings` (`.add(vc,msg)`, `.violations`, `.lines()`, `.notes`); `write_result(path, scenario, run, violations, notes, model) -> dict`; `exit_code(violations) -> 0|1`.
- `read_stream(path) -> list[dict]`; `orchestrator_events(events)`; `init_event(events)`; `init_model(events) -> str` (raise HarnessError on bad input).

`check_plan.py <plan.md> --run K [--transcript F] [--result-out F]`:
- Output: one `VC-NNN: message` line per violation, `note: ...` lines, last line `check_plan: OK|FAIL <ids>`. Ids: VC-003..VC-007, VC-025 only.
- Exit 0 ok, 1 violations, 2 usage/missing/empty/undecodable. Result scenario is `plan`.
- Notes: without `--transcript` `D14/D15 skipped: no --transcript`; with it, `model` is the init-event model and note `skill-source check skipped`.
- Attribution rules: Depends table/field mismatch is VC-005; plan without table or Iteration headings is VC-003 (exit 1). Dependencies come from the table cell, falling back to the field.

`expect.json`: `{"checker","args","exit","violations"}` plus optional `model`, `notes_contain`; args run with the case dir as cwd; `run.sh` appends `--result-out` itself.

Fixture template conventions (parsers must accept):
- Placeholder `@DIR@` = absolute scratch dir, no trailing slash. Plans are `@DIR@/<name>-plan.md` (`bad-group`, `failing-member`, `smoke-group`); spec `@DIR@/specs/tinyshop-spec.md`; artifact dir `@DIR@/<name>-plan-artifacts/`.
- Group letters: `A` bad, `B` failing member, `C` smoke.
- Table header `| Iteration | Depends on | Parallel group | Touches (summary) |`; ungrouped cell is `—`.
- Per-iteration fields on one line: `**Goal**: ...`, `**Depends on**: 2, 3` (or `none`), `**Parallel group**: `A` — ...` (ungrouped: ``none``), `**Touches**: ...` = comma-separated backticked absolute paths, no trailing parentheticals. Grouped members list their own record `.../iterations/NN-<slug>.md`; ungrouped also list artifact `CONTEXT.md`/`DECISIONS.md`.
- Grouped iterations' Scope contains `iterations/NN-<slug>.md`, `Proposed CONTEXT.md changes`, `Proposed decisions`. Final iteration names `docs/overview.md`, `docs/usage.md`, `README.md`.
- Verbatim example (smoke, iteration 2): `**Touches**: `@DIR@/tinyshop/pricing.py`, `@DIR@/tests/test_pricing.py`, `@DIR@/smoke-group-plan-artifacts/iterations/02-pricing.md``

## Conventions & invariants
- Fixtures are static, hand-edited files; no script generates them.
- Staging is always by explicit path (never `git add -A` in the skills repo); `specs/` other than this artifact dir is untracked and must not be committed.
- Hygiene (plan ground rule 5): no `.sh`/`.py` contains the bypass-permissions flag text (build grep patterns by concatenation); `mkdir`/`makedirs`/`mkdtemp` only in `setup.sh`, `run_scenario.sh`, `selftest/`, `check_run.py`.
- Harness code is `python3` stdlib only (>= 3.11); fixtures/plans use `python`. Checkers run with `PYTHONDONTWRITEBYTECODE=1`, `GIT_OPTIONAL_LOCKS=0`.
- Add a golden case: write `case_<name>()` in `selftest/make_cases.py`.
- Known-good plan golden cases use 5 and 7 iterations (D-007).
- Subagent shells may refuse compound `&&` commands or ones mentioning git env vars; run `bash selftest/run.sh` plainly.
- Parallel-group worktrees start from the commit at dispatch; members may need `git merge --ff-only` to the latest main to see earlier fixtures.

## Commands
From `/Users/fede/devel/fclabs/skills/tests/parallel`:
- `bash selftest/run.sh` — all golden cases.
- `bash selftest/vc_setup.sh` — VC-001/VC-002 (needs `$TMPDIR` outside any git repo).
- `python3 check_plan.py plan.md --run 1 [--transcript t.jsonl] [--result-out r.json]`
- `python3 selftest/make_cases.py <outdir>`
- `grep -c '^## Iteration ' fixture/*.tmpl` → 4, 5, 4.

## Known gaps
- D14 `skill-source` check not implemented (notes only; Iteration 9).
- VC-016 check_run half and all `check_run.py` cases absent (Iterations 4-6); no case uses `repo/` yet.
- `fixture/tinyshop-spec.md` not yet reviewed (VC-023, Iteration 9); it must not change after the hash is recorded.
- Spec/plan text for VC-019 still says "3 iterations"; implementation uses 5 (D-007).
- `setup.sh` does not check that the skills repo contains `write-spec-plan`/`implement-spec-plan`.
