# Iteration 3: hlib.py, check_plan.py, plan golden cases

Commit SHA: see `git log` entry "Add hlib, check_plan.py and plan golden cases with selftest runner" on branch `worktree-agent-a204b91e55a1a1767` (a record cannot hold its own SHA). Parallel-group member (A): CONTEXT.md and DECISIONS.md untouched; the executor reconciles from the two Proposed sections below.

## Criteria results
Commands from the harness dir (worktree `tests/parallel`) with `PYTHONDONTWRITEBYTECODE=1`.
- PASS VC-003/004/005/006/007/025: `bash selftest/run.sh` -> exit 0, `selftest: 30/30 cases passed`, every plan case (good, bad, usage) listed PASS.
- PASS VC-016 (plan half): `python3 check_plan.py <scratch>/plan-bad-vc007-overlap/plan.md --run 1` -> exit 1, output has `VC-007: group A: iterations 2 and 3 overlap on tinyshop/util.py / tinyshop/util.py`; `python3 check_plan.py /nonexistent --run 1` -> exit 2.
- PASS VC-019 (plan part): case list has good plans with 7 (`plan-good-7-iterations`) and 5 iterations (see Deviations), absolute (`plan-good-7-iterations`) and relative bulleted Touches (`plan-good-relative-touches-bullets`), trailing parenthetical (`plan-good-trailing-parenthetical`), bare-integer Depends (`plan-good-bare-integer-depends`).
- PASS BR-004: `--result-out` file validated by `selftest/run.sh` on every exit-0/1 case: exactly the keys scenario, run, passed, violations, notes, model with types str/int/bool/list/list/str; also `cat` of the VC-007 result above.
- PASS VC-021 (partial): `grep -rEn 'mkdir|makedirs|mkdtemp' check_plan.py hlib.py` -> no output; `P='dangerously''-skip'; grep -rn -- "$P" hlib.py check_plan.py selftest` -> no output.
- PASS importable, no bytecode: `python3 -c "import hlib, check_plan"` -> ok; `find . -name __pycache__` -> nothing.
- PASS artifacts: this record has all criteria plus both Proposed sections.

## Files
Added: tests/parallel/hlib.py, tests/parallel/check_plan.py, tests/parallel/selftest/make_cases.py, tests/parallel/selftest/run.sh, this record. Changed/deleted: none.
Branch base: the worktree started before Iteration 1; it was fast-forwarded (`git merge --ff-only e746db3`) to the Iteration 1 commit before work began.

## Deviations
- VC-019 / plan Scope asked for a known-good plan with 3 iterations. Changed to 5 (minimal valid: scaffold, three modules, final iteration holding cli, orders, docs) because VC-004 (three module iterations in one non-ungrouped group) and VC-006 (first and last ungrouped) make 3 impossible. The user approved this. 7 is kept.
- The VC-007 bad case is a hand-built overlapping tinyshop plan, as the plan allows (the bad-group template is not a tinyshop plan).
- Approved judgement calls: a missing Execution Order table or no `## Iteration` headings is VC-003 (exit 1), not exit 2; a table-vs-field `Depends on` mismatch is VC-005; no `--check-skill-source` switch (only the note).
- Extra cases beyond the plan: VC-003 no-table, VC-004 split/non-adjacent, VC-005 depends mismatch, VC-006 last-grouped, VC-007 glob-prefix, VC-025 module-extra-dep, tax/discount group, colon-inside-bold, transcript good/bad, usage-error cases.

## Gotchas
- Sandboxed shell here refuses commands that mention git env vars or are compound; run the selftest as a plain `bash selftest/run.sh`.
- A group-A member that depends transitively on the other members (e.g. last-grouped case) also triggers VC-005; bad cases must be built so exactly one id fires.
- `Iteration.group` is the table cell when the table has a group column and a row for the iteration, else the field value.
- Touches prefix stripping uses the plan's own directory (and its parent when it is `specs/`), plain and realpath forms (macOS `/var` vs `/private/var`).

## For the next iteration
- Reuse `hlib` for stream-json (`read_stream`, `orchestrator_events`, `init_model`) and plan parsing; add check_run cases via `case_<name>()` in `make_cases.py` returning `Case(files, expect)`; `expect.json` may use `repo/` and `transcript.jsonl` files and optional keys `model`, `notes_contain`.
- `run.sh` fails a case whose checker file is missing; it appends `--result-out` and treats exit 2 as "no result file needed".
- Without `--transcript` check_plan notes `D14/D15 skipped: no --transcript`; with it, `skill-source check skipped` and model from the init event (exit 2 if no init/model). Iteration 9 finishes D14.

## Proposed CONTEXT.md changes
**File map** (add):
- `hlib.py`: shared helpers (plan parsing, Touches/Group/Depends rules, Findings, BR-004 result writer, exit codes, stream-json reader). Stdlib only.
- `check_plan.py`: S1 checker, VC-003..007 and VC-025; `<plan.md> --run K [--transcript F] [--result-out F]`.
- `selftest/make_cases.py`: builds golden cases `<outdir>/<case>/{plan.md,expect.json,...}`; one `case_<name>()` function per case.
- `selftest/run.sh`: builds cases in a temp dir, runs each, asserts exit, exact violation set, result shape, stdout names ids; exit 0 only if all pass.

**Public interfaces** (add), `hlib`:
- `class HarnessError(Exception)` exit-2 conditions; `EXIT_OK/EXIT_FAIL/EXIT_USAGE = 0/1/2`; `SHARED_RESOURCES`, `RESULT_KEYS`.
- `split_sections(text) -> list[tuple[str,str]]`; `field_text(body, label) -> str|None`; `split_row(line) -> list[str]`; `find_table(body) -> (header, rows)|None`.
- `parse_touches(raw, prefixes=(), artifact_name="") -> list[str]`; `strip_prefix(path, prefixes) -> str`; `paths_overlap(a, b) -> bool`; `matches_shared(path, shared=SHARED_RESOURCES) -> str|None`.
- `parse_group(raw|None) -> str|None`; `parse_depends(raw|None) -> set[int]`; `transitive_deps(deps: dict[int,set[int]], n) -> set[int]`.
- `parse_plan(path) -> Plan` (HarnessError if missing/empty/undecodable); `Plan(path,text,artifact_name,header,rows,cols,iterations)` with `.by_n(n)`; `Iteration(n,name,body,goal,touches,depends_field,group_field,row,table_group,table_depends,has_group_col)` with properties `.group`, `.depends`; `scratch_prefixes(path)`.
- `Findings` (`.add(vc,msg)`, `.violations`, `.lines()`, `.notes`); `write_result(path, scenario, run, violations, notes, model) -> dict`; `exit_code(violations) -> 0|1`.
- `read_stream(path) -> list[dict]`; `orchestrator_events(events)`; `init_event(events)`; `init_model(events) -> str` (all raise HarnessError on bad input).
- `check_plan.py` output: one `VC-NNN: message` line per violation, `note: ...` lines, last line `check_plan: OK|FAIL <ids>`; violation ids VC-003..VC-007, VC-025 only.
- `expect.json`: `{"checker","args","exit","violations"}` plus optional `model`, `notes_contain`; args run with the case dir as cwd.

**Commands** (add): `bash selftest/run.sh` (all golden cases); `python3 check_plan.py plan.md --run 1 [--transcript t.jsonl] [--result-out r.json]`; `python3 selftest/make_cases.py <outdir>`.

**Known gaps** (add): D14 `skill-source` check not implemented (note only; Iteration 9). VC-016 `check_run.py` half and all check_run cases absent (Iterations 4-6). No case uses `repo/`. 3-iteration known-good plan replaced by a 5-iteration one (VC-004/VC-006 make 3 impossible; spec/plan text still says 3).

## Proposed decisions

## D-? : Shared hlib.py helper module; D14 as a disabled, noted check  (Iteration 3)
**Context**: check_plan.py and check_run.py both need the Parsing rules, the BR-004 result writer and a stream-json reader; the spec lists no shared file. D14 needs the loaded-skill-path field, unknown until live runs (Iteration 9).
**Decision**: Added stdlib-only `hlib.py` holding all shared parsing and result code (no duplication in checkers). D14 is not a switch: check_plan.py with `--transcript` records the init-event model (D15) and only the note `skill-source check skipped`; without it, the note `D14/D15 skipped: no --transcript`.
**Rejected**: Putting helpers in check_plan.py and importing it from check_run.py (couples checkers); a `--check-skill-source` switch (half-built feature, user-approved omission).
**Consequences**: Iterations 4-9 extend `hlib.py` (Touches list of 4 and 9 already includes it). Iteration 9 replaces the note by the real check and updates the golden cases' `notes_contain`.

## D-? : VC-019 "3 iterations" known-good plan becomes 5  (Iteration 3)
**Context**: VC-019 asks for known-good plans with 7 and 3 iterations. VC-004 needs the three module files in three distinct iterations sharing a non-ungrouped group, and VC-006 needs first and last ungrouped, so the minimum valid tinyshop plan has 5.
**Decision**: Golden cases use 7 and 5 iterations. The user approved this change.
**Rejected**: Making VC-004/VC-025 conditional on the plan naming tinyshop modules (would let a plan without modules pass FR-004).
**Consequences**: BR-001 (no iteration-count assertion) is still shown. Spec VC-019 text is stale; do not add a 3-iteration good case.

## D-? : Checker attribution and parse-failure rules for plans  (Iteration 3)
**Context**: The spec leaves open which VC owns a Depends-on table/field mismatch and how a plan with no table or headings is classified.
**Decision**: Depends mismatch is VC-005 (next to the group-field agreement). A plan with no Execution Order table or no Iteration headings is VC-003 (exit 1); only a missing, empty or undecodable file is exit 2. Dependencies for VC-004/005/025 come from the table cell, falling back to the field.
**Rejected**: Exit 2 for a malformed plan (a bad model output would show as an errored run instead of a failed VC).
**Consequences**: Bad cases must be built so exactly one id fires (e.g. a grouped last iteration must depend only on iteration 1).
