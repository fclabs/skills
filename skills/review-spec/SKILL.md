---
name: review-spec
description: >-
  Reviews a specification document for clarity, completeness, and quality across
  six structured dimensions. Use when the user asks to review, audit, critique,
  or evaluate a spec, PRD, design doc, or requirements document — including
  phrases like "review this spec", "check my spec", "what's missing in this
  spec", "is this spec ready", or any time the user provides a spec file path
  and wants structured feedback. Always use this skill instead of improvising a
  spec review format on your own.
---

# Spec Review Skill

Perform a structured review of a specification document across six quality dimensions, producing concrete findings and a prioritized action list.

## 1. Read the spec

Read the full spec file at the path provided before starting the review. If no path is given, ask the user for it.

## 2. Review dimensions

For each dimension, list findings as:
- **Issues** — must be fixed before implementation
- **Warnings** — likely to cause problems
- **Suggestions** — optional improvements

If a dimension looks good, say so briefly. Do not fabricate findings.

### 1. Goal & Scope
- Is there a single, unambiguous statement of what this spec achieves and *why*?
- Is scope explicitly bounded — what is in vs out?
- Are "nice to haves" or future-proofing elements mixed with core requirements?

### 2. Completeness & Consistency
- Are all functional requirements explicitly listed (what the system must *do*)?
- Is each FR atomic, testable, and unambiguous?
- Are terms, names, and concepts used consistently throughout?
- Are there forward references to concepts never explained, contradictions, or gaps?
- Are there implicit behaviors buried in examples or diagrams that should be promoted to explicit FRs?

### 3. Edge cases & Testability
- For each behavior, are error paths and boundary conditions addressed (empty input, concurrent requests, missing config, network failure)?
- Does every `FR-NNN` and `BR-NNN` have at least one corresponding `VC-NNN`?
- Are success criteria concrete and verifiable — not vague adjectives like "fast" or "robust"?
- Can a test be written from the spec alone, without additional design decisions?
- Is there an end-to-end acceptance check covering the spec as a whole?

### 4. Non-Functional Requirements
- Are NFRs addressed: performance, scalability, availability, security, observability, maintainability?
- For each relevant NFR, is there a measurable target (e.g., p99 latency < 200ms)?
- Is there at least one end-to-end check that exercises the load-bearing NFR thresholds?

### 5. Technology & Rationale
- Are technologies, frameworks, libraries, and external services explicitly named, with version/compatibility constraints where relevant?
- Are architectural/design decisions explained with a *why*, not just a *what*?
- Are trade-offs acknowledged? Flag decisions that appear arbitrary or conflict with the stated goal.

### 6. Simplicity
- Is the proposed approach the simplest one that satisfies the requirements?
- Are there over-engineered components — abstractions or infrastructure not justified by requirements?
- Could any requirement be dropped or deferred without compromising the goal?

## 3. Output format

```
## Spec Review: [spec title or filename]

### Summary
One short paragraph on the overall state of the spec.

### Findings by Dimension

#### 1. Goal & Scope — [PASS / WARN / FAIL]
...

#### 2. Completeness & Consistency — [PASS / WARN / FAIL]
...

[... repeat for all 6 dimensions ...]

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
