---
name: implement-spec-plan
description: >-
  Implements a plan file produced by the write-spec-plan skill, one iteration
  at a time, verifying acceptance criteria and running full regression tests
  before advancing. Use when the user asks to implement, execute, or build from
  a plan — including phrases like "implement this plan", "start building from
  the plan", "execute the iterations", "build iteration N", or any time the
  user provides a *-plan.md file and wants it built. Always use this skill
  instead of improvising an implementation approach on your own.
---

# Implement Spec Plan Skill

Execute a plan file (produced by `write-spec-plan`) iteration by iteration,
verifying all acceptance criteria and running full regression tests before
advancing to the next iteration.

## 1. Read the plan

Read the full plan file at the path provided. If no path is given, ask the
user for it. Also read the original spec the plan references, so you
understand the intent behind each requirement.

## 2. Determine starting iteration

- If the user specifies an iteration number, start there.
- Otherwise start at **Iteration 1** (or the lowest uncompleted iteration if
  the plan has been partially executed).
- Before starting, confirm with the user which iteration to begin and show a
  one-line summary of its goal.

## 3. Execute each iteration in order

Repeat the loop below for every iteration until all are complete.

---

### Iteration loop

#### 3a. Announce the iteration

Print a short header:

```
## Iteration N: [Name]
Goal: <goal from plan>
```

#### 3b. Implement the scope

Implement **only** what the iteration's **Scope** section lists.
Do not implement anything listed under **Out of scope**.
If you discover that a scope item is ambiguous, stop and ask the user before
writing any code for it.

#### 3c. Update documentation

Before running any verification, apply every documentation update listed in
the iteration's **Documentation updates** section:

- Update API docs, usage guides, README sections, and inline docstrings.
- If a listed doc does not exist yet, create it.
- Documentation must be committed together with the code — never deferred.

#### 3d. Verify the iteration's acceptance criteria

Run every check listed in the iteration's **Success criteria**, in order.
For each criterion:

1. Run the exact command given (or the closest equivalent if the plan is
   slightly out of date — flag the deviation).
2. Record the outcome: PASS or FAIL.
3. If any criterion FAILs, **stop**, fix the issue, and re-run the full
   success-criteria checklist from the top before continuing.

Do not proceed to 3e until **every** criterion shows PASS.

#### 3e. Run full regression tests

After all iteration criteria pass, run the project's full test suite to
catch regressions introduced by this iteration's changes.

- Use the test command defined in the project (e.g. `pytest`, `npm test`,
  `go test ./...`). If there is no obvious command, ask the user.
- If any pre-existing test fails, **stop**, fix the regression, and re-run
  the full suite before continuing.
- Do not advance to the next iteration until the full suite is green.

#### 3f. Commit the iteration

Create a single git commit that includes:

- All code changes for this iteration.
- All documentation updates for this iteration.

Use the **Commit message** draft from the plan as the commit message (refine
the wording if needed, but keep the intent).

#### 3g. Confirm before continuing

After committing, report:

```
Iteration N complete. All success criteria passed. Regression suite green.
Ready to start Iteration N+1: [Name] — goal: <goal>.
Proceed? (yes / no / stop here)
```

Wait for the user's confirmation before starting the next iteration.

---

## 4. Final verification

After all iterations are complete, run the `/verify-spec` skill,
passing the original spec file and the plan file. That skill performs a
complete cross-check of every `FR-NNN`, `BR-NNN`, and measurable `NFR-NNN`
against their `VC-NNN` criteria, confirms documentation is up to date, and
offers to open a PR when everything passes.

Do not declare the implementation complete until `/verify-spec`
reports `PASSED`.

---

## Rules (enforce throughout)

1. **Gate** — never start iteration N+1 until iteration N's success criteria
   and regression suite are fully green and committed.
2. **No scope creep** — implement exactly what the iteration scope says;
   refactors, cleanups, or "while I'm here" changes belong in a separate
   commit or a later iteration.
3. **Tests green at every commit** — the codebase must be in a working,
   passing state after each iteration commit; no known failures may be left.
4. **Docs ship with code** — documentation updates are part of the iteration
   commit, never a follow-up.
5. **No orphaned state** — if an iteration is interrupted, the codebase must
   still build and all existing tests must still pass; no half-wired features.
6. **Ambiguity blocks progress** — if a scope item is unclear, stop and ask
   rather than silently picking an interpretation.
