# Iteration 5: git-history and end-to-end checks (VC-008..011, VC-013)

Commit SHA: see `git log` entry "Add check_run.py git-history and end-to-end checks (VC-008..011, VC-013) with golden cases" on `main` (a record cannot hold its own SHA).

## Criteria results
Commands from `/Users/fede/devel/fclabs/skills/tests/parallel`.
- PASS VC-008, VC-009, VC-010, VC-011, VC-013: `bash selftest/run.sh` -> `selftest: 94/94 cases passed` (~25 s wall). New cases (25): good `s2-good-7-iterations`, `-5-iterations`, `-reconcile-ascii-hyphen`, `-empty-decisions`, `-attribution-by-iteration-name`, `-no-groups`, `-result-notes`; bad `s2-bad-vc008-{members-in-two-messages,missing-isolation,member-not-dispatched,diverged-fork-points}`, `vc009-{merge-order,extra-commit-before-reconcile,reconcile-without-context,no-reconcile-commit,worktree-left-behind,unmapped-commit-after-reconcile}`, `vc010-{member-changes-context,member-outside-touches,member-record-missing}`, `vc011-{placeholder-id,id-gap,decreasing-iterations}`, `vc013-{unittest-fails,wrong-tax}`. Each bad case asserts exit 1 with exactly its VC id.
- PASS VC-019 (S2 part): ASCII-hyphen Reconcile, empty `DECISIONS.md`, 5- and 7-iteration cases exist. The "3-iteration" variants are replaced by 5 (D-013; same reasoning as D-007).
- PASS NFR-002: built cases in a temp dir, ran `check_run.py` on `s2-good-7-iterations` (exit 0) with `PYTHONDONTWRITEBYTECODE=1`: `git -C repo status --porcelain | wc -l` -> 0 before and after; `find repo -name __pycache__ | wc -l` -> 0; no `vc013-*` directory left in `$TMPDIR`. `grep -n tempfile check_run.py` -> lines 26 (import), 374 (docstring), 377 (`tempfile.TemporaryDirectory`).
- PASS VC-016 (run half, partial): unchanged (`run-usage-missing-transcript` still exit 2).
- PASS regression: all 69 earlier cases still PASS (full NFR-001 cases rebuilt on S2 histories); `bash selftest/vc_setup.sh` -> VC-001 PASS, VC-002 PASS.
- PASS hygiene: `grep -rEn 'mkdir|makedirs|mkdtemp' hlib.py check_plan.py check_run.py` -> none; `P='dangerously''-skip'; grep -rln -- "$P" *.py *.sh selftest/*` -> none; `python3 -c "import hlib, check_plan, check_run"` ok; no `__pycache__` in the tree; `git status --porcelain` shows only this iteration's files plus the two untracked spec files.
- PASS artifacts: this record, `CONTEXT.md` rewritten (107 lines), `DECISIONS.md` D-012..D-015.

## Files
Changed: `tests/parallel/check_run.py` (git helpers, 5 checks, VC013_DRIVER), `tests/parallel/selftest/make_cases.py` (S2 builders and cases; `_nfr` and the full subagent-not-counted case now use `_s2_case`), `CONTEXT.md`, `DECISIONS.md`. Added: this record. Deleted: none. `hlib.py` and `selftest/run.sh` untouched.

## Deviations
- 3-iteration S2 variants replaced by 5 and 7 (D-013). An extra good case without groups was added.
- `full` NFR-001 cases (15/16, counts-calls-not-messages, subagent-not-counted) were rewritten to use a good S2 history plus `extra` unattributed Agent calls; the plan's cases are otherwise unchanged.

## Gotchas
- Shell constraints as before: run `bash selftest/run.sh` plainly; no `grep --include`.
- The case plan's `Touches` are scratch-prefix-stripped relative paths; record paths in the repo (`specs/tinyshop-plan-artifacts/iterations/NN-*.md`) are accepted by regex, not by `Touches` (plan artifact dir is dropped from Touches).
- Reconcile/member synthetic histories use real `git merge --no-ff`; `worktree-left` creates `<case>/leftover-wt` outside `repo/`.
- A member without a merge commit makes VC-008 add only a note (VC-009 reports it).

## For the next iteration
- Add VC-012 (notes only), VC-014, VC-015 with `@check`; scenarios `downgrade` / `failing-member` / `full`. Reuse `attribute_agent_calls(plan, calls)`, `first_parent_commits`, `commit_iteration`, `hlib.text_blocks`, `hlib.tool_results`, `hlib.group_by_message`.
- For S3/S4 cases build repos with `build_repo` or `build_s2_repo` (sequential history gives a no-merge main); `s2_transcript` handles sequential prompts but not text blocks: extend it or use `build_transcript(texts=...)`. The bad-group plan has group A on iterations 2 and 3, so the case plan needs a matching `It` list.
- `ctx.plan.iterations[i].name` is the title-cased heading name; `it.goal` is the Goal text.
- Real-transcript reconciliation (Agent `prompt`/`isolation` input keys, skill path) is Iteration 9.
