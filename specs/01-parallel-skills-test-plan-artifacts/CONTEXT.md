# CONTEXT (rewritten in place each iteration)

Plan: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test-plan.md
Spec: /Users/fede/devel/fclabs/skills/specs/01-parallel-skills-test.md
Harness dir: /Users/fede/devel/fclabs/skills/tests/parallel/ (paths below are relative to it)
Plan decision ids are `D-NNN`; spec decisions are written `spec D5`.

## Current state
- After Iteration 1 only fixtures and the artifact scaffold exist. No script, checker or README yet.
- `fixture/tinyshop-spec.md` is a complete, READY-shaped product spec (FR-001..FR-009, VC-001..VC-010, Open Questions: None). It has not been run through `/review-spec` (Iteration 9 does).
- Three complete fixture plan templates exist (`*.md.tmpl`), each containing the token `@DIR@` for the absolute scratch path.
- Next: Iterations 2 and 3 (parallel group A) use these fixtures.

## File map
- `fixture/tinyshop-spec.md`: fixture spec `tinyshop`, ids are its own (header note). Written as an ordinary product spec; does not mention the harness, iterations or groups.
- `fixture/bad-group-plan.md.tmpl`: S3 plan, 4 iterations: 1 scaffold; 2 and 3 in group `A`, both touching `pyproject.toml` (`[tool.x]` / `[tool.y]` tables); 4 docs.
- `fixture/failing-member-plan.md.tmpl`: S4 plan, 5 iterations: 1 scaffold; 2-4 group `B` = pricing, inventory, shipping; 5 docs. Iteration 2 carries the contradictory criteria `price_cents([]) == 0` and `price_cents([]) == -1`.
- `fixture/smoke-group-plan.md.tmpl`: VC-022 plan, 4 iterations: 1 scaffold; 2-3 group `C` = pricing, inventory; 4 docs. All criteria satisfiable.
- Artifact dir: `CONTEXT.md`, `DECISIONS.md`, `iterations/01-fixtures.md`.

## Public interfaces
Fixture spec requirement map (fixture ids, in order): FR/VC-001 scaffold, 002 pricing, 003 inventory, 004 shipping, 005 cli, 006 orders, 007 tax, 008 discount, 009 docs; plus VC-010 end-to-end, BR-001 integer cents, BR-002 stdlib only (>= 3.11). Shared files named in the spec: `pyproject.toml`, `tinyshop/__init__.py`, `tinyshop/cli.py`, `tinyshop/rates.toml`, `docs/`.

Template conventions (checker parsers must accept these):
- Placeholder: literal `@DIR@` = absolute scratch dir, substituted by `setup.sh` (no trailing slash). Plan files are `@DIR@/<name>-plan.md` where `<name>` is `bad-group`, `failing-member`, `smoke-group`; the spec is `@DIR@/specs/tinyshop-spec.md`.
- Artifact directory: `@DIR@/<name>-plan-artifacts/` (rendered plan stem + `-artifacts`), e.g. `@DIR@/bad-group-plan-artifacts/`.
- Group letters: `A` bad, `B` failing member, `C` smoke.
- Execution Order table header: `| Iteration | Depends on | Parallel group | Touches (summary) |`; ungrouped cells are the em dash `—`; Depends cell like `2, 3` or `—`.
- Per-iteration fields (each on one line, bold label then colon outside the bold): `**Goal**: ...`, `**Depends on**: 2, 3` (or `none`; no other digits on the line), `**Parallel group**: `A` — runs concurrently with Iteration 3. Safe because ...` (ungrouped: ``none``, Iteration 1 adds ` (creates the artifact directory).`), `**Touches**: ...`.
- `**Touches**` is one line of comma-separated backticked absolute paths. Grouped iterations list only their own files plus their own record `@DIR@/<name>-plan-artifacts/iterations/NN-<slug>.md`; ungrouped ones also list the artifact `CONTEXT.md` and `DECISIONS.md`. No trailing parentheticals are used.
- Grouped iterations carry, in Scope, the literal strings `iterations/NN-<slug>.md`, `Proposed CONTEXT.md changes`, `Proposed decisions`.
- Goal sentences are unique per plan; iteration headings are `## Iteration N: <Name>`; table rows equal heading count (4, 5, 4).
- Final iteration Scope names backticked `docs/overview.md` and `docs/usage.md` and `README.md`.

Verbatim `Touches` example lines (iteration 2 of each template):
- bad: `**Touches**: `@DIR@/pyproject.toml`, `@DIR@/bad-group-plan-artifacts/iterations/02-tool-x.md``
- failing-member: `**Touches**: `@DIR@/tinyshop/pricing.py`, `@DIR@/tests/test_pricing.py`, `@DIR@/failing-member-plan-artifacts/iterations/02-pricing.md``
- smoke: `**Touches**: `@DIR@/tinyshop/pricing.py`, `@DIR@/tests/test_pricing.py`, `@DIR@/smoke-group-plan-artifacts/iterations/02-pricing.md``

## Conventions & invariants
- Fixtures are static files generated once; they are not produced by any harness script. Edit them by hand only.
- The fixture spec must stay free of the words "plan", "iteration", "parallel", "harness" as product vocabulary.
- Staging is always by explicit path (never `git add -A` in the skills repo); `specs/` other than this artifact dir is untracked and must not be committed.
- Hygiene (ground rule 5): no `.sh`/`.py` file may contain the bypass-permissions flag text; `mkdir`/`makedirs`/`mkdtemp` words only in `setup.sh`, `run_scenario.sh`, `selftest/`, `check_run.py`.
- Harness code is `python3`, stdlib only; fixtures and plans use `python`.

## Commands
- Verify fixtures (from `/Users/fede/devel/fclabs/skills/tests/parallel`): `grep -o 'FR-00[1-9]' fixture/tinyshop-spec.md | sort -u | wc -l` (9); `grep -c '^## Iteration ' fixture/*.tmpl` (4, 5, 4).
- Nothing else to build or run yet.

## Known gaps
- `fixture/tinyshop-spec.md` has not been reviewed with `/review-spec` (VC-023, Iteration 9; hash recorded in README then; the spec file must not change afterwards or VC-023 must be re-run).
- No `setup.sh`, so `@DIR@` substitution is untested (Iteration 2).
- Plan templates were not run through `check_plan.py` (not in scope; they are hand-written).
