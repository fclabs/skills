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

## 0. Load existing context

Before discovery, find what is already known about the code this spec touches:

- **Frozen capsules** — `*-frozen.md` files from `/freeze-spec`, usually next to the specs. They record shipped behavior and never change.
- **Baseline capsules** — `<docs>/codebase/capsules/**/*.md` (or `<docs>/codebase/<unit>/capsules/**/*.md`) from `/document-codebase`. They mirror the code's folder layout (a service under `src/services/` has its capsule under `capsules/services/`) and record existing behavior at their `Commit:`.

Read the capsules for the modules in scope; skip the rest. Treat them as follows:

- **Public interfaces / data** are the contracts this spec must respect or explicitly change. Cite them in Data & Interfaces (e.g., "per `capsules/services/invoice-billing.md`") instead of re-deriving them.
- **Known limits** are constraints; carry the relevant ones into NFRs or Scope/Out.
- Anything labelled `[inferred]` or `[unknown]` in a baseline capsule is not a fact. If the spec depends on it, confirm it with the user or record an Open Question.
- If a baseline capsule's `Commit:` is behind `HEAD` and `git diff --name-only <commit>..HEAD -- <its Source path>` lists files, tell the user it may be stale and suggest refreshing it with `/document-codebase`.
- If a frozen and a baseline capsule disagree, the baseline describes current code; raise the disagreement as an Open Question.

If the spec changes existing code that has neither kind of capsule, suggest running `/document-codebase` on those modules first. Don't run it yourself; continue if the user declines.

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
- **Non-Functional Requirements** — each must include a measurable threshold (absolute value or explicit relative bound with a baseline; "fast" and "as today" are not measurable).
- **Data & Interfaces** — only what this spec touches.
- **Verification Criteria** — see §3.
- **Open Questions**, **Assumptions**.

**Open Questions discipline**: An Open Question is a placeholder for a decision not yet made. When the decision is made, fold it back into the normative section it belongs to (FR, BR, Data, or Scope) and remove the question. A shipped spec must have zero unresolved Open Questions. Never answer an Open Question with a freestanding "Resolution Note" or "Implementation Note" section.

## 3. Verification criteria (the core)

Every **FR and BR** needs at least one VC. Measurable NFRs don't each need a VC — a single end-to-end check covering the relevant NFR thresholds is sufficient.

**Default form (one line)** — use this whenever the failure mode is just the scenario inverted:

```
VC-NNN: <scenario> → <observable expected result>
```

**Long form** — use only when the failure mode is independent of the happy path and worth describing separately:

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
- **Expected Result must be unconditional**: no "if X exists, verify via Y; otherwise verify indirectly." If the result depends on optional infrastructure, either make the infrastructure required or split into two VCs.

## 4. Before declaring ready

When the draft feels complete, run `/review-spec` on the file. Its 6-dimension checklist is the **authoritative** definition of "ready." Address every `[MUST]` item before moving on to `/write-spec-plan`.

## Anti-patterns

| Bad | Fix |
|-----|-----|
| "Handle errors gracefully" | Enumerate each error and its response |
| "Should work on mobile" | "Renders correctly at 375px viewport" |
| "Validate input" | List every field, type, range, format |
| FR with "and" | Split into two FRs |
| "As discussed" | Inline the decision and rationale |
| "Resolution Note" / "Implementation Note" section | Fold the decision into the FR, BR, or Data section it affects |
| VC Expected Result with "if X exists ... otherwise verify indirectly" | Make the observable concrete or split into two VCs |
| NFR threshold "same as today" / "dominated by X" | State an absolute bound or a named baseline measurement that can be re-run |

---

## Appendix: child specs

When a spec extends a parent spec, new requirements introduced in the child must use a distinct numeric range (e.g., parent uses 0xx–099, child uses 1xx). Requirements *re-stated or imported* from the parent must cite the parent's identifier (e.g., "per FR-015 from spec-01") rather than being renumbered — renumbering creates two authoritative IDs for the same rule.

*Optional doc hygiene:* add Version, Last Updated, Status, Owner, and a Changelog when the spec will be maintained over time.
