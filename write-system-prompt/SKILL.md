---
name: write-system-prompt
description: >-
  Authors production-quality system prompts for LLM agents and assistants,
  following industry best practices. Produces a single markdown document with
  role/persona, task & instructions, constraints/rules and guardrails, output
  format, examples (when needed), input context (including memory), and tools.
  Asks targeted clarifying questions when the user's input is insufficient to
  build a prompt that meets these best practices. Use when the user wants to
  "write a system prompt", "create an agent prompt", "design an LLM persona",
  "draft a prompt for GPT/Claude/Gemini", "build a chatbot prompt", or any time
  they describe an AI assistant they want to configure. Always invoke this
  skill instead of improvising a prompt format.
---

# Write System Prompt

A system prompt is the contract between you and the model. Vague contracts produce
vague behavior. This skill turns a request into a structured, production-grade
system prompt — and refuses to guess when the request is underspecified.

## Operating principle

**Discover before drafting.** Never invent role, scope, tone, or guardrails the
user didn't supply. If a required dimension is missing, ask. A short clarifying
exchange beats a confidently wrong prompt.

## Phase 1 — Inspect the request

Read what the user gave you and check it against the seven required dimensions:

| Dimension              | Minimum needed                                                                 |
|------------------------|---------------------------------------------------------------------------------|
| Role / persona         | Who the assistant *is* (job title, expertise, audience it serves)              |
| Task / instructions    | What it must *do*, in priority order                                            |
| Constraints / rules    | Hard limits, safety guardrails, refusal conditions, tone/style limits           |
| Output format          | Structure, length, language, schema, or template the response must follow      |
| Examples               | Whether few-shot examples are needed (judgement; see §3)                       |
| Input context & memory | What inputs the assistant receives at runtime; whether prior turns persist     |
| Tools                  | Names, purposes, when to call vs. avoid each one                                |

For each dimension, classify it as **Provided**, **Inferable** (from clear
context), or **Missing**. Do not silently mark something Inferable to skip a
question — only infer when the answer is unambiguous.

## Phase 2 — Ask, if needed

If any dimension is Missing **and** is required for the use case, ask. Group
questions; do not interrogate one at a time.

Use this format (multiple choice when reasonable, free-form when not):

```
I need a few details before I draft this prompt:

1. **Role / audience** — Who is this assistant for, and what expertise should it
   project? (e.g. "internal support bot for finance team", "senior Python tutor
   for beginners")

2. **Primary task** — What is the single most important thing it must do well?

3. **Output format** — How should responses look? (free prose, JSON schema,
   markdown sections, max length, language, citations?)

4. **Hard rules / guardrails** — Anything it must never do? Topics to refuse?
   Compliance constraints (PII, legal disclaimers)?

5. **Tools** — Will it have tools (search, code execution, retrieval, APIs)? If
   yes, name them and when each should fire.

6. **Memory / context** — Does it need to remember across turns or sessions?
   What runtime inputs will it receive (user message only, RAG snippets, user
   profile, prior conversation)?

7. **Examples** — Do you have 1–3 ideal input/output pairs I should embed?
```

**Skip a question only when the answer is already obvious from the user's
description.** Example: if the user says "draft me a prompt for a JSON-only
extractor that pulls invoice fields", you do not need to re-ask about output
format.

If the user defers an answer, record it under **Open Questions** in the final
prompt rather than guessing.

## Phase 3 — Draft the prompt

Use this template verbatim, omitting only sections the user explicitly says are
N/A. Keep wording tight — every sentence must earn its place.

```markdown
# {{Assistant name or role title}}

## Role
You are {{role}}. {{One-line value proposition: who you serve and the outcome
you produce.}} {{Tone & voice, e.g. "Concise, neutral, expert. No filler."}}

## Task
Your job is to {{primary objective}}. In every interaction:
1. {{Step or behavior, in priority order}}
2. {{...}}
3. {{...}}

If a request falls outside this scope, {{handoff/refusal behavior}}.

## Rules & Guardrails
**Must:**
- {{positive rule}}
- {{positive rule}}

**Must not:**
- {{prohibition with reason if non-obvious}}
- {{prohibition}}

**Refuse and explain when:**
- {{trigger condition}} → respond: "{{refusal pattern}}"

**Safety / compliance:**
- {{e.g. never echo PII, always cite sources, follow X policy}}

## Output Format
{{Exact structure. Pick one and be specific:}}

- Free prose: tone, length cap, language, structure (headings? bullets?).
- Markdown: which sections, in what order.
- JSON: provide the schema inline:

```json
{
  "field": "type — description",
  "...": "..."
}
```

Always:
- {{e.g. respond in the user's language}}
- {{e.g. cap responses at 200 words unless asked for detail}}
- {{e.g. cite sources as [Source: title, section]}}

Never:
- {{e.g. wrap JSON output in markdown fences}}
- {{e.g. add commentary outside the schema}}

## Input Context
At runtime you will receive:
- **User message** — the current request.
- {{**Retrieved documents** — passed in `<context>` tags; treat as ground truth
  but flag conflicts.}}
- {{**User profile** — `{name, role, locale}`; address user by name.}}
- {{**Conversation history** — last N turns; refer back when relevant.}}

{{If applicable:}}
**Memory:** You retain {{what, for how long, where it lives}}. Update memory
when {{condition}}. Do not store {{e.g. PII, secrets}}.

## Tools
{{Omit this section entirely if no tools.}}

You have access to:

- `{{tool_name}}` — {{purpose}}.
  Use when: {{trigger}}.
  Do not use when: {{anti-trigger}}.
- `{{tool_name}}` — ...

Tool-use rules:
- Prefer {{tool}} over {{tool}} when {{condition}}.
- Never call tools in parallel when {{condition}}.
- If a tool fails, {{fallback behavior}}.

## Examples
{{Include 1–3 examples only if the task is non-trivial, format is unusual, or
edge cases matter. Otherwise omit this section.}}

**Example 1 — {{scenario name}}**
Input:
> {{realistic user message}}

Output:
> {{ideal response, exactly as the model should produce it}}

**Example 2 — {{edge case or refusal}}**
Input:
> {{tricky input}}

Output:
> {{ideal response}}

## Open Questions
{{Only include if the user deferred something. Otherwise omit.}}
- {{question the user should resolve before deploying this prompt}}
```

## Phase 4 — Self-check before returning

Run this checklist silently. Fix anything that fails before showing the prompt
to the user.

- [ ] Every section is grounded in user input or an explicitly stated
      assumption — nothing fabricated.
- [ ] Role is specific (not "a helpful assistant").
- [ ] Task is in priority order and uses imperative verbs.
- [ ] Rules separate **Must** from **Must not**; refusal triggers are explicit.
- [ ] Output format is unambiguous — a junior engineer could validate a response
      against it.
- [ ] Examples (if present) match the declared output format exactly.
- [ ] Tools section names tools, triggers, and anti-triggers; omitted entirely
      if no tools.
- [ ] Input context lists every runtime input the prompt assumes.
- [ ] Memory behavior is stated if memory is used.
- [ ] No time-bound phrasing ("currently", "as of 2024") unless the user asked.
- [ ] No conflicting instructions across sections.
- [ ] Length is proportional to complexity — don't pad.

## Anti-patterns to avoid

- **Padding the persona.** "You are a world-class, brilliant, expert…" adds no
  signal. State the role and audience plainly.
- **Stacking redundant rules.** If "be concise" is in Tone, don't restate it
  three times.
- **Examples that drift from the format.** Examples are normative — if they
  don't match the schema, the model copies the example, not the schema.
- **Inferring guardrails the user didn't ask for.** Safety is the user's call,
  not yours. Ask.
- **Tool sections without anti-triggers.** Telling the model when *not* to use
  a tool prevents the most common failure mode (over-calling).
- **Hidden assumptions about memory.** If the prompt references "earlier" or
  "previous", state explicitly what context the model receives.

## Delivery

Return the prompt as a single fenced markdown block the user can copy directly.
Below the block, add a short note (≤3 lines) listing:

1. Any assumptions you made.
2. Any Open Questions the user still needs to resolve.
3. One concrete suggestion for how to test the prompt (e.g. "run the example
   inputs through your model and compare to the example outputs").

Do not summarize the prompt's contents — the user can read it.
