---
name: ddd-analysis
description: Perform a rigorous Domain-Driven Design (DDD) analysis from requirements or product descriptions and produce a structured DDD document section by section. Use whenever the user mentions domain-driven design, DDD, bounded contexts, ubiquitous language, aggregates, domain events, strategic design, tactical design, or asks to model/analyze a domain from requirements or product specs.
---

# DDD Analysis Skill

## Overview

This skill guides the agent through producing a complete Domain-Driven Design document from a requirements description or product spec. The document is built section by section, with user confirmation before moving to the next section.

## Core Behavior Rules

1. Never skip ahead. Complete and present one section at a time. Wait for explicit user confirmation (for example: "looks good", "continue", "approved", "yes") before proceeding.
2. Ask before starting if the input is ambiguous or missing. Request requirements or a product description.
3. Use domain language from the input. Avoid generic placeholders.
4. Be specific and concrete. Infer real domain concepts from the requirements; avoid generic DDD boilerplate.
5. Remind the user at each step that they can request revisions before continuing.

## Workflow

### Step 0 - Gather Input

If requirements or product description are missing, ask:

> Please share the product description or requirements you'd like me to analyze. This can be a rough spec, user stories, a paragraph description, or any level of detail.

When input is available, confirm the plan:

> Great! I'll analyze the domain and build the DDD document one section at a time. After each section I'll pause so you can review and suggest changes before we move on. Ready? Let's start with the Ubiquitous Language.

### Section 1 - Ubiquitous Language (Glossary)

Goal: Define significant domain terms so technical and business stakeholders share a single, unambiguous vocabulary.

Instructions:
- Scan requirements for nouns (things), verbs (actions/processes), and adjectives carrying domain meaning.
- Group terms into Entities, Actions/Processes, States/Statuses, and Supporting Concepts.
- If a term has multiple meanings in different contexts, capture each meaning with its context.
- Write business-friendly definitions without unnecessary jargon.

Output format:

```markdown
## 1. Ubiquitous Language (Glossary)

### Core Terms

| Term | Definition | Context Notes |
|------|-----------|---------------|
| [Term] | [Clear definition] | [e.g., "Means X in Billing, Y in Support"] |

### Actions & Processes

| Term | Definition |
|------|-----------|
| [Verb/Process] | [What it means in the domain] |

### Context-Specific Meanings

**[Term]**
- In [Context A]: [Meaning]
- In [Context B]: [Different meaning]
```

After presenting Section 1:

> That's the Ubiquitous Language. Does this capture the terminology accurately? Feel free to add, rename, or clarify any terms - once you approve, we'll move on to Strategic Mapping.

### Section 2 - Strategic Mapping

Proceed only after user approval of Section 1.

Goal: Identify bounded contexts and map their relationships.

Part A: Bounded Contexts
- Identify distinct business subdomains where each bounded context owns its model and language.
- Classify each as Core Domain, Supporting Subdomain, or Generic Subdomain.
- Briefly describe each context's responsibilities.

Part B: Context Map
- Capture context relationships using DDD patterns:
  - Upstream / Downstream (U/D)
  - Customer-Supplier
  - Conformist
  - Anti-Corruption Layer (ACL)
  - Shared Kernel
  - Open Host Service / Published Language

Output format:

```markdown
## 2. Strategic Mapping

### 2.1 Bounded Contexts

| Context Name | Type | Responsibilities |
|-------------|------|-----------------|
| [Name] | Core / Supporting / Generic | [What it owns and does] |

### 2.2 Context Map

**[Context A] -> [Context B]**
- Relationship: [Pattern name]
- Direction: [Upstream/Downstream or bidirectional]
- Integration: [What data/events cross the boundary and how]

[Repeat for each relationship]

### Context Map Diagram (Text)

[Context A] --[U]--> [Context B]
[Context C] --[ACL]--> [Context D]
... (ASCII or text-based diagram)
```

After presenting Section 2:

> That's the Strategic Map. Does the breakdown of contexts and their relationships match your vision? Approve or suggest changes, and we'll dive into the Tactical Design next.

### Section 3 - Tactical Design (The Model)

Proceed only after user approval of Section 2.

Goal: Model the internal structure of the most important bounded context(s).

Instructions:
- Focus on the Core Domain first; offer expansion to additional contexts.

Part A: Entities and Value Objects
- Entity: Has unique identity over time.
- Value Object: Defined only by values, immutable, no identity.
- For each, include key attributes and behaviors.

Part B: Aggregates
- Group entities/value objects that must remain consistent together.
- Identify aggregate root as the only entry point.
- Define aggregate invariants.

Part C: Domain Services
- Identify operations that do not naturally belong to one Entity or Value Object.
- Document service purpose, inputs, outputs, and rationale.

Output format:

```markdown
## 3. Tactical Design - [Context Name]

### 3.1 Entities

**[EntityName]** (Entity)
- Identity: `[id field]`
- Key Attributes: [list]
- Key Behaviors: [list of methods/operations]

### 3.2 Value Objects

**[ValueObjectName]** (Value Object)
- Attributes: [list]
- Rules/Constraints: [e.g., "Email must be valid format"]

### 3.3 Aggregates

**[AggregateName] Aggregate**
- Aggregate Root: `[EntityName]`
- Members: [list of entities and value objects in the aggregate]
- Invariants:
  - [Rule 1 that is always enforced]
  - [Rule 2]

### 3.4 Domain Services

**[ServiceName]**
- Purpose: [What problem it solves]
- Inputs: [What it receives]
- Output: [What it returns or triggers]
- Why not on an Entity: [Brief reasoning]
```

After presenting Section 3:

> That's the Tactical Design. Does the model accurately represent the domain's core logic and structure? Once approved, we'll finish with the Domain Events.

### Section 4 - Domain Events

Proceed only after user approval of Section 3.

Goal: Identify significant domain occurrences that other parts of the system should know about.

Instructions:
- Use past tense event names.
- For each event: include trigger, payload, and consumers.
- Group events by publishing bounded context.
- Mark cross-boundary events explicitly.

Output format:

```markdown
## 4. Domain Events

### [Context Name] Events

**[EventName]** *(e.g., OrderPlaced)*
- Trigger: [What action or condition causes this event]
- Payload: [Key data fields: field1, field2, ...]
- Consumers: [Which contexts/services react to this]
- Cross-boundary: Yes / No

[Repeat for each event]

### Event Flow Summary

[Brief narrative or table showing how events chain together across contexts]
```

After presenting Section 4:

> That completes the Domain Events - and the full DDD document! 🎉
>
> Would you like me to:
> - Compile everything into a single clean document?
> - Revise any section?
> - Go deeper on a specific bounded context's tactical design?

## Final Compilation (On Request)

If requested, assemble all four approved sections into one Markdown document:

```markdown
# Domain-Driven Design Analysis
## [Product/System Name]
*Generated from requirements analysis*
---
[All four sections in order]
```

Offer to save the compiled document as a `.md` file when file tools are available.

## Tips for Quality Output

- Anchor all terms, contexts, and events to the provided requirements.
- Use names that match stakeholder language.
- Keep aggregates small and invariant-focused.
- Keep value objects immutable.
- Use business events, not technical events.
- Ask the user when core domain ownership or terminology is unclear.
