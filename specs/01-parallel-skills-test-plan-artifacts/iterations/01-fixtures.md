# Iteration 1: Fixture spec, plan templates, artifact scaffold

Commit SHA: see `git log` entry "Add tinyshop fixture spec, fixture plan templates and artifact scaffold" (a record cannot hold its own SHA).

## Criteria results
All commands run from /Users/fede/devel/fclabs/skills/tests/parallel.
- PASS: Open Questions exists with no entries. `grep -ci 'open questions' fixture/tinyshop-spec.md` -> 1; section body observed: `None.`
- PASS: `grep -o 'FR-00[1-9]' fixture/tinyshop-spec.md | sort -u | wc -l` -> 9; same with `VC-00[1-9]` -> 9.
- PASS: `grep -cF` for `tinyshop/pricing.py`, `inventory.py`, `shipping.py`, `orders.py`, `cli.py`, `rates.toml`, `tax_bp = 800`, `discount_bp = 1000` -> each >= 1 (2,3,2,2,3,9,2,2).
- PASS: each template contains `@DIR@`, `## Execution Order`, `## Artifact Protocol`, `## Final Verification` (count 1 each, `@DIR@` 21/24/21); `grep -c '^## Iteration '` -> bad 4, failing-member 5, smoke 4.
- PASS: bad plan: group `A` on iterations 2 and 3 only (table and `**Parallel group**` fields); `pyproject.toml` in both Touches lines.
- PASS: failing-member plan contains both `price_cents([]) == 0"` and `price_cents([]) == -1"` commands verbatim (1 each); smoke plan has group `C` on iterations 2 and 3 only.
- PASS: `pyproject.toml` appears in a Touches line of the smoke and failing-member plans only for Iteration 1.
- PASS: token check for VC-001: after `@DIR@` -> `/ABS`, no whitespace token starting with `/` and containing a second `/` lacks the prefix.
- PASS: artifacts exist (`CONTEXT.md` six sections, `DECISIONS.md`, this record); file map matches committed files.

## Files
Added: tests/parallel/fixture/tinyshop-spec.md, bad-group-plan.md.tmpl, failing-member-plan.md.tmpl, smoke-group-plan.md.tmpl; specs/01-parallel-skills-test-plan-artifacts/{CONTEXT.md,DECISIONS.md,iterations/01-fixtures.md}. Changed/deleted: none.

## Deviations
- The fixture spec has VC-010 and BR-001/BR-002 beyond the plan's table (D-001).
- Fixture plan artifact paths use `<stem>-artifacts` where stem is the plan filename without `.md` (e.g. `bad-group-plan-artifacts`), per the plan's hands-off.
- `/review-spec` not run, as instructed.

## Gotchas
- `@DIR@` in a rendered plan must not be followed by text that makes a `/`-token with a different prefix.
- The final-iteration criteria in the templates grep docs for `iteration`/`plan.md`/`-artifacts`; the docs rules in Scope forbid those words.

## For the next iteration
- Iteration 2: `setup.sh` renders `fixture/*.md.tmpl` by replacing every `@DIR@` with `pwd -P` of `<dir>`; output names `bad-group-plan.md`, `failing-member-plan.md`, `smoke-group-plan.md` (strip `.tmpl`).
- Iteration 3: Touches/Group/Depends formats are in CONTEXT.md Public interfaces; Depends lines are like `2, 3`, group cells `A`/`B`/`C`/`—`.
- Do not edit fixture files; if the fixture spec changes, VC-023 must be re-run.
