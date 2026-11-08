# CONTEXT (rewritten in place each iteration)

Plan: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test-plan.md
Spec: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test.md
Harness dir: /Users/fede/devel/fclabs/skills/tests/parallel/ (paths below are relative to it)
Plan decision ids are `D-NNN`; spec decisions are written `spec D5`.

## Current state
- Done: Iteration 1 (fixtures), group A (Iteration 2 `setup.sh`, Iteration 3 `hlib.py` + `check_plan.py` + plan golden cases), reconciled; Iteration 4 (`check_run.py` core: three CLI modes, refusals, NFR-001 cost check, check registry, transcript helpers, run-case golden cases).
- `bash selftest/run.sh` passes 69/69 cases (30 plan + 39 check_run); `bash selftest/vc_setup.sh` prints VC-001/VC-002 PASS.
- `check_run.py` registers only NFR-001 so far. No `run_scenario.sh`, `accept.sh` or README yet. Next: Iteration 5 (VC-008..011, VC-013).
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
- `check_run.py`: S2-S4 checker (registry + NFR-001), `--summary`, `--mark-failed`; creates no directories yet.
- `selftest/make_cases.py`: builds golden cases `<outdir>/<case>/{plan.md,expect.json,...}`; one `case_<name>()` function per case returning `Case(files, expect, build=None)`; also the transcript and repo builders.
- `selftest/run.sh`: builds cases in a temp dir, runs each, asserts exit code, exact violation set, result-file shape, stdout names ids, plus the optional expect.json keys below; exit 0 only if all pass. A case whose checker file is missing FAILS.
- Artifact dir (`specs/01-parallel-skills-test-plan-artifacts/`): `CONTEXT.md`, `DECISIONS.md`, `iterations/01..04`.

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

`hlib` transcript helpers (orchestrator level only; a "message" = events sharing `message.id`, one event per content block; `msg_index` = ordinal by first appearance; `event_index` = index in the full event list so tool_use and tool_result positions compare):
- Dataclasses `ToolUse(event_index,msg_id,msg_index,id,name,input)`, `TextBlock(event_index,msg_id,msg_index,text)`, `ToolResult(event_index,tool_use_id,content,is_error)`, `Transcript(events,init,model,result)`; `AGENT_TOOL_NAMES=("Agent","Task")`.
- `assistant_blocks(events)`, `tool_uses(events, names=None)`, `agent_calls(events)`, `group_by_message(uses) -> {msg_index: [ToolUse]}`, `text_blocks(events)`, `tool_results(events) -> {tool_use_id: ToolResult}`, `result_event(events)`, `permission_denials(events)`, `load_transcript(path) -> Transcript` (HarnessError if missing/unparseable, no init event, no model, or no orchestrator assistant events).

`check_run.py` (Iteration 4):
- Modes: `<repo> <plan.md> --transcript F --run K --scenario {full,downgrade,failing-member} [--result-out F] [--check-skill-source]`; `--summary <results-dir> --scenario {plan,full,downgrade,failing-member}`; `--mark-failed --scenario S --run K --result-out F [--violation skipped|error]`.
- Exit: 0 ok; 1 violations (or summary with < 2 passes); 2 usage/refusal/unparseable (also argparse errors, summary with < 3 files, `--violation` other than skipped/error).
- Check registry: `@check(vc_id, scenarios=RUN_SCENARIOS)` appends `Check(vc_id, scenarios, fn)` to `CHECKS`; `fn(ctx, findings)` with `ctx = Context(repo: Path, plan: hlib.Plan, tr: hlib.Transcript, scenario, run)`; report with `findings.add(vc_id, msg)` (violation) or `findings.notes.append(text)` (note). Iterations 5-6 only add decorated functions.
- Helpers: `git(repo, *args, check=True) -> stdout` and `git_ok(repo, *args) -> bool` (always `git -C`, env `GIT_OPTIONAL_LOCKS=0`), `max_agents(scenario)`, `refuse_repo(repo, scenario)`, constants `MAX_AGENTS_S2=15`, `MAX_AGENTS_OTHER=6`, `PLAN_IN_REPO="specs/tinyshop-plan.md"`.
- Messages (stderr, prefix `check_run.py: error: `): `transcript not found: <path>`, `transcript line N is not JSON`, `transcript has no system init event`, `init event carries no model`, `transcript has no assistant events`, `repository not found: <path>`, `refusing to check the skills repository itself: <top>`, `specs/tinyshop-plan.md is not committed on main in <repo>`, `results directory not found: <d>`, `result file <p> does not have the BR-004 shape`, `summary S: fewer than 3 result files`.
- Stdout: `subagents: N`, `VC-NNN|NFR-001: message` per violation, `note: ...`, final `check_run: OK|FAIL <ids>`; summary prints `summary S: N files, P passed` and `violations: <union or none>`; mark-failed prints one line.
- Notes (all in `Findings.notes`, written to the result file): `subagents: N`, `skill-source check skipped` (or `skill-source check requested but not implemented` with the switch), `permission_denials: <json sorted keys>` when non-empty, `transcript has no result event`, `working tree is dirty` (git status --porcelain non-empty; never an error). `--mark-failed` result: `notes=["marked failed: <v>"]`, `model=""`.
- Refusal order: plan parse, repo (is a dir, git toplevel not the skills repo, plan committed on main for `full` only), then transcript load.

`expect.json`: `{"checker","args","exit","violations"}` plus optional `model`, `scenario`, `run`, `notes_contain` (exact note strings), `passed` (default exit==0), `output_contains` (substrings of stdout+stderr, checked before the exit-2 early return), `append_result_out` (default true; false when args carry `--result-out` or the mode has none), `result_file` (default `result.json`; with `append_result_out` false and no `result_file`, run.sh only looks for the violation ids in stdout). Args run with the case dir as cwd. A `Case` may have `build(casedir)` that creates a repo after files are written.

`make_cases.py` builders (reuse in Iterations 5-6): transcripts `ev_init`, `ev_assistant(mid, block, parent=None)`, `ev_text`, `blk_agent(tuid, isolation=None, name="Agent", prompt)`, `ev_tool_result`, `ev_result(denials)`, `build_transcript(agents, per_message, sub_agents, isolation, tool_name, texts, final_text, denials, model, init, assistant, result) -> jsonl text`; repo `build_repo(path, plan_text=None, commit_plan=True, skills_layout=False, dirty=False)` (git init -b main, one commit, plan at `specs/tinyshop-plan.md`); case helpers `_run_case(scenario, transcript, exit, violations, repo_kw, extra, args, no_repo, no_plan)`, `_run_args`, `_summary_case`, `_mark_case`, `_res`; constants `CHECK_RUN`, `TEST_MODEL`. Case dir layout for run cases: `plan.md`, `transcript.jsonl`, `repo/`.

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
- `check_run.py` never writes in `<repo>`; it writes only `--result-out`. Notes accumulate in `Findings.notes` and are printed as `note:` lines (the `subagents: N` note is printed on its own line instead).
- Subagent shells may refuse compound `&&` commands or ones mentioning git env vars; run `bash selftest/run.sh` plainly.
- Parallel-group worktrees start from the commit at dispatch; members may need `git merge --ff-only` to the latest main to see earlier fixtures.

## Commands
From `/Users/fede/devel/fclabs/skills/tests/parallel`:
- `bash selftest/run.sh` — all golden cases.
- `bash selftest/vc_setup.sh` — VC-001/VC-002 (needs `$TMPDIR` outside any git repo).
- `python3 check_plan.py plan.md --run 1 [--transcript t.jsonl] [--result-out r.json]`
- `python3 check_run.py <repo> plan.md --transcript t.jsonl --run 1 --scenario downgrade [--result-out r.json]`; `python3 check_run.py --summary <dir> --scenario full`; `python3 check_run.py --mark-failed --scenario full --run 2 --result-out r.json [--violation error]`
- `python3 selftest/make_cases.py <outdir>`
- `grep -c '^## Iteration ' fixture/*.tmpl` → 4, 5, 4.

## Known gaps
- D14 `skill-source` check not implemented (notes only; Iteration 9).
- VC-016 `Merge iteration` -> `VC-014` half (Iteration 6); VC-008..015 checks absent (Iterations 5-6); only NFR-001 is registered. VC-013 temp copy (Iteration 5) will be `check_run.py`'s only directory creation.
- Synthetic transcripts follow the spec's Transcript shape, not a real sample (Iteration 9 reconciles).
- `fixture/tinyshop-spec.md` not yet reviewed (VC-023, Iteration 9); it must not change after the hash is recorded.
- Spec/plan text for VC-019 still says "3 iterations"; implementation uses 5 (D-007).
- `setup.sh` does not check that the skills repo contains `write-spec-plan`/`implement-spec-plan`.
