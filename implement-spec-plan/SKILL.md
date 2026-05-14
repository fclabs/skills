---
name: implement-spec-plan
description: >-
  Implements a plan file produced by the write-spec-plan skill, one iteration
  at a time, verifying each iteration's acceptance criteria before advancing.
  Use when the user asks to implement, execute, or build from a plan —
  including phrases like "implement this plan", "start building from the plan",
  "execute the iterations", "build iteration N", or any time the user provides
  a *-plan.md file and wants it built. Always use this skill instead of
  improvising an implementation approach on your own.
---

# Implement Spec Plan Skill

Execute a plan file (produced by `write-spec-plan`) iteration by iteration,
verifying each iteration's acceptance criteria before advancing.

The full regression suite runs **once at the end**, not after each iteration. By default the loop auto-advances on green criteria; if the user says "step me through this" / "interactive", pause for confirmation after each iteration.

## 1. Read the plan

Read the full plan file at the path provided. If no path is given, ask the user for it. Also read the original spec the plan references, so you understand the intent behind each requirement.

## 2. Determine starting iteration

- If the user specifies an iteration number, start there.
- Otherwise start at **Iteration 1** (or the lowest uncompleted iteration if the plan has been partially executed).

## 3. Execute each iteration in order

For every iteration:

### 3a. Announce

Print a short header:
```
## Iteration N: [Name]
Goal: <goal from plan>
```

### 3b. Implement scope

Implement **only** what the iteration's **Scope** lists. If a scope item is ambiguous, stop and ask the user before writing code for it.

### 3c. Verify success criteria

Run every check in the iteration's **Success criteria**, in order. For each: record PASS or FAIL. If any FAILs, fix the issue and re-run the full success-criteria checklist from the top. Do not proceed until every criterion shows PASS.

### 3d. Commit

Create a single git commit with all this iteration's changes, using the **Commit message** draft from the plan (refine wording if needed).

### 3e. Advance

- **Default**: auto-advance to the next iteration.
- **Interactive mode** (when the user invoked the skill with "interactive" / "step me through"): print
  ```
  Iteration N complete. Ready to start Iteration N+1: [Name].
  Proceed? (yes / no / stop here)
  ```
  and wait for confirmation.

## 4. Final verification

After all iterations are complete:

1. Run the project's full test suite. If anything fails, stop, fix the regression, and re-run. Do not declare done until the full suite is green.
2. Confirm the final iteration shipped all documentation updates listed in the plan; if any are missing, add them and amend the final commit (or add a follow-up commit).
3. Run `/verify-spec`, passing the original spec file and the plan file. That skill performs the end-to-end coverage cross-check of every `FR-NNN` and `BR-NNN` against their `VC-NNN`s.

Do not declare the implementation complete until `/verify-spec` reports `PASSED`.

---

## Rules (enforce throughout)

1. **Gate** — never start iteration N+1 until iteration N's success criteria pass and are committed.
2. **No scope creep** — implement exactly what the iteration scope says; refactors and "while I'm here" changes belong in a separate commit or a later iteration.
3. **Working state at every commit** — the codebase must build and the iteration's own tests must pass after each iteration commit. The full regression runs once at the end.
4. **Docs ship in the final iteration** — never partway through.
5. **No orphaned state** — if an iteration is interrupted, the codebase must still build; no half-wired features called by existing code.
6. **Ambiguity blocks progress** — if a scope item is unclear, stop and ask rather than silently picking an interpretation.
