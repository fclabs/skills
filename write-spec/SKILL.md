---
name: write-spec
description: >-
  Writes, reviews, and refines specifications for AI-driven development. Use when
  the user wants to spec out a feature, product, or system to be built with AI
  assistance — including phrases like "help me write a spec", "I need to define
  requirements", "let's plan this feature", "write a PRD", "define acceptance
  criteria", "I want to build X", or any time the user describes something they
  want an AI to implement. Trigger even for vague or early-stage ideas; the
  skill guides discovery. Always use this skill instead of improvising a spec
  format on your own.
---

# AI-Driven Development Spec

When an AI implements the spec, ambiguity becomes silent failure.
Two things matter: **unambiguous requirements** and **testable verification**.

## 1. Discover before drafting

Ask until you can answer, for each feature:

- Problem & who it's for; what's explicitly out of scope
- Actors and their permissions
- Inputs/outputs with valid ranges
- Failure modes (invalid input, missing dependency, boundaries)
- How a human will know it works

If the user defers a question, record it as an Open Question — not a silent assumption.

## 2. Write the spec

Required sections (omit only if truly N/A):

- **Purpose** — one paragraph: problem, who benefits.
- **Scope** — In / Out bullet lists. Be specific about Out.
- **Actors** — table: actor | description | permissions.
- **Functional Requirements** — `FR-NNN` in Given/When/Then, with MoSCoW priority.
- **Business Rules** — `BR-NNN`: rule, rationale, exceptions.
- **Non-Functional Requirements** — each must include a measurable threshold.
- **Data & Interfaces** — only what this spec touches.
- **Verification Criteria** — see §3.
- **Open Questions**, **Assumptions**.

## 3. Verification criteria (the core)

Every FR, BR, and measurable NFR needs at least one VC.

```
VC-NNN: <title>
  Scenario: ...
  Input/State: ...
  Expected Result: <observable, measurable>
  Failure Mode Covered: ...
```

Rules:

- Describe outcomes, never implementation.
- Cover happy path, failure path, and boundaries (empty/null/max/min/duplicate).
- If you can't write a VC for a requirement, you don't understand it yet.

## 4. Before declaring ready

- Every FR and BR has a VC.
- No ambiguous words ("fast", "gracefully", "appropriate").
- No implementation leaks ("use Redis", "call X API").
- Open Questions don't block the core path.

When the draft feels complete, run `/review-spec` on the file to get a structured review across ten quality dimensions. Address any `[MUST]` items before moving on to `/write-spec-plan`.

## Anti-patterns

| Bad | Fix |
|-----|-----|
| "Handle errors gracefully" | Enumerate each error and its response |
| "Should work on mobile" | "Renders correctly at 375px viewport" |
| "Validate input" | List every field, type, range, format |
| FR with "and" | Split into two FRs |
| "As discussed" | Inline the decision and rationale |

---

*Optional doc hygiene:* add Version, Last Updated, Status, Owner, and a Changelog when the spec will be maintained over time.
