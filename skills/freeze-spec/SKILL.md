---
name: freeze-spec
description: >-
  Produces a compact, immutable "context capsule" from a finished spec —
  preserving what downstream specs need (purpose, public interfaces, key
  decisions, known limits) and dropping internal mechanics (VCs, Given/When/Then,
  Open Questions, MoSCoW). Use when the user wants to summarize, freeze,
  archive, or distill a completed spec for use as background context in future
  work — including phrases like "freeze this spec", "summarize the shipped
  spec", "make this into a context capsule", "archive this spec", or any time
  the user wants a smaller, durable reference for a spec whose implementation
  is done. Always use this skill instead of improvising a summary format.
---

# Freeze Spec Skill

A shipped spec is too detailed to use as context for the *next* spec. It carries VCs, Open Questions, exhaustive Given/When/Then, anti-pattern guidance, MoSCoW labels — almost none of which a downstream spec needs. What a downstream spec *does* need: purpose, public surface, key decisions and why, data-model facts that constrain dependent systems.

This skill produces a small, immutable context capsule from a finished spec.

## 0. Prerequisites

- The implementation must be shipped: `/verify-spec` returned `PASSED` and the work is merged.
- Open Questions must all be resolved (folded into the spec body).
- If either condition isn't met, warn the user before proceeding.

(Exception: the user may invoke this skill on a legacy spec they want to summarize as background context. In that case, skip the prerequisite check but note the freeze date and source clearly.)

## 1. Read the inputs

- **Spec file** (required) — the `.md` written with `write-spec`.
- **Plan file** *(optional)* — informs which iterations shipped.
- **Verify-spec output** *(optional)* — confirms what actually passed.
- **PR / commit reference** *(optional)* — for attribution.

If a path is missing, ask the user for it.

## 2. Determine output file path

- If the user provides a destination filename, use it.
- Otherwise, derive it from the spec filename by appending `-frozen` before the extension.
  Example: `specs/01-fastapi-server.md` → `specs/01-fastapi-server-frozen.md`

## 3. Write the capsule

Target size: 20–30% of the original spec. Use this structure:

```
# Frozen: <spec title>

Source: <path to original spec>
Status: SHIPPED
Frozen: <YYYY-MM-DD>
PR / commit: <link, if known>

## Purpose
<1 paragraph — the spec's Purpose section, kept verbatim>

## What it does
- <FR-001 collapsed to one sentence, present tense, indicative mood>
- <FR-002 ...>
- <BR-NNN one-liners interleaved or in a sub-list — whichever reads better>
...

## Public interfaces / data
<the spec's "Data & Interfaces" section, copied VERBATIM — paraphrasing risks silently changing contracts>

## Key decisions
- <decision>: <why> — sourced from BR rationale and inline rationale in the original
...

## Known limits (still true at freeze)
- <NFR threshold downstream systems must respect>
- <anything from Scope/Out that future specs commonly forget>
...

## Deliberately excluded
<Scope/Out, summarized — one or two short bullets>
```

## 4. Rules

1. **Verbatim where load-bearing** — copy "Data & Interfaces" exactly. This is the contract; paraphrasing creates silent drift.
2. **Compress FR/BR** — each becomes one sentence in indicative mood ("The ingestor batches events in 60-second windows" not "Given X, When Y, Then Z"). Strip MoSCoW labels — everything that shipped is implicitly Must.
3. **Drop entirely** — VCs, Open Questions, Assumptions (should already be folded in), anti-pattern guidance, numbering scheme rules, the original spec's review/verify ceremony.
4. **Preserve attribution** — always link back to the source spec path and the implementing PR/commit. The capsule is a summary, not a replacement; an investigator must be able to recover the detail.
5. **Frozen means immutable** — any change to the underlying behavior creates a *new* spec (and a new frozen file). Never edit an existing frozen file in place. If the user asks to "update" a frozen file, push back: it should be a new freeze of a new shipped spec.
6. **Cap the size** — if the capsule grows past ~30% of the original, push harder on compression. The whole point is that downstream specs can include this in their context cheaply.

## 5. After writing

Print:

```
Frozen capsule written to <path>.
Size: <N lines> (was <M lines> in source — <P>% of original).
Reference this file in future specs that depend on <feature name>.
```

If the capsule exceeds 30% of the original, flag it and suggest specific sections that could be tightened.
