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
