# CONTEXT (rewritten in place each iteration)

Plan: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test-plan.md
Spec: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test.md
Harness dir: /Users/fede/devel/fclabs/skills/tests/parallel/ (paths below are relative to it)
Plan decision ids are `D-NNN`; spec decisions are written `spec D5`.

## Current state
- Done: Iteration 1 (fixtures), group A (Iteration 2 `setup.sh`, Iteration 3 `hlib.py` + `check_plan.py` + plan golden cases), reconciled; Iteration 4 (`check_run.py` core); Iteration 5 (git-history checks VC-008..011, VC-013); Iteration 6 (transcript-text checks VC-012 notes, VC-014, VC-015; `check_run.py` is now feature-complete except D14).
- `bash selftest/run.sh` passes 126/126 cases (30 plan + 25 run + 7 summary + 7 mark + 30 S2 + 17 S3 + 10 S4; ~32 s); `bash selftest/vc_setup.sh` prints VC-001/VC-002 PASS.
- No `run_scenario.sh`, `accept.sh` or README yet. Next: Iteration 7 (`run_scenario.sh`).
- `fixture/tinyshop-spec.md` has not been run through `/review-spec` (Iteration 9).

Registered checks in `check_run.py` (`CHECKS`, in this order):
| Check | Scenarios | Gating | Reads |
|---|---|---|---|
| NFR-001 | full, downgrade, failing-member | yes | Agent call count vs `max_agents` |
| VC-008, VC-009, VC-010, VC-011, VC-013 | full | yes | git history, repo copy (Iteration 5) |
| VC-012 | full | NO: notes only (spec D12) | doc files in the working tree |
| VC-014 | downgrade | yes | text blocks, Agent calls, tool_results, `git rev-list --merges`, first-parent commits |
| VC-015 | failing-member | yes (unmerged-branches line is a note) | final text block, Agent calls, `git rev-list --merges`, `git branch --no-merged` |

Golden-case coverage (case-name prefix -> VCs; every bad case exits 1 naming exactly its id):
| Cases | Covers |
|---|---|
| `plan-good-*` (8, incl. 7- and 5-iteration plans, relative/absolute Touches, trailing parenthetical, bare-integer Depends on) / `plan-bad-vc003..vc007,vc025-*` / `plan-usage-*` | VC-003..007, VC-025, VC-016 plan half |
| `run-refuse-*`, `run-usage-*` | VC-017 checker half, VC-016 (missing/unparseable transcript exit 2) |
| `run-nfr001-*` (S2 via `_s2_case`, S3 via `_s3_case`, S4 via `_s4_case`) | VC-020 / NFR-001 |
| `run-good-result-*`, `run-note-no-result-event`, `summary-*`, `mark-failed-*` | VC-018 checker parts, BR-004 shape |
| `s2-good-*` (7 and 5 iterations, ASCII-hyphen Reconcile, empty DECISIONS.md, no groups) / `s2-bad-vc008..vc013-*` | VC-008..011, VC-013 |
| `s2-vc012-*` (5; all exit 0, findings in notes) | VC-012 non-gating |
| `s3-good-*` (4), `s3-bad-vc014-*` (11), `s3-usage-missing-transcript-file` | VC-014, VC-016 run half (`Merge iteration`-style merge on main -> VC-014; missing transcript -> 2) |
| `s4-good-*` (2), `s4-bad-vc015-*` (8) | VC-015 |
Not covered yet: `skill-source` (D14) and the real-sample case (Iteration 9). VC-019's "3-iteration" good plan/repo is 5 by D-007/D-013.

## File map
- `fixture/tinyshop-spec.md`: fixture spec `tinyshop` (ids are its own; FR/VC-001..009 plus VC-010, BR-001/002; Open Questions: None). Reads as an ordinary product spec.
- `fixture/bad-group-plan.md.tmpl`: S3 plan, 4 iterations; 2 and 3 in group `A`, both touching `pyproject.toml`.
- `fixture/failing-member-plan.md.tmpl`: S4 plan, 5 iterations; 2-4 group `B` = pricing, inventory, shipping; iteration 2 has contradictory criteria (`price_cents([]) == 0` and `== -1`).
- `fixture/smoke-group-plan.md.tmpl`: VC-022 plan, 4 iterations; 2-3 group `C` = pricing, inventory.
- `setup.sh`: `setup.sh <dir>` builds the scratch repo (FR-001/002).
- `selftest/vc_setup.sh`: verifies VC-001/VC-002 using temp dirs.
- `hlib.py`: shared helpers (plan parsing, Touches/Group/Depends rules, Findings, BR-004 result writer, exit codes, stream-json reader). Stdlib only.
- `check_plan.py`: S1 checker, VC-003..007 and VC-025.
- `check_run.py`: S2-S4 checker (registry, NFR-001, VC-008..015), `--summary`, `--mark-failed`; its only directory creation is the VC-013 `tempfile` copy.
- `selftest/make_cases.py`: builds golden cases `<outdir>/<case>/{plan.md,expect.json,...}`; one `case_<name>()` function per case returning `Case(files, expect, build=None)`; also the transcript and repo builders (including the S2 builders below).
- `selftest/run.sh`: builds cases in a temp dir, runs each, asserts exit code, exact violation set, result-file shape, stdout names ids, plus the optional expect.json keys below; exit 0 only if all pass. A case whose checker file is missing FAILS.
- Artifact dir (`specs/01-parallel-skills-test-plan-artifacts/`): `CONTEXT.md`, `DECISIONS.md`, `iterations/01..06`.

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
- Git-history helpers (Iteration 5, all in `check_run.py`): `Commit(sha, parents, subject)`; `first_parent_commits(repo) -> list[Commit]` (main, oldest first); `commit_iteration(repo, c) -> int|None` (Commit->iteration: lowest `iterations/NN-*.md` added by the commit, for a merge by `parents[0]..parents[1]`; else `Iteration N` in the subject, case-insensitive; else None); `plan_groups(plan) -> {group: [n,...]}` (table cells); `attribute_agent_calls(plan, calls) -> {n: [ToolUse]}` (verbatim Goal, whitespace-normalised, earliest in prompt; else earliest `Iteration N: <name>`; else dropped); `find_merge(repo, fp, n)` (subject `Merge iteration N: `, else merge commit mapping to n); `branch_base(repo, merge, main_fp)` (fork point of a member branch). Regexes `RECORD_RE`, `MERGE_RE`, `RECONCILE_RE` (en dash or hyphen), `SUBJECT_ITER_RE`; `ARTIFACT_FILES`.
Registered S2 checks (scenario `full`): VC-008 (per group: attributed calls in one `msg_index`, `isolation == "worktree"`, one common fork point; missing merge commit is only a note), VC-009 (per group: ascending `Merge iteration N:` directly followed by exactly one Reconcile for that range, Reconcile touches a `CONTEXT.md`, later commits map to iterations > group max, unmapped is a violation; once: `git worktree list` has one entry), VC-010 (member branch paths within Touches + own `iterations/NN-*.md`, no CONTEXT.md/DECISIONS.md; main has exactly one record per plan iteration; a missing merge is VC-009's finding), VC-011 (every `DECISIONS.md` on main: no `D-?`, heading ids 1..k, `(Iteration N)` non-decreasing; no file at all is a violation), VC-013 (copytree of the working tree to a `tempfile` directory, `sys.executable -m unittest discover`, then `VC013_DRIVER` via `-c`; removed in `finally`).

Transcript-text helpers (Iteration 6, `check_run.py`): `find_text_block(blocks, *patterns) -> TextBlock|None` (first orchestrator text block, transcript order, matching EVERY compiled pattern; matching is per block, a message's text blocks are judged one by one); `final_text(blocks) -> str` (last text block, `""` if none); `first_call(calls) -> ToolUse|None` (lowest `event_index`); `merge_count(repo) -> int` (`git rev-list --merges --count main`); `doc_files(plan) -> list[str]` (backticked `docs/...` paths in the last iteration's `**Scope**` field, de-duplicated, directories and `..` dropped, then `README.md`). Regexes `GROUP_A_RE` (`\b[Gg]roup\W{0,3}A\b`), `SEQUENTIAL_RE` (`sequential|downgrad`, i), `ITERATION_2_RE`, `DOC_FORBIDDEN_RE` (`plan\.md|-artifacts|iterations?\b`, i), `DOC_SPEC_RE` (`\bspec\b`, i). Event order: `TextBlock.event_index` and `ToolUse.event_index` are indices in the full event list, so "announcement precedes call" is `block.event_index < call.event_index` (a text event emitted before a tool_use event of the same message id counts as preceding).
Registered text checks: VC-012 (full; notes only) emits `VC-012: ok: N doc file(s) checked` when clean, else `VC-012: doc file missing: <rel>`, `VC-012: <rel> contains plan/iteration references: <sorted lowercase matches>`, `VC-012: <rel> contains the word 'spec'`. VC-014 (downgrade): the announcement block (group A + pyproject.toml + sequential|downgrad in ONE block) must exist and precede the first Agent call attributed to iteration 2 or 3 (neither attributable, or one missing -> violation); no orchestrator Agent call (any) has `isolation == "worktree"`; calls for 2 and 3 in different `msg_index`es and iteration 2's tool_result `event_index` before iteration 3's call; `merge_count == 0`; first-parent commits mapping to iterations 2 and 3 both exist and 2 comes first. VC-015 (failing-member): `merge_count == 0`; last text block matches `iteration 2` (i) and contains `price_cents` and `-1`; for each plan group, every member has an attributed call, `isolation == "worktree"`, all in one `msg_index` (a plan with no group is a violation); note `VC-015: unmerged branches: a, b` (sorted, or `none`).

Messages (stderr, prefix `check_run.py: error: `): `transcript not found: <path>`, `transcript line N is not JSON`, `transcript has no system init event`, `init event carries no model`, `transcript has no assistant events`, `repository not found: <path>`, `refusing to check the skills repository itself: <top>`, `specs/tinyshop-plan.md is not committed on main in <repo>`, `results directory not found: <d>`, `result file <p> does not have the BR-004 shape`, `summary S: fewer than 3 result files`.
- Stdout: `subagents: N`, `VC-NNN|NFR-001: message` per violation, `note: ...`, final `check_run: OK|FAIL <ids>`; summary prints `summary S: N files, P passed` and `violations: <union or none>`; mark-failed prints one line.
- Notes (all in `Findings.notes`, written to the result file): `subagents: N`, `skill-source check skipped` (or `skill-source check requested but not implemented` with the switch), `permission_denials: <json sorted keys>` when non-empty, `transcript has no result event`, `working tree is dirty` (git status --porcelain non-empty; never an error). `--mark-failed` result: `notes=["marked failed: <v>"]`, `model=""`.
- Refusal order: plan parse, repo (is a dir, git toplevel not the skills repo, plan committed on main for `full` only), then transcript load.

`expect.json`: `{"checker","args","exit","violations"}` plus optional `model`, `scenario`, `run`, `notes_contain` (exact note strings), `passed` (default exit==0), `output_contains` (substrings of stdout+stderr, checked before the exit-2 early return), `append_result_out` (default true; false when args carry `--result-out` or the mode has none), `result_file` (default `result.json`; with `append_result_out` false and no `result_file`, run.sh only looks for the violation ids in stdout). Args run with the case dir as cwd. A `Case` may have `build(casedir)` that creates a repo after files are written.

`make_cases.py` builders (reuse in Iteration 6): transcripts `ev_init`, `ev_assistant(mid, block, parent=None)`, `ev_text`, `blk_agent(tuid, isolation=None, name="Agent", prompt)`, `ev_tool_result`, `ev_result(denials)`, `build_transcript(agents, per_message, sub_agents, isolation, tool_name, texts, final_text, denials, model, init, assistant, result) -> jsonl text`; repo `build_repo(path, plan_text=None, commit_plan=True, skills_layout=False, dirty=False)` (git init -b main, one commit, plan at `specs/tinyshop-plan.md`); case helpers `_run_case(scenario, transcript, exit, violations, repo_kw, extra, args, no_repo, no_plan)`, `_run_args`, `_summary_case`, `_mark_case`, `_res`; constants `CHECK_RUN`, `TEST_MODEL`. Case dir layout for run cases: `plan.md`, `transcript.jsonl`, `repo/`.
S3/S4 builders (Iteration 6): `s3_its()` (4 iterations, group A on 2-3 both touching pyproject.toml), `s4_its()` (`base5` with group B on 2-4), `s3_transcript(its, *, announce=ANNOUNCE, announce_at="before"|"same-message"|"after-first-call", calls="separate"|"one-message"|"overlap", isolation_on, prompt_style="goal"|"none", decoy_texts, final_text, extra, sub_agents, tool_name, denials, model, result)`, `_s3_case(exit, violations, *, tr, merge, reorder, extra, scenario, transcript, dirty, no_plan)` (sequential `build_s2_repo` history; `merge` adds a `--no-ff` merge via `_add_merge`; `reorder` commits iteration 3 before 2), `_s4_case(exit, violations, *, tr, merge, branches=("member-3","member-4"), extra, run)` (`build_repo` + unmerged branches via `_add_branches`; transcript is `s2_transcript(..., final_text=S4_FINAL, upto=4)`), constants `ANNOUNCE`, `S4_FINAL`; `It.scope_extra` adds a Scope bullet (used for doc paths, `_docs_its`); `s2_transcript(..., upto=n)` stops after iteration/group n. Downgrade/failing-member NFR-001 and result-note cases now run on these valid S3/S4 runs (`run-*` cases that used `build_transcript(agents=...)` for those scenarios were rebuilt).
S2 builders: `build_s2_repo(path, its, plan_text, *, defect=None, sep="–", decisions=None, final_files=None)` (real git history for plan `its`: "Add plan", `Iteration N: name` commits, member branches + `--no-ff` merges + Reconcile; final iteration writes tinyshop stubs; defects: diverged-base, merge-order, extra-commit, no-reconcile-context, no-reconcile, worktree-left, late-unmapped, member-context, member-outside, missing-record); `s2_transcript(its, *, extra, extra_per_message, sub_agents, prompt_style="goal"|"name", split_group, no_isolation, skip_members, final_text)` (one Agent call per iteration, group calls in one message; `extra` adds unattributed calls); `_s2_case(its, exit, violations, repo=, tr=, extra=)` (use a fresh `base7()`/`base5()`); constants `ART`, `FINAL_STUBS`, `SMOKE_TEST`. `full` NFR-001 cases now use `_s2_case` (7 plan calls + `extra`).

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
- Known-good plan golden cases and S2 history cases use 5 and 7 iterations (D-007, D-013).
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
- D14 `skill-source` check not implemented (notes only; Iteration 9); no real-sample case yet.
- VC-012/014/015 match synthetic text and tool_use shapes only; real `Agent` inputs (`isolation`, `prompt`), real `tool_result` placement and branch names in S4 are reconciled in Iteration 9.
- VC-014 attribution depends on member prompts quoting the Goal; a real executor that paraphrases would read as `no Agent call is attributable` (see D-016).
- VC-008..011/013 are tested against synthetic transcripts/histories only; real-transcript field shapes (Agent `prompt`/`isolation` input) and real commit shapes are reconciled in Iteration 9.
- VC-013 uses `sys.executable`, not a `python` on PATH (D-014).
- Synthetic transcripts follow the spec's Transcript shape, not a real sample (Iteration 9 reconciles).
- `fixture/tinyshop-spec.md` not yet reviewed (VC-023, Iteration 9); it must not change after the hash is recorded.
- Spec/plan text for VC-019 and Iteration 5 still say "3 iterations"; implementation uses 5 (D-007, D-013).
- `setup.sh` does not check that the skills repo contains `write-spec-plan`/`implement-spec-plan`.
