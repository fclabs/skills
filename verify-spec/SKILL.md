---
name: verify-spec
description: >-
  Verifies that an implementation fully satisfies a spec written with the
  write-spec skill, one iteration at a time. Use when the user wants to confirm
  that code matches a spec — including phrases like "verify the implementation",
  "check the spec is met", "run acceptance criteria", "does this match the spec",
  "validate implementation against spec", or any time the user wants assurance
  that what was built satisfies the original requirements. Always use this skill
  instead of improvising a verification approach on your own.
---

# Verify Spec Implemented Skill

Confirm that the codebase fully satisfies a spec (written with `write-spec`)
by walking through each iteration's acceptance criteria, running full regression
tests, and verifying documentation is up to date.

## 1. Read the inputs

Ask the user for the following if not already provided:

- **Spec file** — the `.md` spec produced by `write-spec`.
- **Plan file** *(optional but recommended)* — the `-plan.md` produced by
  `write-spec-plan`. If absent, treat the entire spec as a single iteration:
  run all `VC-NNN` criteria from the spec's Verification Criteria section,
  then run the full regression suite.
- **Starting iteration** — default to Iteration 1 (or the lowest unverified
  iteration if partially complete).

Read both files in full before proceeding. Confirm the spec has a
**Verification Criteria** section; if it is missing or empty, stop and warn the
user — a spec without VCs cannot be verified.

## 2. Determine the verification scope

From the spec, collect every requirement that must be verified:

- All `FR-NNN` (Functional Requirements)
- All `BR-NNN` (Business Rules)
- All measurable `NFR-NNN` (Non-Functional Requirements)

Build a checklist mapping each requirement to its `VC-NNN` criteria. If any
FR, BR, or measurable NFR has **no corresponding VC**, flag it as a gap before
proceeding — do not skip it silently.

## 3. Verify one iteration at a time

Repeat the loop below for every iteration until all are complete.

---

### Iteration verification loop

#### 3a. Announce the iteration

```
## Verifying Iteration N: [Name]
Scope: <summary of what this iteration was supposed to deliver>
```

#### 3b. Verify acceptance criteria

Run every check listed in the iteration's **Success criteria**, in order.
For each criterion:

1. Run the exact command given (or the closest equivalent — flag any deviation).
2. Record the outcome: **PASS** or **FAIL**.
3. If any criterion **FAILs**, stop immediately. Report:
   - Which criterion failed and why.
   - Whether the failure is in the implementation or in the test/command itself.
   Do **not** move to the next criterion or the next iteration until all
   failures are resolved and the full checklist re-runs clean from the top.

Do not proceed to 3c until every criterion shows PASS.

#### 3c. Verify documentation updates

Check every documentation update that the plan (or spec) required for this
iteration:

- For each listed doc, confirm the file exists and contains the expected content.
- Spot-check: read the relevant section to verify the update reflects the
  current implementation, not a stale draft.
- If a doc is missing or its content does not match what was built, record it
  as a **FAIL** and stop — documentation gaps are blocking failures, not
  warnings.

#### 3d. Run full regression tests

After all acceptance criteria and doc checks pass, run the project's full test
suite to catch regressions:

- Use the test command defined in the project (e.g. `pytest`, `npm test`,
  `go test ./...`). If there is no obvious command, ask the user.
- If any pre-existing test fails, stop, report the failure, and do not advance
  to the next iteration until the full suite is green.

#### 3e. Report iteration result

```
Iteration N: [Name] — PASSED
  Acceptance criteria: N/N passed
  Documentation:       N/N updates verified
  Regression suite:    green
```

If anything failed:

```
Iteration N: [Name] — FAILED
  [List each failure with criterion ID and description]
```

#### 3f. Confirm before continuing

After a passing iteration, ask:

```
Iteration N verified. Ready to check Iteration N+1: [Name].
Proceed? (yes / no / stop here)
```

Wait for the user's confirmation before starting the next iteration.

---

## 4. Final spec coverage check

After all iterations pass, perform a full cross-check of the original spec:

1. For every `FR-NNN`, `BR-NNN`, and measurable `NFR-NNN`, confirm:
   - At least one `VC-NNN` covers it.
   - That VC was executed and passed in one of the iterations.
2. Produce a coverage table:

```
| Requirement | VC(s) | Iteration | Status  |
|-------------|-------|-----------|---------|
| FR-001      | VC-001| 1         | PASSED  |
| BR-002      | VC-004| 2         | PASSED  |
| ...         | ...   | ...       | ...     |
```

3. Report any requirement with no VC or with a failing VC as an **uncovered gap**.
   Do not declare the spec fully verified if any gap exists.

## 5. Declare result

If all requirements are covered and all tests are green:

```
## Spec Verification: PASSED

All functional requirements, business rules, and measurable NFRs are covered
by passing verification criteria. Regression suite is green. Documentation
is up to date.
```

Then offer to create a pull request:

```
Verification complete. Would you like me to open a pull request for this
implementation? I can include the coverage table and a summary of what was
verified in the PR description.
```

If the user says yes, create a PR using `gh pr create` with:
- A title that references the spec or feature name.
- A body that includes:
  - A brief summary of what was built.
  - The full coverage table from step 4.
  - A test plan checklist derived from the verification criteria.
  - The standard `🤖 Generated with Claude Code` footer.

---

## Rules (enforce throughout)

1. **Gate** — never advance to iteration N+1 until iteration N's acceptance
   criteria, documentation checks, and regression suite are all passing.
2. **No skipping** — every `FR`, `BR`, and measurable `NFR` in the spec must
   have at least one executed, passing VC. Unverified requirements block the
   final PASSED declaration.
3. **Docs are not optional** — missing or stale documentation is a blocking
   failure, not a warning.
4. **Regression must be green** — the full test suite must pass after every
   iteration; no known failures may be left.
5. **Gaps block success** — if a requirement has no VC, flag it immediately in
   step 2 and do not proceed until the user either adds the VC or explicitly
   descopes the requirement.
6. **Honest reporting** — never declare PASSED unless every check passed. If
   the user asks to skip a check, record it as explicitly waived in the
   coverage table, not as PASSED.
