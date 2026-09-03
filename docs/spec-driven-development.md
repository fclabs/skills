# Spec-Driven Development: A Beginner's Guide

This guide explains how to use the six spec skills in this repository, for someone
who has never worked in a spec-driven way before. It assumes you know how to run
Claude Code and nothing else.

The skills themselves live under [`skills/`](../skills/), one directory per skill —
`skills/write-spec/SKILL.md`, `skills/review-spec/SKILL.md`, and so on. Those files
are the source of truth for behaviour; this guide is the orientation. To use them,
install each skill directory under `~/.claude/skills/` or your project's
`.claude/skills/`, then invoke it by name as shown below.

---

## 1. Why bother writing a spec at all?

When *you* write code, ambiguity is harmless. You read "validate the input", and
your own judgement fills the gap — you know that emails need an `@`, that empty
strings should be rejected, that the error message should not leak the database
schema.

When an **AI** writes the code, ambiguity is not harmless. The model also fills the
gap — silently, plausibly, and sometimes wrongly. You get working code that does
the wrong thing, and you find out three iterations later when something built on
top of it breaks.

Spec-driven development (SDD) is the discipline of closing those gaps *before*
implementation starts. It rests on two ideas:

1. **Unambiguous requirements.** Every behaviour is stated once, explicitly, with
   its inputs, its outputs, and its failure modes.
2. **Testable verification.** Every requirement carries a check that can be run
   and that either passes or fails — no human judgement in the loop.

Everything in these skills exists to serve those two ideas.

### Is this overkill for my task?

Sometimes, yes. Rough guidance:

| Task | Approach |
|---|---|
| Fix a typo, rename a variable, bump a dependency | Just do it. No spec. |
| Add an endpoint to an existing, well-understood service | Maybe a short spec; skip the plan. |
| A new feature touching several files, with real edge cases | Full workflow. |
| A new service, subsystem, or anything you'll build on later | Full workflow, and freeze it at the end. |

The cost of the workflow is mostly front-loaded thinking. The payoff is that the
implementation phase becomes mechanical and verifiable. If you can already hold
the whole change in your head and check it by eye, you don't need this.

---

## 2. The pipeline at a glance

```
  /write-spec  ──►  /review-spec  ──►  /write-spec-plan  ──►  /implement-spec-plan  ──►  /verify-spec  ──►  /freeze-spec
   what & why       is it ready?        how, in steps          build it, step by step      did we?          remember it
       ▲                 │
       └─── fix MUSTs ───┘
```

Each stage produces a file, and the next stage reads it. Nothing is passed by
memory or by conversation — this matters, because implementation runs in fresh
subagents that were never part of your conversation.

| Stage | Skill | Reads | Writes |
|---|---|---|---|
| 1 | `write-spec` | your description of the problem | `specs/01-thing.md` |
| 2 | `review-spec` | the spec | a review report (in chat) |
| 3 | `write-spec-plan` | the spec | `specs/01-thing-plan.md` |
| 4 | `implement-spec-plan` | the plan + spec | code, commits, `…-plan-artifacts/`, docs |
| 5 | `verify-spec` | the spec + plan + code | a coverage table + verdict (in chat) |
| 6 | `freeze-spec` | the shipped spec | `specs/01-thing-frozen.md` |

Stages 1–5 are the normal loop. Stage 6 is only for work that later work will
build upon.

---

## 3. Stage 1 — `/write-spec`

**Invoke it with anything, however vague.** "I want a service that ingests
webhooks and dedupes them" is enough to start. The skill is designed to trigger on
half-formed ideas; it will do discovery before it drafts.

### What happens

Claude will ask you questions until it can answer, for every feature:

- What problem is this, and who is it for? What is explicitly *out* of scope?
- Who are the actors, and what may each of them do?
- What are the inputs and outputs, with valid ranges?
- What happens on invalid input, a missing dependency, a boundary condition?
- How will a human know it works?

**Answer these properly — this is where the value is.** If you genuinely don't
know an answer yet, say so; it gets recorded as an **Open Question** rather than
silently assumed. That distinction is the whole point: a recorded unknown is
manageable, an invented assumption is a landmine.

### What comes out

A markdown file with these sections:

- **Purpose** — one paragraph: the problem and who benefits.
- **Scope** — In / Out bullets. Be specific about Out; it's what stops scope creep later.
- **Actors** — a table of actor, description, permissions.
- **Functional Requirements** — numbered `FR-001`, `FR-002`… each written as
  Given/When/Then, each tagged with a MoSCoW priority (Must / Should / Could / Won't).
- **Business Rules** — numbered `BR-001`… each with rule, rationale, exceptions.
- **Non-Functional Requirements** — performance, security, etc., each with a
  **measurable threshold**. "Fast" is not a threshold. "p99 under 200 ms" is.
- **Data & Interfaces** — only the parts this spec touches.
- **Verification Criteria** — numbered `VC-001`… see below.
- **Open Questions** and **Assumptions**.

### The bit that beginners underestimate: verification criteria

Every `FR` and every `BR` needs at least one `VC`. A VC is one line:

```
VC-014: POST /webhooks with a duplicate delivery-id → 200, and no new row in `events`
```

Scenario on the left, **observable** result on the right. Not "the deduplication
works correctly" — that isn't observable. Not "the `dedupe()` function is called" —
that's implementation, and it will be wrong the moment someone refactors.

Two rules worth memorising:

- **If you cannot write a VC for a requirement, you do not yet understand the
  requirement.** This is the single most useful signal the workflow gives you.
  Go back and clarify rather than writing a vague VC.
- **Expected results must be unconditional.** No "if a metrics backend exists,
  check the counter; otherwise verify indirectly." Either make the backend
  required, or split it into two VCs. Conditional criteria always resolve to the
  easy branch.

### Before you move on

Resolve every Open Question by *folding the answer into the requirement it
belongs to* — edit the FR, BR, or Data section — and delete the question. Do not
leave a trailing "Resolution Notes" section; that creates two places where the
truth lives. A spec that goes to implementation has zero open questions.

---

## 4. Stage 2 — `/review-spec`

Run this on the spec file when the draft feels complete. It is the **authoritative
definition of "ready"** — not your own sense that the document looks thorough.

It grades six dimensions, each PASS / WARN / FAIL:

1. **Goal & Scope** — one clear statement of what and why; in/out bounded; no nice-to-haves smuggled in among the requirements.
2. **Completeness & Consistency** — every FR atomic and testable; terms used consistently; no forward references, contradictions, or behaviours hiding inside examples.
3. **Edge cases & Testability** — error paths and boundaries covered; every FR/BR has a VC; success criteria concrete; a test writable from the spec alone.
4. **Non-Functional Requirements** — performance, security, observability etc. addressed, each with a measurable target.
5. **Technology & Rationale** — technologies named with versions; decisions explained with a *why*; trade-offs acknowledged.
6. **Simplicity** — is this the simplest approach that works? Anything over-engineered or droppable?

You get an overall verdict — `READY`, `NEEDS WORK`, or `MAJOR ISSUES` — and a
prioritised action list tagged `[MUST]`, `[SHOULD]`, `[COULD]`.

**Rule: fix every `[MUST]` and re-run the review.** `[MUST]` items are things that
will cause the implementation to be wrong, not stylistic quibbles. Don't proceed
to planning until the verdict is `READY`; `write-spec-plan` will refuse anyway.

Expect one or two round trips. That is normal and it is cheap — far cheaper than
discovering the same gap after three iterations of code exist.

---

## 5. Stage 3 — `/write-spec-plan`

Turns a `READY` spec into an **iterative build plan**, written to
`<spec>-plan.md` next to the spec.

### The key idea: subagents with no memory

Implementation does not run in your conversation. Each iteration is executed by a
**fresh subagent with a blank context**, which knows only what it can read from
disk. The plan is written for that reader — which is why it uses absolute paths
everywhere, names things explicitly, and never says "the same approach as before".

If you remember one thing about this stage: **the plan must be self-sufficient.**

### The artifact directory

Because subagents can't talk to each other, they hand off through files in
`<spec>-plan-artifacts/`:

```
01-thing-plan-artifacts/
  CONTEXT.md              # living state — rewritten in place each iteration
  DECISIONS.md            # append-only decision log
  iterations/NN-slug.md   # one immutable handoff record per iteration
```

- **`CONTEXT.md`** answers "where does this project stand right now": what works
  end to end, a file map, the public interfaces later iterations will call,
  conventions to follow, copy-pasteable commands, and known gaps. It is
  *overwritten* each iteration, so it can never go stale.
- **`DECISIONS.md`** is append-only. One short entry per non-obvious choice:
  context, decision, rejected alternatives, consequences. This is what stops
  iteration 5 from quietly undoing a choice made in iteration 2.
- **`iterations/NN-slug.md`** is written once at the end of each iteration and
  never edited: criteria results with the commands run, commit SHA, files
  touched, deviations, gotchas, and an explicit "For the next iteration" section.

You mostly don't need to read these. They exist so the machinery works. But when
something goes sideways, they're the first place to look.

### The iterations

Each iteration in the plan has a **Goal**, a **Reads** list, a **Scope**,
**Success criteria** (each referencing the `VC-NNN` it satisfies, with the exact
command to run), a **Hands off** section naming the facts the next iteration
needs, and a **commit message**.

Iterations are ordered so each one leaves something working and testable. Each
one ends in a single commit including its artifacts. An iteration may not start
until the previous one's criteria have actually passed.

### The final iteration writes the docs

The last iteration always has one extra job: read the whole artifact directory and
**turn it into human documentation** in the project's docs space. This is
synthesis, not copying — the artifacts are a build log written by machines, the
docs are for a person who arrives later and was never here.

That means: organised by what a reader needs (never by iteration number), with
the PASS/FAIL tables, commit SHAs, and handoff notes dropped, and the decisions,
constraints, and surprises kept. Shipped docs must not reference the plan, the
spec, or the artifact directory — they stand alone.

All user-facing docs ship in that final commit, never partway through.

### Review the plan before building

Read it yourself. You're looking for: iterations that are too big to finish in one
focused session, iterations that produce nothing runnable, and iterations that
need five separate facts from the previous one (usually a sign the split is
wrong). Ask for changes now — it's the last cheap moment.

---

## 6. Stage 4 — `/implement-spec-plan`

Point it at the plan file and it builds.

### What Claude does

It acts as an **orchestrator**, not an implementer. For each iteration, in order:

1. Announces the iteration.
2. Dispatches **one subagent** with a self-contained prompt: the absolute paths,
   the iteration's goal/scope/criteria quoted verbatim, and the rules.
3. Waits. Never runs two iterations in parallel.
4. **Gates** on the result: every success criterion must have actually been run
   and passed, the work must be committed, and the artifacts must be present and
   current. Stale artifacts count as a failure even when the code is green —
   because the next subagent has no other way to learn what happened.
5. Advances.

### Your part

By default it auto-advances through iterations and reports back. If you'd rather
approve each step, say **"step me through this"** or **"interactive"** when you
invoke it, and it will pause for confirmation after each iteration.

You'll be pulled in when:

- **A scope item is ambiguous.** The subagent stops without committing and the
  orchestrator asks you. Answer the question; don't tell it to just pick
  something — the ambiguity is real and your answer is the fix.
- **A criterion can't be made to pass.** Same: progress halts rather than
  silently degrading. Decide whether the code is wrong or the spec was.

That halting behaviour is deliberate. A workflow that guesses when it's unsure is
a workflow that produces confident, wrong software.

### What you get

A sequence of commits, one per iteration, each with its code, its tests, and its
artifacts. Then the orchestrator runs the full regression suite itself (once, at
the end — not after every iteration), checks the shipped docs, checks the
artifacts describe the finished system, and finally runs `/verify-spec`.

It will not declare the implementation done until that verification passes.

---

## 7. Stage 5 — `/verify-spec`

The end-to-end authority on "does the code actually satisfy the spec".
`implement-spec-plan` calls it automatically, but you can also run it standalone —
against work built without a plan, or to re-check after later changes.

Give it the spec (and the plan, if there is one). It:

1. Builds a **coverage table** of every `FR` and `BR` mapped to its `VC`s. Any
   requirement with no VC is flagged as an **Uncovered Gap** — and gaps block a
   `PASSED` verdict outright.
2. Runs each VC's command once and records PASS or FAIL.
3. Runs the full regression suite. **A red suite means `FAILED`, regardless of
   how the VCs went.**
4. Spot-checks that the documentation the plan promised exists and matches
   reality.

The verdict is `PASSED` or `FAILED`, with the table and any failing commands and
output. Doc gaps surface as `[MUST-FIX-BEFORE-MERGE]` items — they don't block
the verdict on their own, but you should not merge past them.

If you explicitly waive a check, it's recorded as `WAIVED`, never as `PASSED`. The
verdict is meant to be trustworthy; that's the only reason it's worth having.

On `PASSED`, it offers to open a PR with the coverage table and a test-plan
checklist in the body.

---

## 8. Stage 6 — `/freeze-spec`

Optional, and only for shipped work that **future work will build on**.

The problem it solves: a full spec is far too detailed to hand to the next spec as
background. It's full of VCs, Given/When/Then, MoSCoW labels, and resolved
questions — none of which the next author needs. But they *do* need the purpose,
the public interfaces, and the decisions they must not accidentally undo.

`/freeze-spec` distils the spec into `<spec>-frozen.md`, at 20–30% of the
original:

- **Purpose** — verbatim.
- **What it does** — each FR and BR collapsed to a single indicative sentence
  ("The ingestor batches events in 60-second windows"), MoSCoW labels stripped
  because everything that shipped is implicitly a Must.
- **Public interfaces / data** — copied **verbatim**. This is the contract;
  paraphrasing it creates silent drift.
- **Key decisions** — what and why.
- **Known limits** — thresholds and boundaries downstream work must respect.
- **Deliberately excluded** — a compressed version of Scope/Out.

Prerequisites: verification passed, the work is merged, and no Open Questions
remain. (You can also freeze a legacy spec purely as background context — the
skill will note the source and date.)

**Frozen means immutable.** If behaviour changes, that's a new spec and a new
freeze — never an edit to an existing frozen file. If you ask to "update" one,
expect pushback.

---

## 9. Working across several specs

Real projects end up with `specs/01-…`, `specs/02-…`, and so on. Two conventions
keep them from tangling:

- **Numbering in child specs.** A spec that extends another uses its own numeric
  range — parent `FR-0xx`, child `FR-1xx`. Requirements *re-stated* from the
  parent cite the parent's ID ("per FR-015 from spec-01") rather than being
  renumbered. Renumbering gives one rule two authoritative IDs, and they
  eventually disagree.
- **Feed frozen capsules forward.** When writing spec 03, include the frozen
  capsules of 01 and 02 as context rather than the full specs. That's exactly
  what they're for.

---

## 10. Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Answering discovery questions with "use your judgement" | You've handed the decision to a model that will make it silently and inconsistently | Answer it, or record it as an Open Question |
| "Handle errors gracefully" | Every error becomes whatever the implementer felt like | Enumerate each error and its response |
| "Should work on mobile" | Unverifiable, so it won't be verified | "Renders correctly at 375px viewport" |
| An FR with "and" in it | Half of it can pass while the other half fails | Split it into two FRs |
| "As discussed" / "same as before" | The subagent was not in that conversation and never will be | Inline the decision and its rationale |
| Skipping `/review-spec` because the spec looks fine | The `[MUST]` items are precisely the gaps you can't see | Run it; fix the MUSTs; re-run |
| Treating `[MUST]` items as suggestions | They are the ones that make implementation wrong | Fix them before planning |
| Writing VCs that check implementation ("calls `dedupe()`") | Breaks on the first refactor and proves nothing about behaviour | Check the observable outcome |
| Editing artifacts by hand mid-build | The next subagent trusts them; you've now lied to it | Let the iterations own their artifacts |
| Shipping docs in iteration 3 | You document a state that iterations 4 and 5 invalidate | Docs ship in the final iteration only |
| Treating the artifact directory as the documentation | It's a build log — decisions buried in PASS/FAIL tables | Synthesise real docs in the last iteration |
| Editing a frozen spec | Its consumers assume it's stable; silent contract drift | New spec, new freeze |

---

## 11. A worked example, end to end

```
You:    I need a webhook ingest service that dedupes deliveries.
Claude: [/write-spec] — asks about actors, retention, what counts as a duplicate,
        what happens when the upstream retries after a partial write, how you'd
        know it works.
You:    [answer; defer the retention question]
        → specs/01-webhook-ingest.md, with one Open Question about retention.

You:    Retention is 30 days.
Claude: folds it into the Data section, removes the Open Question.

You:    /review-spec specs/01-webhook-ingest.md
Claude: NEEDS WORK. [MUST] FR-004 has no VC. [MUST] NFR-002 says "fast".
        [SHOULD] "delivery" and "event" used interchangeably.

You:    fix those
Claude: edits the spec.
You:    /review-spec specs/01-webhook-ingest.md
Claude: READY.

You:    /write-spec-plan specs/01-webhook-ingest.md
        → specs/01-webhook-ingest-plan.md, 4 iterations + final verification table.

You:    [read it; iteration 2 looks too big]
        split iteration 2
Claude: rewrites it as 2a and 2b.

You:    /implement-spec-plan specs/01-webhook-ingest-plan.md
Claude: Iteration 1 … PASS, committed a1b2c3d.
        Iteration 2 … PASS, committed e4f5g6h.
        Iteration 3 … blocked: the spec doesn't say whether a duplicate with a
        *different* payload is an error or a silent drop.
You:    it's a 409.
Claude: … PASS. Iteration 4 (code + docs) … PASS.
        Full regression: green. /verify-spec: PASSED.
        Open a PR?
You:    yes.

You:    /freeze-spec specs/01-webhook-ingest.md
        → specs/01-webhook-ingest-frozen.md — context for spec 02.
```

---

## 12. Quick reference

```
/write-spec           <describe anything>        → specs/NN-name.md
/review-spec          specs/NN-name.md           → verdict + action items
/write-spec-plan      specs/NN-name.md           → specs/NN-name-plan.md
/implement-spec-plan  specs/NN-name-plan.md      → code, commits, artifacts, docs
/verify-spec          specs/NN-name.md [+ plan]  → coverage table + verdict
/freeze-spec          specs/NN-name.md           → specs/NN-name-frozen.md
```

**Prefixes and what they mean**

| ID | Meaning |
|---|---|
| `FR-NNN` | Functional requirement — something the system must do |
| `BR-NNN` | Business rule — a constraint, with rationale and exceptions |
| `NFR` | Non-functional requirement — must carry a measurable threshold |
| `VC-NNN` | Verification criterion — a runnable check for an FR or BR |
| `D-NNN` | A decision recorded in `DECISIONS.md` during implementation |

**The four gates.** Each is a place where the workflow stops rather than guesses:

1. `review-spec` must say `READY` before a plan is written.
2. An iteration's criteria must pass, and its artifacts be current, before the
   next one starts.
3. Ambiguity halts the subagent instead of being resolved by guesswork.
4. `verify-spec` must say `PASSED` — with a green regression suite — before the
   implementation is called done.

If you understand those four gates, you understand the workflow.
