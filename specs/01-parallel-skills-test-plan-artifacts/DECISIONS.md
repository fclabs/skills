# DECISIONS (append-only)

Ids are the plan's `D-NNN`; spec decisions are cited as `spec D5`.

## D-001: Fixture spec adds VC-010 and two business rules  (Iteration 1)
**Context**: The spec table gives FR/VC-001..009, but `write-spec` requires a VC for every BR and `review-spec` asks for an end-to-end check; VC-023 needs the fixture to review READY.
**Decision**: Added BR-001 (integer cents) and BR-002 (stdlib only, Python >= 3.11) covered by VC-002 and VC-001, and an end-to-end VC-010. FR/VC-001..009 map to A1..A9 unchanged.
**Rejected**: Omitting BRs/end-to-end check (risks a NEEDS WORK review verdict).
**Consequences**: Checks scanning `VC-00[1-9]` still see exactly 9 ids; VC-010 is extra. Do not renumber.

## D-002: Fixture plans generated once, committed as static templates  (Iteration 1)
**Context**: Three near-identical complete plans are tedious and error-prone to hand-edit.
**Decision**: Generated them with a throwaway script kept outside the repo; only the resulting `.md.tmpl` files are committed.
**Rejected**: Committing the generator (would add an unplanned `.py` under the harness hygiene rules).
**Consequences**: Edit the templates directly; keep the three in sync by hand.

## D-003: Touches format in templates  (Iteration 1)
**Context**: The checker parsers (Iteration 3) must accept what the templates use.
**Decision**: One line of backticked absolute `@DIR@/...` paths, no trailing parentheticals, grouped members list their own record file; artifact dir is `@DIR@/<stem>-artifacts/`.
**Rejected**: Relative paths or bulleted lists (the spec's parser handles them, but one format keeps templates uniform).
**Consequences**: Iteration 3 golden cases should also cover bulleted/relative forms themselves.

## D-004: setup.sh cleans up after its own failure  (Iteration 2)
**Context**: FR-002 requires "changes nothing" on refusal; a failure mid-build (git, sed, cp) could leave a half-built `<dir>`.
**Decision**: All refusals run before anything is created. After creation an ERR trap removes the created directory (or empties a pre-existing empty one).
**Rejected**: No cleanup (leaves a non-empty dir that blocks a re-run until deleted).
**Consequences**: A failed run can simply be repeated; the trap deletes only paths setup.sh itself created.

## D-005: setup.sh derives the skills repo from its own location  (Iteration 2)
**Context**: Symlinks must point at the skills version being edited (spec D1) regardless of `$PWD`.
**Decision**: `REPO_ROOT` is `$(dirname setup.sh)/../..` resolved with `pwd -P`; symlink targets are absolute, one per directory in `$REPO_ROOT/skills/`.
**Rejected**: Using `$PWD` or `git rev-parse` (breaks when invoked from elsewhere).
**Consequences**: Running a copy of `setup.sh` under another checkout tests that checkout's skills.

## D-006: Shared hlib.py helper module; D14 as a disabled, noted check  (Iteration 3)
**Context**: check_plan.py and check_run.py both need the Parsing rules, the BR-004 result writer and a stream-json reader; the spec lists no shared file. D14 needs the loaded-skill-path field, unknown until live runs (Iteration 9).
**Decision**: Added stdlib-only `hlib.py` holding all shared parsing and result code. D14 is not a switch in check_plan.py: with `--transcript` it records the init-event model (D15) and only the note `skill-source check skipped`; without it, the note `D14/D15 skipped: no --transcript`.
**Rejected**: Helpers in check_plan.py imported by check_run.py (couples checkers); a `--check-skill-source` switch in check_plan.py (half-built feature).
**Consequences**: Iterations 4-9 extend `hlib.py`. Iteration 9 replaces the note by the real check and updates golden cases' `notes_contain`. (check_run.py in Iteration 4 still wires its own off-by-default switch per the plan.)

## D-007: VC-019 "3 iterations" known-good plan becomes 5  (Iteration 3)
**Context**: VC-019 asks for known-good plans with 7 and 3 iterations. VC-004 needs the three module files in three distinct iterations sharing a non-ungrouped group, and VC-006 needs first and last ungrouped, so the minimum valid tinyshop plan has 5.
**Decision**: Plan golden cases use 7 and 5 iterations. The user approved this change.
**Rejected**: Making VC-004/VC-025 conditional on the plan naming tinyshop modules (would let a plan without modules pass FR-004).
**Consequences**: BR-001 still shown. Spec VC-019 text is stale; do not add a 3-iteration good *plan*. Iteration 5's "3-iteration" S2 repo variants must be re-examined for the same constraint (a repo history need not satisfy plan VCs, but its plan might).

## D-008: Checker attribution and parse-failure rules for plans  (Iteration 3)
**Context**: The spec leaves open which VC owns a Depends-on table/field mismatch and how a plan with no table or headings is classified.
**Decision**: Depends mismatch is VC-005. A plan with no Execution Order table or no Iteration headings is VC-003 (exit 1); only a missing, empty or undecodable file is exit 2. Dependencies for VC-004/005/025 come from the table cell, falling back to the field.
**Rejected**: Exit 2 for a malformed plan (a bad model output would show as an errored run instead of a failed VC).
**Consequences**: Bad cases must be built so exactly one id fires.

## D-009: check_run.py validates transcript shape strictly; skill-source switch only notes  (Iteration 4)
**Context**: The spec says a transcript not matching the recorded shape is a usage error (exit 2); the real shape is unknown until Iteration 9. The plan wants a `--check-skill-source` switch wired but off.
**Decision**: `hlib.load_transcript` raises (exit 2) when the file is missing/unparseable, has no init event, an init event without a model, or no orchestrator-level assistant events. A missing `result` event is only a note. `--check-skill-source` exists; when given it adds the note `skill-source check requested but not implemented`, by default the note `skill-source check skipped`.
**Rejected**: Requiring a `result` event (a killed run yields a partial transcript; D10 maps crashes via the caller, not the checker); silently ignoring the switch.
**Consequences**: Iteration 9 replaces the switch's body and the default note, and updates `notes_contain` in cases.

## D-010: Check registry design and refusal order  (Iteration 4)
**Context**: Iterations 5-6 add ten checks that must share parsing, git access and notes without touching the CLI flow.
**Decision**: `@check(vc_id, scenarios)` registers `fn(ctx, findings)` in `CHECKS`; `ctx` is `Context(repo, plan, tr, scenario, run)`. NFR-001 is itself a registered check. Refusals run before the transcript is loaded: plan parse, repo is a git dir, skills-repo layout, plan committed on `main` (only for `full`).
**Rejected**: Tuples returning (violations, notes) lists (more plumbing than a shared Findings); checking the transcript first (a refused repo should not depend on transcript quality).
**Consequences**: A check adds violations under any id (its own VC or NFR-001); `scenarios` decides when it runs.

## D-011: Summary, mark-failed and expect.json extensions  (Iteration 4)
**Context**: `--summary` and `--mark-failed` take no `--result-out` (or take their own), and the spec leaves open exit codes of `--mark-failed` and what `--summary` prints when it exits 2.
**Decision**: `--mark-failed` exits 0 after writing (the caller already decided the run failed); `--violation` accepts only `skipped|error` (argparse exit 2 otherwise); scenarios `plan|full|downgrade|failing-member`. `--summary` prints `summary S: N files, P passed` and `violations: <union|none>` before exiting, even for exit 2; files that do not have the BR-004 shape are exit 2. expect.json gained `append_result_out`, `result_file`, `output_contains`, `passed`, `scenario`, `run`; `Case` gained `build`.
**Rejected**: Exit 1 for `--mark-failed` (would make run_scenario.sh treat it as a checker failure); a separate runner for non-result modes.
**Consequences**: run.sh stays one runner for every case; later cases can combine the keys freely.

## D-012: Commit->iteration, attribution and fork-point algorithms  (Iteration 5)
**Context**: The spec's Parsing rules leave details open: several records in one commit, merge commits, prompts quoting several Goals, how to find a member's fork point.
**Decision**: A commit maps to the lowest `iterations/NN-*.md` it adds (a merge: what `parents[0]..parents[1]` adds), else the `Iteration N` subject match, else none. An Agent call maps to the Goal (whitespace-normalised) that occurs earliest in its prompt, else the earliest `Iteration N: <name>`. A member's merge is the first-parent commit with subject `Merge iteration N: `, else a merge commit mapping to N. The fork point is found by walking the second-parent chain to the first commit whose parent is on main's first-parent line; all members must agree. A member without a merge commit is VC-009's finding (VC-008 only notes it, VC-010 skips it).
**Rejected**: Failing VC-008/010 as well when merges are missing (one defect would fire three ids).
**Consequences**: Each bad S2 case trips exactly one VC id.

## D-013: S2 repo variants use 5 and 7 iterations, not 3  (Iteration 5)
**Context**: The plan asks for 3-iteration S2 variants; D-007 shows a tinyshop plan cannot be valid (VC-004, VC-006) below 5 iterations, and the case plan must pass the plan rules.
**Decision**: S2 cases use `base5()` and `base7()`; also a good case with no groups (checks that VC-008..010 are vacuous per group). Following D-007 (and the executor brief for this iteration) the reasoning is reused; the spec's VC-019 "3 iterations" and the S2 criterion stay unmet by design.
**Rejected**: A 3-iteration repo with a non-conforming plan (would not model a real S2 run).
**Consequences**: Later records must not claim a 3-iteration case.

## D-014: VC-013 runs the harness interpreter in a tempfile copy  (Iteration 5)
**Context**: The spec says `python -m unittest discover` on a copy; NFR-003 requires both `python` and `python3`.
**Decision**: The copy skips `.git`, `__pycache__` and `.claude`, lives in a `tempfile.TemporaryDirectory` removed in a `finally`, and both the unittest run and the driver use `sys.executable` (the checker's own Python >= 3.11), with `PYTHONDONTWRITEBYTECODE=1`; the first failing step is one VC-013 violation. A `tinyshop` import error in the driver also yields VC-013.
**Rejected**: `python` from PATH (adds an environment dependency to the checker).
**Consequences**: A fixture needing `python` features beyond the checker's interpreter is not detected; live runs use `python` in the plans themselves.

## D-015: S2 check scope and strictness details  (Iteration 5)
**Context**: Spec text leaves edge cases open.
**Decision**: VC-009 requires the merges to sit at consecutive first-parent positions followed immediately by the Reconcile commit (so out-of-order merges, a commit in between and a Reconcile for the wrong range all fail), a Reconcile touching any file named `CONTEXT.md`, and `git worktree list` with exactly one entry, checked once for the run. VC-010's "one record per iteration" means exactly one `iterations/NN-*.md` on main for each plan iteration (zero or two fail). VC-011 checks every `DECISIONS.md` on main, takes ids from headings only, and treats a missing file as a violation.
**Rejected**: Accepting duplicate records; reading ids from the whole text (body cross-references would count).
**Consequences**: Plans with no groups pass VC-008/009 vacuously; VC-010/011/013 still apply.

## D-016: VC-014 text-block matching and attribution edge cases  (Iteration 6)
**Context**: The spec says "the first assistant text block matching ... precedes the first Agent call attributed to iteration 2 or 3" but not how multi-block messages, a single attributable call, or event ties are handled.
**Decision**: Matching is per text block: group A (`\b[Gg]roup\W{0,3}A\b`), `pyproject.toml` and `sequential|downgrad` must all occur in ONE block (pieces spread over blocks fail). The first matching block is compared with the earliest attributed call by position in the event list (`event_index`), so a text event placed before a tool_use of the same message counts as preceding. If neither iteration 2 nor 3 has an attributed call: violation (spec); if only one has: also a violation, and the ordering checks are skipped. "Calls returned" means iteration 2's `tool_result` sits before iteration 3's call in the event list and the two calls are in different assistant messages. Commits for iterations 2 and 3 must both exist on main's first-parent line, 2 first. The isolation check covers every orchestrator Agent call, not only attributed ones.
**Rejected**: Treating a single attributable call as enough (order cannot be verified); pooling all text of a message (the spec says "block").
**Consequences**: A real executor whose member prompts do not quote the iteration Goal reads as unattributable; Iteration 9 must confirm real prompts.

## D-017: VC-012 resolves docs in the working tree and always emits a note  (Iteration 6)
**Context**: VC-012 is non-gating (spec D12); selftest cases can assert only the presence of a note (`notes_contain`), not its absence, and changing `run.sh` is out of scope.
**Decision**: Doc files are the backticked `docs/...` paths in the final iteration's `**Scope**` field (files only, `..` dropped) plus `README.md`, read from the working tree (not `main`). Each problem is one note (`doc file missing`, forbidden plan/artifact/iteration words listed sorted and lowercase, the word `spec`); a clean run emits `VC-012: ok: N doc file(s) checked`, so cases can prove cleanliness. Nothing ever goes to `violations`.
**Rejected**: A silent clean run (untestable without a run.sh change); reading `main:` blobs (the spec says the file exists, and the VC-013 copy already uses the working tree).
**Consequences**: Notes carry the `VC-012:` prefix in the result file for the README's reader.

## D-018: VC-015 scope  (Iteration 6)
**Context**: The spec names "group B" but the checker should not hard-code a letter; "final orchestrator-level assistant text" can span several blocks.
**Decision**: The final text is the last orchestrator text block. The member-call rule applies to every group in the plan (S4's plan has only B) and a plan without any group is a violation, as is a member with no attributed call. Unmerged branches are always a note (`VC-015: unmerged branches: a, b` sorted, or `none`); fewer than two does not fail (spec D3).
**Rejected**: Hard-coded group letter or member numbers (BR-001 favours structure); failing when a passing member's branch is absent (D3 does not require it).
**Consequences**: A final sign-off block after the failure report fails VC-015 (case `s4-bad-vc015-only-earlier-text-names-the-failure`).

## D-019: Downgrade and failing-member cases rebuilt on valid runs  (Iteration 6)
**Context**: Registering VC-014/VC-015 makes every `downgrade`/`failing-member` case run them, so the generic Iteration 4 cases (empty transcripts, `build_transcript(agents=n)`) would trip them.
**Decision**: Cases whose expectation is "exit 0" or "only NFR-001" for those scenarios (`run-nfr001-downgrade/failing-member-*`, `run-good-result-*`, `run-note-no-result-event`, `run-missing-plan-in-repo-ok-for-downgrade`, subagent-not-counted-other) now use `_s3_case` / `_s4_case` with `extra` unattributed Agent calls; expectations and ids are unchanged. Usage-error cases (exit 2) stay as they were.
**Rejected**: Letting those cases expect VC-014/VC-015 as well (muddies the one-id rule); restricting registration (VC-014/015 must run in their scenarios).
**Consequences**: New downgrade/failing-member cases must start from `_s3_case`/`_s4_case`.
