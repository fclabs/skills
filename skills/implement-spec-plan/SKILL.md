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

You act as the **orchestrator**: you read the plan, dispatch **one subagent per
iteration**, and gate progress on that subagent's reported result. You do not
implement iteration scope yourself.

The full regression suite runs **once at the end**, not after each iteration. By default the loop auto-advances on green criteria; if the user says "step me through this" / "interactive", pause for confirmation after each iteration.

## 1. Read the plan

Read the full plan file at the path provided. If no path is given, ask the user for it. Also read the original spec the plan references, so you understand the intent behind each requirement.

Note the plan's **Artifact Protocol** section and its artifact directory. That
directory is how iterations hand off to each other: each iteration subagent
reads it before starting and updates it before committing. If the plan has no
Artifact Protocol (an older plan), create the directory next to the plan file as
`<plan-basename>-artifacts/` and hold the subagents to the same protocol:
`CONTEXT.md` (living state, rewritten each iteration), `DECISIONS.md`
(append-only decision log), `iterations/NN-<slug>.md` (one handoff record per
iteration).

## 2. Determine starting iteration

- If the user specifies an iteration number, start there.
- Otherwise start at **Iteration 1** (or the lowest uncompleted iteration if the plan has been partially executed).

## 3. Execute each iteration in order — one subagent per iteration

Iterations run **sequentially**, never in parallel: each one builds on the
committed state of the previous. For every iteration:

### 3a. Announce

Print a short header:
```
## Iteration N: [Name]
Goal: <goal from plan>
Dispatching subagent…
```

### 3b. Dispatch the iteration subagent

Spawn exactly **one** subagent (Agent tool, `general-purpose` unless the plan
names a better-suited agent type) to carry out the whole iteration —
implementation, verification, and commit. Give it a self-contained prompt
containing:

- Absolute paths to the plan file, the original spec file, and the artifact
  directory, with an instruction to read — before writing any code — the spec,
  the plan's Artifact Protocol section and its own iteration, then
  `CONTEXT.md`, `DECISIONS.md`, and the two most recent `iterations/` records.
- The iteration number and name, and its **Goal**, **Scope**, **Success
  criteria**, and **Commit message** draft quoted verbatim from the plan.
- A short pointer to the carry-over from previous iterations — the previous
  iteration's "For the next iteration" section and any deviation you already
  know about. Keep it a pointer, not a transcript: the artifacts are the source
  of truth, and duplicating them into the prompt is how the two drift apart.
- The Rules below, restated as binding constraints on the subagent.
- Instructions to implement only the listed Scope, run every success criterion
  and record PASS/FAIL for each, fix and re-run the full checklist from the top
  on any FAIL, then — before committing — rewrite `CONTEXT.md` to describe the
  codebase as it now stands, append any new decision to `DECISIONS.md`, and
  write `iterations/NN-<slug>.md` with the criteria results, commit-ready file
  list, deviations, gotchas, and a "For the next iteration" section. Artifacts
  go in the same commit as the code.
- An instruction to stop and report back **without committing** if a scope item
  is ambiguous or a criterion cannot be made to pass.
- The required report format: per-criterion PASS/FAIL with the command run and
  its result, the commit SHA and message, files touched, deviations from the
  plan, the paths of the artifacts it wrote, and any notes the next iteration
  needs.

Wait for the subagent to finish before doing anything else. Never run a second
iteration's subagent while one is still in flight.

### 3c. Gate on the subagent's report

Relay a condensed version of the report to the user — the subagent's output is
not shown to them. Then:

- **All criteria PASS and committed** → check the artifacts before advancing:
  `iterations/NN-<slug>.md` exists, and `CONTEXT.md` was touched by this
  iteration's commit (`git show --stat HEAD`) and its file map and public
  interfaces match what the report says shipped. Stale or missing artifacts are
  a FAIL — send the subagent back to write them, since the next subagent has no
  other way to learn what happened. Then proceed to 3d.
- **Any FAIL, or blocked/ambiguous** → do not advance. Surface the blocker. If
  it is an ambiguity or a decision for the user, ask them. If it is a
  mechanical failure the subagent merely ran out of room on, dispatch a
  follow-up subagent (via `SendMessage` to the same agent, so it keeps its
  context) with the specific fix; then re-gate.
- **Report claims success but is unverifiable** (no commit SHA, criteria
  described rather than run) → verify yourself with a quick `git log` / re-run
  of the cheapest criteria before advancing.

### 3d. Advance

- **Default**: auto-advance to the next iteration. The next subagent's prompt
  points at the artifacts rather than restating them; add inline only what the
  artifacts do not yet capture.
- **Interactive mode** (when the user invoked the skill with "interactive" / "step me through"): print
  ```
  Iteration N complete. Ready to start Iteration N+1: [Name].
  Proceed? (yes / no / stop here)
  ```
  and wait for confirmation.

## 4. Final verification

After all iterations are complete, do this work yourself as the orchestrator —
final verification is not delegated:

1. Run the project's full test suite. If anything fails, stop, fix the regression, and re-run. Do not declare done until the full suite is green.
2. Confirm the final iteration synthesised the artifacts into human-oriented documentation in the plan's documentation space: every doc file the plan names exists, reads as standalone documentation rather than a build log, and references neither the plan, the spec, nor the artifact directory. Missing or artifact-shaped docs are a blocker — send the final iteration's subagent back to write them properly rather than patching them yourself.
3. Confirm the artifact directory reflects the shipped system: `CONTEXT.md` describes the finished state rather than an intermediate one, `DECISIONS.md` covers the non-obvious choices, and `iterations/` holds one record per iteration.
4. Run `/verify-spec`, passing the original spec file and the plan file. That skill performs the end-to-end coverage cross-check of every `FR-NNN` and `BR-NNN` against their `VC-NNN`s.

Do not declare the implementation complete until `/verify-spec` reports `PASSED`.

---

## Rules (enforce throughout)

1. **One subagent per iteration** — every iteration's implementation runs in its own subagent; the orchestrator plans, dispatches, gates, and reports, and does not write iteration code itself.
2. **Sequential dispatch** — never run two iteration subagents concurrently; each starts from the previous iteration's commit.
3. **Gate** — never start iteration N+1 until iteration N's success criteria pass and are committed.
4. **No scope creep** — implement exactly what the iteration scope says; refactors and "while I'm here" changes belong in a separate commit or a later iteration.
5. **Working state at every commit** — the codebase must build and the iteration's own tests must pass after each iteration commit. The full regression runs once at the end.
6. **Context carries forward through artifacts** — each subagent starts fresh and learns the project state from `CONTEXT.md`, `DECISIONS.md`, and the iteration records, not from the orchestrator's memory. Anything a later iteration needs must be written to disk by the iteration that learned it.
7. **Artifacts every iteration** — an iteration is not complete until its record is written and `CONTEXT.md` matches the committed code, no matter how green its code criteria are.
8. **User-facing docs ship in the final iteration** — never partway through. The final subagent reads the whole artifact directory and rewrites it as documentation for a person who was not here: organised by reader need, not iteration order, with the criteria tables, PASS/FAIL records, commit SHAs, and hand-off notes dropped and the decisions and constraints kept. Working artifacts are separate, update every iteration, and are never shipped as the documentation.
9. **No orphaned state** — if an iteration is interrupted, the codebase must still build; no half-wired features called by existing code.
10. **Ambiguity blocks progress** — if a scope item is unclear, the subagent stops and reports; the orchestrator asks the user rather than silently picking an interpretation.
