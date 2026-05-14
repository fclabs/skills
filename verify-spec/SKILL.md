---
name: verify-spec
description: >-
  Verifies that an implementation fully satisfies a spec written with the
  write-spec skill, doing a single end-to-end coverage sweep. Use when the user
  wants to confirm that code matches a spec — including phrases like "verify
  the implementation", "check the spec is met", "run acceptance criteria",
  "does this match the spec", "validate implementation against spec", or any
  time the user wants assurance that what was built satisfies the original
  requirements. Always use this skill instead of improvising a verification
  approach on your own.
---

# Verify Spec Skill

Confirm that the codebase fully satisfies a spec (written with `write-spec`) in a single end-of-implementation sweep. Iteration-level verification is the job of `implement-spec-plan`; this skill is the end-to-end authority.

## 1. Read the inputs

Ask the user for the following if not already provided:

- **Spec file** — the `.md` spec produced by `write-spec`.
- **Plan file** *(optional)* — the `-plan.md` produced by `write-spec-plan`. If absent, treat the entire spec as a single deliverable.

Read both files. Confirm the spec has a **Verification Criteria** section; if missing or empty, stop and warn the user.

## 2. Build the coverage table

From the spec, collect every requirement that must be verified:

- All `FR-NNN`
- All `BR-NNN`
- The end-to-end NFR check, if the spec defines one

Map each requirement to its `VC-NNN`. If any FR or BR has **no corresponding VC**, flag it as an uncovered gap before proceeding — do not skip silently.

## 3. Run the verification sweep

1. For each `VC-NNN`, run its test command exactly once. Record PASS or FAIL.
2. Run the project's full regression suite once.
3. Spot-check documentation: for each doc the plan (or spec) said would ship, confirm the file exists and the relevant section reflects the current implementation. Record doc gaps as findings — they go in the action list, but do not auto-fail the verdict unless the user wants strict mode.

## 4. Produce the coverage table and verdict

```
| Requirement | VC(s) | Status  |
|-------------|-------|---------|
| FR-001      | VC-001| PASSED  |
| BR-002      | VC-004| PASSED  |
| ...         | ...   | ...     |
```

Then:

```
## Spec Verification: PASSED   (or: FAILED)

Regression suite: green / failing
Documentation:    N/N updates verified  (list any gaps)
```

If anything failed, list each failure with the criterion ID, the command, and the observed output.

If any FR or BR has no VC, list it under **Uncovered Gaps** — these block PASSED.

If docs are missing or stale, list them as `[MUST-FIX-BEFORE-MERGE]` items — these do not block PASSED on their own but should block the PR merge.

## 5. Offer a PR (only when PASSED)

```
Verification complete. Would you like me to open a pull request for this
implementation? I can include the coverage table and a test plan checklist
derived from the verification criteria.
```

If the user says yes, create a PR using `gh pr create` with:
- A title referencing the spec or feature name.
- A body that includes a brief summary, the coverage table, the test plan checklist, and the standard `🤖 Generated with Claude Code` footer.

---

## Rules

1. **No skipping** — every `FR` and `BR` in the spec must have at least one executed, passing VC. Uncovered requirements block the PASSED verdict.
2. **Regression must be green** — if the full suite is failing, the verdict is FAILED regardless of VC results.
3. **Honest reporting** — never declare PASSED unless every required check passed. If the user explicitly waives a check, record it as `WAIVED` in the coverage table, not `PASSED`.
4. **Doc gaps surface, but don't block the verdict** — they appear as `[MUST-FIX-BEFORE-MERGE]` items. The user decides whether to ship without docs.
