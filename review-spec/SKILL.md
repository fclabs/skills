---
name: review-spec
description: >-
  Reviews a specification document for clarity, completeness, and quality across
  ten structured dimensions. Use when the user asks to review, audit, critique,
  or evaluate a spec, PRD, design doc, or requirements document — including
  phrases like "review this spec", "check my spec", "what's missing in this
  spec", "is this spec ready", or any time the user provides a spec file path
  and wants structured feedback. Always use this skill instead of improvising a
  spec review format on your own.
---

# Spec Review Skill

Perform a structured review of a specification document across ten quality dimensions, producing concrete findings and a prioritized action list.

## 1. Read the spec

Read the full spec file at the path provided before starting the review. If no path is given, ask the user for it.

## 2. Review dimensions

For each dimension, assess the spec and list findings as:
- **Issues** — must be fixed before implementation
- **Warnings** — likely to cause problems
- **Suggestions** — optional improvements

If a dimension looks good, say so briefly. Do not fabricate findings.

### 1. Goal Clarity
- Is there a single, unambiguous statement of what this spec achieves?
- Would a new engineer understand *why* this is being built and what success looks like?
- Is scope explicitly bounded — what is in vs out of scope?

### 2. Consistency & Completeness
- Are terms, names, and concepts used consistently throughout?
- Are there forward references to concepts never explained?
- Do any sections contradict each other?
- Are there gaps — steps or components described but never elaborated?

### 3. Edge Case Coverage
- For each feature/behavior, are error paths and boundary conditions addressed?
- Are obvious "what if" scenarios missing (empty input, concurrent requests, missing config, network failure)?
- Flag flows that only describe the happy path.

### 4. Success Criteria & Testability
- Does every `FR-NNN` and `BR-NNN` have at least one corresponding `VC-NNN` in the Verification Criteria section?
- Are success criteria concrete and verifiable — not vague adjectives like "fast" or "robust"?
- Does each `VC-NNN` include: Scenario, Input/State, Expected Result, and Failure Mode Covered?
- Is there an end-to-end acceptance test covering the full spec?
- Can a test be written from the spec alone, without additional design decisions?

### 5. Reference Technology
- Are technologies, frameworks, libraries, and external services explicitly named?
- Are version constraints or compatibility requirements stated where relevant?
- Are there implicit technology choices that should be made explicit?

### 6. Decision Rationale
- Are architectural/design decisions explained with a *why*, not just a *what*?
- Are trade-offs acknowledged (e.g., "we chose X over Y because...")?
- Flag any decisions that appear arbitrary or conflict with the stated goal.

### 7. Simplicity
- Is the proposed approach the simplest one that satisfies the requirements?
- Are there over-engineered components — abstractions or infrastructure not justified by requirements?
- Could any requirement be dropped or deferred without compromising the goal?

### 8. Functional Requirements
- Are all functional requirements explicitly listed (what the system must *do*)?
- Is each one atomic, testable, and unambiguous?
- Are there implicit behaviors buried in examples or diagrams that should be promoted to explicit requirements?

### 9. Non-Functional Requirements
- Are NFRs addressed: performance, scalability, availability, security, observability, maintainability?
- For each relevant NFR, is there a measurable target (e.g., p99 latency < 200ms)?
- Are NFRs consistent with the chosen technology and architecture?

### 10. Scope Discipline
- Does the spec contain requirements beyond what is needed to achieve the stated goal?
- Are "nice to haves" or future-proofing elements mixed with core requirements?
- Flag anything that adds complexity without contributing to the goal.

## 3. Output format

```
## Spec Review: [spec title or filename]

### Summary
One short paragraph on the overall state of the spec.

### Findings by Dimension

#### 1. Goal Clarity — [PASS / WARN / FAIL]
...

#### 2. Consistency & Completeness — [PASS / WARN / FAIL]
...

[... repeat for all 10 dimensions ...]

---

### Overall Verdict
[READY / NEEDS WORK / MAJOR ISSUES]

Brief justification (2-3 sentences).

### Action Items (prioritized)
1. [MUST] ...
2. [MUST] ...
3. [SHOULD] ...
4. [COULD] ...
```

Use `[MUST]` for blockers that prevent correct implementation, `[SHOULD]` for issues likely to cause problems, and `[COULD]` for optional improvements.

**Next step guidance**: If the verdict is `READY`, proceed to `/write-spec-plan`. If it is `NEEDS WORK` or `MAJOR ISSUES`, return to `/write-spec` and address the `[MUST]` items before re-checking.
