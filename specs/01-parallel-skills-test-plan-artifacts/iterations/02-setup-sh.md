# Iteration 2: setup.sh

Parallel-group A member. Commit SHA: see `git log` entry "Add setup.sh and its VC-001/VC-002 verification script" on the member branch (a record cannot hold its own SHA). CONTEXT.md and DECISIONS.md were not touched.

## Criteria results
All commands run from the worktree root (`tests/parallel/...` relative).
- PASS VC-001: `bash tests/parallel/selftest/vc_setup.sh` printed `VC-001 PASS` (exit 0). Covers, for both an existing empty dir and a nonexistent nested dir: setup.sh exit 0; branch `main`; `rev-list --count HEAD` = 1; author and committer `harness`; repo-local `user.name`/`user.email` = `harness` / `harness@example.invalid`; clean tree; `READY.md` (exactly `READY`), `specs/tinyshop-spec.md`, `.gitignore` (exact two lines), `.claude/skills/write-spec-plan/SKILL.md`, symlink entry; the three plan files exist, no `@DIR@`, mention the real `pwd -P` path, and every whitespace token starting with `/` with a second `/` starts with that path.
- PASS VC-002: same run printed `VC-002 PASS`. Covers: dir with one file (exit 2, `ls -A` unchanged); existing empty subdir and nonexistent nested subdir of a git repo (exit 2, tree unchanged); no argument, empty argument, two arguments (exit 2, nothing created).
- PASS repo status: `git status --porcelain` after the runs listed only `tests/parallel/selftest/` and `tests/parallel/setup.sh` (this iteration's files; the record was added afterwards). The script's temp dir was removed (`ls "$TMPDIR" | grep -c vc_setup` -> 0).
- PASS hygiene: `grep -rn 'dangerously''-skip' tests/parallel --include='*.sh' --include='*.py'` -> no match (rc 1). `mkdir` appears only in `setup.sh` and `selftest/vc_setup.sh`.
- PASS manual spot check: `setup.sh` into a scratchpad dir gave symlinks with absolute targets into this worktree's `skills/`, one commit by `harness`, and 21 substituted paths in `smoke-group-plan.md`.
- PASS artifacts: this record only; CONTEXT.md/DECISIONS.md untouched.

## Files
Added: `tests/parallel/setup.sh`, `tests/parallel/selftest/vc_setup.sh`, `specs/01-parallel-skills-test-plan-artifacts/iterations/02-setup-sh.md`. Changed/deleted: none.

## Deviations
- The worktree was created at 42f9494, before Iteration 1's commit e746db3 (no fixtures or artifact dir). I ran `git merge --ff-only e746db3` on the member branch so the Iteration 1 files exist; no content changed. The merge into the group result is therefore a plain fast-forward-compatible history.
- `setup.sh` also exits 2 for more than one argument or an empty argument, and for an existing non-directory path (beyond the plan text).
- On failure after creation `setup.sh` removes what it created (trap), to leave no orphaned state.
- Commit message in the scratch repo is `Initial scratch repo`, with `--no-verify` and `commit.gpgsign=false` so global hooks or signing cannot interfere.

## Gotchas
- Skill symlink targets resolve from the script location: running `setup.sh` from a worktree links that worktree's `skills/`, not the main checkout's.
- A `@DIR@` replacement uses `sed` with `|` delimiter and escapes `\`, `&`, `|` in the path.
- The scratch temp parent must be outside any git work tree; `vc_setup.sh` aborts (exit 1) if `$TMPDIR` is inside one.
- Do not run the tool's bash in `a && b` forms inside a worktree-isolated agent session: they get refused; run commands separately.

## For the next iteration
- `run_scenario.sh` may rely on `<dir>/specs/tinyshop-spec.md`, `<dir>/READY.md`, `<dir>/{bad-group,failing-member,smoke-group}-plan.md`, `<dir>/.claude/skills/*` symlinks, branch `main`, one clean commit. Exit 2 means refusal (nothing changed), anything else non-zero means failure (partial output removed).
- Invoke the verifier with `bash tests/parallel/selftest/vc_setup.sh` (prints two PASS lines, exit 0). `accept.sh`/`vc_static.sh` (Iteration 8) should call it.
- `<dir>` need not exist, and may be relative; it is made absolute with `pwd -P`.

## Proposed CONTEXT.md changes
- File map: `setup.sh`: `setup.sh <dir>` creates the scratch repo (FR-001/002); `selftest/vc_setup.sh`: verifies VC-001 and VC-002 with temp dirs, prints `VC-001 PASS` / `VC-002 PASS`.
- Public interfaces: `setup.sh <dir>`: exit 0 created; exit 2 on no/empty/extra argument, non-empty `<dir>`, `<dir>` not a directory, or `<dir>` (or nearest existing ancestor) inside a git work tree; nothing is changed on exit 2. Result: repo on `main`, repo-local `user.name=harness`/`user.email=harness@example.invalid`, one commit "Initial scratch repo" by `harness` containing `specs/tinyshop-spec.md`, `READY.md` (`READY`), `.claude/skills/<name>` absolute symlinks to each dir of this repo's `skills/` (repo root derived from the script location), `bad-group-plan.md`, `failing-member-plan.md`, `smoke-group-plan.md` (templates with `@DIR@` replaced by `pwd -P` of `<dir>`), `.gitignore` (`__pycache__/`, `.claude/worktrees/`).
- Commands: `bash tests/parallel/selftest/vc_setup.sh` (VC-001/VC-002, exit 0 iff both pass; needs `$TMPDIR` outside any git repo).
- Known gaps: setup.sh does not check that the skills repo contains `write-spec-plan`/`implement-spec-plan`; symlinks to a worktree's skills if run from a worktree; commit message text is unspecified by the spec and unchecked.

## Proposed decisions
## D-? : setup.sh cleans up after its own failure  (Iteration 2)
**Context**: FR-002 requires "changes nothing" on refusal; a failure mid-build (git, sed, cp) could leave a half-built `<dir>`.
**Decision**: All refusals run before anything is created. After creation an ERR trap removes the created directory (or empties a pre-existing empty one).
**Rejected**: No cleanup (leaves a non-empty dir that blocks a re-run until deleted).
**Consequences**: A failed run can simply be repeated; the trap deletes only paths setup.sh itself created.

## D-? : setup.sh derives the skills repo from its own location  (Iteration 2)
**Context**: Symlinks must point at the skills version being edited (spec D1) regardless of `$PWD`.
**Decision**: `REPO_ROOT` is `$(dirname setup.sh)/../..` resolved with `pwd -P`; symlink targets are absolute, one per directory in `$REPO_ROOT/skills/`.
**Rejected**: Using `$PWD` or `git rev-parse` (breaks when invoked from elsewhere).
**Consequences**: Running a copy of `setup.sh` under another checkout tests that checkout's skills.
