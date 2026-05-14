---
name: write-spec-plan
description: >-
  Generates a detailed, iterative implementation plan from a specification file
  and writes it to a companion markdown file. Use when the user asks to plan,
  break down, or create an implementation plan for a spec, feature, or design
  doc — including phrases like "create an implementation plan", "plan this spec",
  "break this into iterations", "how should I implement this", or any time the
  user provides a spec file and wants a step-by-step build plan. Always use this
  skill instead of improvising a plan format on your own.
---

# Implementation Plan Skill

Generate an iterative implementation plan from a spec file and write it to disk.

## 0. Prerequisite

The spec must have passed `/review-spec` with a verdict of `READY` before a plan is written. If the spec has not been checked, run `/review-spec` first. Do not generate a plan for a spec with unresolved `[MUST]` items.

## 1. Read the spec

Read the full spec file at the path provided. If no path is given, ask the user for it.

## 2. Determine output file path

- If the user provides a destination filename, use it.
- Otherwise, derive it from the spec filename by replacing the extension with `-plan.md`.
  Example: `specs/01-fastapi-server.md` → `specs/01-fastapi-server-plan.md`

## 3. Write the plan

### Header

- Title: `# Implementation Plan: [Feature Name]`
- Spec reference: link or path to the original spec
- Brief summary (2–3 sentences) of what is being built

### Iterations

Split the implementation into self-contained iterations. Each iteration uses this template:

```
## Iteration N: [Name]

**Goal**: One sentence describing what this iteration achieves.

**Scope**:
- Bullet list of what will be implemented (including any docs that are real deliverables for this iteration)

**Success criteria**:
- Concrete, verifiable conditions that must ALL be true before this iteration is complete
- Each criterion references the `VC-NNN` from the spec it satisfies (e.g., "VC-002: …")
- Include specific test commands and expected outcomes

**Commit message**: One-line summary of what this iteration delivers.

---
```

The **final iteration** must include documentation updates as explicit scope items — all docs ship before the final commit, not earlier and not later.

### Iteration rules (enforce in the plan)

1. **Gate** — each iteration may NOT start until the previous iteration's success criteria are fully verified.
2. **Tests green** — every iteration must leave the iteration's own tests passing; the full regression suite is run once at the end (see Final Verification).
3. **Commit** — each iteration ends with a single git commit of all its changes.
4. **Docs in the final iteration** — all documentation updates ship in the last iteration. No half-documented intermediate states.
5. **No orphaned state** — if an iteration is stopped mid-way, the codebase must still build and existing tests must still pass.

### Final Verification

After all iterations, append:

```
## Final Verification

Cross-check each requirement from the original spec:

| Requirement | VC(s)   | Iteration(s) | Verification          |
|-------------|---------|--------------|----------------------|
| FR-001      | VC-001  | Iter 1       | How to verify        |
| BR-002      | VC-004  | Iter 2       | How to verify        |
| ...         | ...     | ...          | ...                  |

**Final acceptance test**: commands to run that prove the full spec is met end-to-end, including the full regression suite.
```

## Format guidelines

- Keep iterations small enough to complete in one focused session — if an iteration feels too large, split it.
- Order iterations so each one delivers a working, testable increment (avoid scaffolding-only iterations with nothing runnable at the end).
- Always reference the spec by section when explaining why something is in scope.
- If the spec is ambiguous, flag the ambiguity explicitly in the relevant iteration rather than silently choosing an interpretation.
