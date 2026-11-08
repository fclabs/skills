# Iteration 6: transcript-text checks (VC-012 notes, VC-014, VC-015)

Commit SHA: see `git log` entry "Add transcript-text checks VC-012, VC-014, VC-015 with golden cases" on `main` (a record cannot hold its own SHA).

## Criteria results
Commands from `/Users/fede/devel/fclabs/skills/tests/parallel`.
- PASS VC-012: `bash selftest/run.sh` -> `selftest: 126/126 cases passed`; case `s2-vc012-findings-are-notes-only` exits 0 with the three VC-012 findings in `notes_contain` and `passed: true`. Manual: `check_run.py <repo> <plan> --transcript <t> --run 1 --scenario full --result-out r.json` -> exit 0, `passed True`, `violations []`, notes list `docs/overview.md ... -artifacts, iteration`, `... the word 'spec'`, `README.md ... plan.md`.
- PASS VC-014, VC-015: same `run.sh` run; 17 S3 and 10 S4 cases, each bad case names exactly its VC id (S3: 11 bad, 4 good, 1 usage; S4: 8 bad, 2 good).
- PASS VC-016: on the built case `s3-bad-vc014-merge-commit-on-main`, `python3 check_run.py repo plan.md --transcript transcript.jsonl --run 1 --scenario downgrade` -> exit 1, prints `VC-014: main has 1 merge commit(s), expected 0`; with `--transcript nonexistent.jsonl` -> exit 2 (`transcript not found`). Also covered by golden cases `s3-bad-vc014-merge-commit-on-main`, `s3-usage-missing-transcript-file`.
- PASS VC-019 (coverage): case/VC table is in `CONTEXT.md` (Current state); VC-003..VC-016 and VC-025 covered; `skill-source` and the real sample remain for Iteration 9; the "3 iteration" variants are 5/7 (D-007, D-013).
- PASS regression: all 94 earlier cases still PASS (the S3/S4-scenario ones were rebuilt, D-019); `bash selftest/vc_setup.sh` -> VC-001 PASS, VC-002 PASS.
- PASS hygiene: `P='dangerously''-skip'; grep -rln -- "$P" *.py *.sh selftest/*` -> none; `grep -rEn 'mkdir|makedirs|mkdtemp' hlib.py check_plan.py check_run.py` -> none; `grep -n tempfile check_run.py` -> lines 26, 374, 377 (VC-013 only); `PYTHONDONTWRITEBYTECODE=1 python3 -c "import hlib, check_plan, check_run"` ok; NFR-002: `git -C <case>/repo status --porcelain | wc -l` -> 0 after a checker run, no `__pycache__` anywhere.
- PASS artifacts: this record; `CONTEXT.md` rewritten in place (134 lines, six sections, check list, helpers, builders, coverage table); `DECISIONS.md` D-016..D-019.

## Files
Changed: `tests/parallel/check_run.py` (text helpers, `check_vc012`, `check_vc014`, `check_vc015`), `tests/parallel/selftest/make_cases.py` (S3/S4/VC-012 builders and 32 new cases; `It.scope_extra`, `s2_transcript(upto=)`; Iteration 4 downgrade/failing-member cases rebuilt), `CONTEXT.md`, `DECISIONS.md`. Added: this record. Deleted: none. `hlib.py` and `selftest/run.sh` untouched (no deviation needed there).

## Deviations
- None from the plan's Scope. Existing cases for the `downgrade`/`failing-member` scenarios were rewritten (same ids/expectations), forced by registering the new checks (D-019).
- VC-012 emits a positive `VC-012: ok:` note so cleanliness is testable without a run.sh change (D-017).

## Gotchas
- Run `python3 check_run.py ...` manually with `PYTHONDONTWRITEBYTECODE=1`, otherwise a `tests/parallel/__pycache__` appears (untracked; remove it).
- Subagent shells may refuse `&&`; run `bash selftest/run.sh` plainly. Selftest takes ~32 s.
- S3 repos are sequential `build_s2_repo` histories (group removed); the merge case adds a `Merge branch side` commit, which maps to no iteration and trips only the merge count.
- S4 repos come from `build_repo` plus unmerged `member-3`/`member-4` branches; the transcript stops after the group (`upto=4`).

## Case vs VC (summary; full table in CONTEXT.md)
VC-012: `s2-vc012-*` (clean, README-only, notes-only findings, missing file, whole-word spec). VC-014: `s3-good-*`, `s3-bad-vc014-*` (after-first-call, missing pyproject/group A/sequential word, pieces in different blocks, no announcement, worktree isolation, one message, overlap, unattributable, merge commit, out-of-order commits). VC-015: `s4-good-*`, `s4-bad-vc015-*` (merge, text without price_cents / -1 / iteration 2, only-last-block rule, two messages, missing isolation, undispatched member). VC-016 run half: merge case plus missing-transcript case.

## For the next iteration
- `check_run.py` is complete apart from D14 and real-shape reconciliation (Iteration 9). Iteration 7 (`run_scenario.sh`) calls `check_run.py <dir> <plan> --transcript T --run K --scenario S --result-out F` and `--mark-failed` / `--summary`; exits: 0 ok, 1 violations, 2 usage; unchanged.
- Result notes now include `VC-012: ...` lines (S2) and `VC-015: unmerged branches: ...` (S4).
