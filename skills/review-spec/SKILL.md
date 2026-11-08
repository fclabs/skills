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

Review a specification document across six quality dimensions, fix the findings, and repeat until a fresh review produces no new findings.

## 1. Get the spec path

If no spec file path is given, ask the user for it. Do not review from memory of the file: every review pass reads the file from disk.

## 2. Review-and-fix loop

Run this loop. Do not stop after the first review.

```
iteration = 1
repeat:
    1. Spawn a NEW subagent (Agent tool) to review the spec  -> findings
    2. If findings contain no [MUST] or [SHOULD] items -> exit loop
    3. Triage: ask the operator about every decision-needing finding NOW
    4. Fix the findings in the spec file
    4. iteration += 1
until exit or iteration > 5
```

### 2a. Review step — always a fresh subagent

Every review runs in its own newly spawned subagent (`general-purpose`). Never reuse a previous reviewer (no SendMessage continuation) and never review inline in the main context. The point is a clean context: the reviewer must not remember earlier iterations or the fixes just made, so it judges the file as it stands.

Brief the subagent with:
- The spec file path, and an instruction to **re-read the whole file from disk** before reviewing.
- The review dimensions (section 3) and the output format (section 4), pasted in full — the subagent does not see this skill.
- An instruction to review only, not edit any file.
- An instruction not to fabricate findings: report nothing for a dimension that is fine.
- An instruction to tag every finding that cannot be resolved from the spec and its context alone as `[DECISION]`, stating the question and 2-3 concrete options with a recommended one. Fixing such a finding means choosing between product or design alternatives, so the operator has to make the choice.
- The paths of any baseline capsules or referenced specs the spec depends on, if known.

Do **not** pass previous findings, the fix history, or your opinion of the spec's quality. This keeps the review unbiased. (The orchestrator tracks history itself, see 2d.)

### 2b. Triage: operator decisions come first

Operator decisions are asked **as early as possible**, so no agent builds on a guess. Right after each review returns, before editing anything:

1. Collect every `[DECISION]` finding, plus any finding you cannot resolve from the spec and its context.
2. Ask the operator about all of them immediately with AskUserQuestion (up to 4 questions per call; use several calls if needed), putting your recommended option first. Do not defer questions to the end of the loop, to the final report, or until after other fixes are done.
3. Record each answer in the spec as a decision, with the reason, so later reviewers see it as settled and do not re-raise it.
4. Only then start the fix step.

Never invent an answer, pick a default, or work around a pending decision. If a fix depends on an unanswered decision, leave that part untouched until the operator answers. If the operator is unavailable, stop the loop and report the open questions instead of guessing.

### 2c. Fix step

Apply fixes to the spec file with Edit, in priority order:
- Fix every `[MUST]` and `[SHOULD]` item.
- Apply `[COULD]` items only when trivial and clearly beneficial; they never keep the loop running on their own.
- Fix only what is decided: every `[DECISION]` was settled in triage (2b) before this step starts.
- Keep fixes minimal and local. Do not rewrite unrelated sections, and do not add scope to satisfy a finding when removing or deferring the requirement is the simpler fix.
- When a fix adds or changes an FR/BR, add or update the matching VC so the next review does not flag the gap you just created.

### 2d. Termination and safeguards

- **Converged**: a review returns no `[MUST]` or `[SHOULD]` action items (verdict `READY`). Stop.
- **Max iterations**: stop after 5 review passes even if findings remain, and report what is left.
- **No progress / oscillation**: keep a short list of findings per iteration (orchestrator-side only). If a finding reappears after being fixed, or a fix reverses an earlier fix, stop and ask the operator to decide right away rather than looping.
- **Disputed findings**: if you judge a finding to be wrong, do not silently ignore it. Note it as disputed, leave the spec unchanged for it, and mention it in the final report. If the fresh reviewer raises it again, ask the operator immediately.

## 3. Review dimensions (give these to each reviewer subagent)

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

## 4. Reviewer output format (give this to each reviewer subagent)

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

## 5. Final report to the user

When the loop ends, report:
- Number of review passes and the final verdict.
- A concise list of what was fixed per iteration.
- Any disputed findings, unresolved items, or `[COULD]` suggestions left as-is.
- Why the loop stopped (converged / max iterations / needs user decision).

**Next step guidance**: If the final verdict is `READY`, proceed to `/write-spec-plan`. If the loop stopped with `NEEDS WORK` or `MAJOR ISSUES`, resolve the remaining `[MUST]` items (with `/write-spec` if they need deeper rework) and run this skill again.
