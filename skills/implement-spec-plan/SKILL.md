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

Iterations run sequentially unless the plan's **Execution Order** table puts
them in the same **parallel group**. Members of a group run concurrently, each
in its own git worktree, and are merged and reconciled before anything later
starts (see 3e). Everything else in this skill applies to a group member as it
does to a solo iteration unless 3e says otherwise.

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

Check whether git ignores the artifact directory (`git check-ignore -q <dir>`).
If it does, no commit carries the artifacts and nobody runs `git add -f`:
subagents commit code only, the reconciliation in 3e edits the files without
committing them, and the artifact checks at each gate look at the files
instead of the commit.

## 2. Determine starting iteration

- If the user specifies an iteration number, start there.
- Otherwise start at **Iteration 1** (or the lowest uncompleted iteration if the plan has been partially executed).

## 3. Execute each iteration in order — one subagent per iteration

Build the schedule from the plan's `## Execution Order` table (and each
iteration's `Depends on`, `Parallel group`, `Touches`): a list of **steps**,
where a step is either a single iteration or a whole parallel group. Steps run
**sequentially**; each builds on the committed state of the previous step. A
plan with no Execution Order table (an older plan) is fully sequential.

**Validate every group before running it.** Do not trust the plan blindly:
treat the group as sequential if any of these hold — members are not adjacent
or have different `Depends on`; one member depends on another; `Touches`
overlap between members (compare the paths yourself); a member touches a shared
resource (lockfile, dependency manifest, migration, schema, registry/barrel
file, shared config, generated code, fixtures, CI config, docs space); the
group contains Iteration 1 or the final documentation iteration; or a member
lacks `Touches`. Tell the user which group you downgraded and why. A solo
iteration follows 3a–3d; a group follows 3e (which reuses them per member).

For every iteration:

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
  go in the same commit as the code, unless git ignores the artifact directory
  (§1).
- An instruction to stop and report back **without committing** if a scope item
  is ambiguous or a criterion cannot be made to pass.
- The required report format: per-criterion PASS/FAIL with the command run and
  its result, the commit SHA and message, files touched, deviations from the
  plan, the paths of the artifacts it wrote, and any notes the next iteration
  needs.

Wait for the subagent to finish before doing anything else. Outside a validated
parallel group (3e), never run a second iteration's subagent while one is still
in flight.

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

### 3e. Parallel groups

For a validated group of iterations `N…M`:

**Announce** the group: members, goals, and "running concurrently".

**Ask how many run at once.** Parallel subagents spend usage all at once, so
before dispatching a group ask the user how many members to run at the same
time (with `AskUserQuestion` when available), naming the members, how many
subagents that is, and the model they run on: all at once, fewer at a time
(the user says how many), or one at a time. Skip the question when the user
already said how many, or asked you to work non-interactively; then run all at
once.

**Dispatch** the members, as many at once as the user chose, **in a single
message** (multiple Agent calls), each with `isolation: "worktree"` so each has
its own checkout branched from the current HEAD (the committed state before the
group). With fewer at a time, dispatch the next member when one reports; the
gate, merge and reconciliation stay the same. Keep each member's agent id for
messages. Each prompt is built as in 3b, with these changes:

- **Reduced artifact protocol.** The member reads the artifacts as usual but
  must **not** edit `CONTEXT.md` or `DECISIONS.md`. It writes only its own
  `iterations/NN-<slug>.md`, with three extra sections: **Proposed CONTEXT.md
  changes** (exact file-map entries, interfaces, conventions, commands, known
  gaps to add or change), **Proposed decisions** (full `D-NNN`-format entries
  with the number left as `D-?`), and **Messages** (every question it sent and
  every answer it received).
- **Artifacts inside its worktree.** The plan names the artifact directory by
  its absolute path in the main checkout. The member reads and writes it at the
  same repo-relative path inside its own worktree, which holds the artifacts as
  committed before the group, and commits its record with its code. If git
  ignores the artifact directory (§1), the worktree has no copy: the member
  reads the artifacts and writes its record at the absolute path, and commits
  code only.
- **Set up the environment.** A new worktree holds tracked files only: no
  virtualenv, `node_modules`, or untracked config such as `.env`. The member
  sets them up inside its worktree with the install commands in `CONTEXT.md`
  before running any criterion, unless a `WorktreeCreate` hook or a
  `.worktreeinclude` file already did. It never uses the main checkout's
  environment: an editable install there imports the main checkout's code, not
  the worktree's.
- **Questions instead of stopping.** If a scope item is ambiguous, the member
  sends you a message (`SendMessage` to `main`) whose first line is
  `QUESTION iter-NN: <question>`, and keeps working on what does not depend on
  the answer; if nothing is left, it ends its turn without committing. Answer
  it yourself only when the spec, the plan or `DECISIONS.md` states the answer,
  and cite it; anything that takes interpretation goes to the user (rule 10).
  Reply with `SendMessage` to that member's id. When the answer also affects
  other members, send it to every member still running, with the first line
  `GROUP <letter>: <answer>`, and put it in the prompt of members not
  dispatched yet. The member records every question and answer under
  **Messages**, and an answer that settles a decision also as a proposed
  decision.
- **Stay inside `Touches`.** The member must not create or modify any path
  outside its declared `Touches`. If it needs to, it stops and reports without
  committing — that means the plan's disjointness claim was wrong.
- **Commit only its own paths**, staged explicitly by path (never `git add -A`),
  as a single commit in its worktree branch.
- Tell it the other members exist and what they own, so it does not touch their
  area or wait on them. Members never message or depend on each other; only
  you exchange messages with them.
- Same report format as 3b, plus the worktree branch name.

**Gate the group.** Collect all reports and apply 3c to each member. The group
passes only if **every** member is all-PASS and committed with its record
written. The relay to the user lists every question a member asked and its
answer, from the user or from you with the source you cited. If any member
fails or blocks:

- Do not merge anything yet. Fix the failing member via `SendMessage` as in 3c
  (or surface the blocker to the user); the passing members' worktrees stay
  untouched meanwhile.
- If the failure shows the members actually interfere (shared file, hidden
  dependency), use the fallback below from the first interfering member,
  telling the user the plan's parallel marking was wrong.

**Merge.** When all members pass, merge their branches into the main branch one
at a time in iteration order (`git merge --no-ff`, message
`Merge iteration N: <name>`). Because `Touches` are disjoint this should be
clean. Check `git diff --name-only` of each member's commit against its
declared `Touches` first; a path outside it, or any merge conflict, means the
disjointness claim failed for that member: do not merge it (`git merge --abort`
on a conflict) and use the fallback. Do not hand-resolve conflicts.

**Fallback.** Keep the members before the failing one, in iteration order:
merge them if they are not merged yet, and reconcile them as below (step 3
re-runs their criteria on the merged tree). Then run the failing member and
every later member of the group as solo iterations (3a–3d, full artifact
protocol), in iteration order, from the reconciled state, and discard their
group worktrees. The iterations keep the order a sequential run would give
them, and only the members from the failing one on are redone.

**Reconcile.** After the last merge, do this yourself (the one place the
orchestrator edits artifacts; it is bookkeeping, not iteration code):

1. Rewrite `CONTEXT.md` by applying every member's **Proposed CONTEXT.md
   changes** to the pre-group version; resolve overlaps in favour of the lower
   iteration number and keep the file under ~300 lines.
2. Append each **Proposed decision** to `DECISIONS.md`, assigning the next
   `D-NNN` numbers in iteration order, and replace the `D-?` placeholders. A
   `GROUP` answer that settled a decision gets one entry, even if several
   records propose it.
3. Verify the merged tree builds and every member's own tests still pass
   together (run each member's test criteria commands once on the merged
   result). A failure here is a hidden interaction: surface it; do not advance.
4. Commit as `Reconcile artifacts for iterations N–M`, unless git ignores the
   artifact directory (§1).

Only then advance to the next step. Remove the worktrees when done.

**Interactive mode**: confirm once per group, before dispatching it and again
after reconciliation, not per member.

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
2. **Sequential dispatch, except validated groups** — never run two iteration subagents concurrently unless they are members of a parallel group that passed validation in §3 (independent, disjoint `Touches`, no shared resource, adjacent). Group members run in separate worktrees; anything unproven runs sequentially. Each step starts from the previous step's commit.
3. **Gate** — never start the next step until every iteration in the current step has passed its success criteria and is committed — and, for a group, merged and reconciled.
4. **No scope creep** — implement exactly what the iteration scope says; refactors and "while I'm here" changes belong in a separate commit or a later iteration.
5. **Working state at every commit** — the codebase must build and the iteration's own tests must pass after each iteration commit. The full regression runs once at the end.
6. **Context carries forward through artifacts** — each subagent starts fresh and learns the project state from `CONTEXT.md`, `DECISIONS.md`, and the iteration records, not from the orchestrator's memory. Anything a later iteration needs must be written to disk by the iteration that learned it.
7. **Artifacts every iteration** — an iteration is not complete until its record is written and `CONTEXT.md` matches the committed code, no matter how green its code criteria are. For a group member the record carries proposals, and `CONTEXT.md`/`DECISIONS.md` are updated by the reconciliation commit; the group is not complete until that commit lands with no `D-?` placeholders left.
8. **User-facing docs ship in the final iteration** — never partway through. The final subagent reads the whole artifact directory and rewrites it as documentation for a person who was not here: organised by reader need, not iteration order, with the criteria tables, PASS/FAIL records, commit SHAs, and hand-off notes dropped and the decisions and constraints kept. Working artifacts are separate, update every iteration, and are never shipped as the documentation.
9. **No orphaned state** — if an iteration is interrupted, the codebase must still build; no half-wired features called by existing code.
10. **Ambiguity blocks progress** — if a scope item is unclear, a solo iteration's subagent stops and reports, and a group member asks by message (3e); the orchestrator answers only when the spec, the plan or `DECISIONS.md` states the answer, citing it, and otherwise asks the user rather than silently picking an interpretation.
