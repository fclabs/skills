# Skills

A collection of Claude Code skills for AI-driven development workflows.

## Repository Layout

```
skills/          # one directory per skill, each with a SKILL.md
docs/            # guides about using the skills
```

Each skill lives at `skills/<name>/SKILL.md`. To install one, copy or symlink its
directory into `~/.claude/skills/` (user-wide) or `.claude/skills/` (project-only) —
the skill directory itself, not the `skills/` wrapper.

## Available Skills

### Specification & Planning

| Skill | Description |
|---|---|
| [write-spec](skills/write-spec/SKILL.md) | Writes and refines specs for AI-driven development. Guides discovery with targeted questions, then produces unambiguous requirements with testable verification criteria. |
| [review-spec](skills/review-spec/SKILL.md) | Reviews a spec across ten quality dimensions (goal clarity, actors, inputs/outputs, failure modes, etc.) and produces a prioritized list of issues, warnings, and suggestions. |
| [write-spec-plan](skills/write-spec-plan/SKILL.md) | Generates an iterative implementation plan from a spec file and writes it to a companion `-plan.md` file. Requires the spec to have passed `review-spec` first. |

### Implementation & Verification

| Skill | Description |
|---|---|
| [implement-spec-plan](skills/implement-spec-plan/SKILL.md) | Executes a plan file one iteration at a time, verifying acceptance criteria and running full regression tests before advancing. |
| [verify-spec](skills/verify-spec/SKILL.md) | Confirms the codebase fully satisfies a spec by walking through each iteration's acceptance criteria and running the full test suite. |
| [freeze-spec](skills/freeze-spec/SKILL.md) | Distills a completed spec into a compact, immutable "context capsule" — preserving purpose, public interfaces, key decisions, and known limits while dropping internal mechanics — for use as background context in future work. |

### Domain Modeling

| Skill | Description |
|---|---|
| [ddd-analysis](skills/ddd-analysis/SKILL.md) | Produces a complete Domain-Driven Design document (ubiquitous language, bounded contexts, aggregates, domain events, etc.) from requirements or a product description, one section at a time with user confirmation. |

### Python Development

| Skill | Description |
|---|---|
| [python-coding](skills/python-coding/SKILL.md) | Standards and conventions for Python projects using `uv`, `ruff`, `ty`, strict typing, FastAPI, Strawberry, SQLAlchemy, Alembic, and Pydantic. |
| [using-pytest](skills/using-pytest/SKILL.md) | Guidelines for writing pytest tests following Given/When/Then/Clean patterns, with business-readable docstrings and organized test layers (unit, functional, interface, integration, evals). |

### AI Tooling

| Skill | Description |
|---|---|
| [write-system-prompt](skills/write-system-prompt/SKILL.md) | Authors production-quality system prompts for LLM agents and assistants. Asks clarifying questions before drafting and structures output across role, instructions, constraints, output format, examples, and tools. |

## Typical Workflow

```
write-spec → review-spec → write-spec-plan → implement-spec-plan → verify-spec
```

New to spec-driven development? Read the
[Spec-Driven Development guide](docs/spec-driven-development.md) — an orientative
walkthrough of the six spec skills, what each stage produces, and the mistakes
beginners usually make.
