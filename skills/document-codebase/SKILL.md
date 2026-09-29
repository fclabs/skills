---
name: document-codebase
description: >-
  Reverse-engineers and documents an existing (brownfield) repository or
  project — architecture, domain and data model, interfaces, key flows,
  configuration, build/deploy, testing, operations, security, conventions,
  tech debt, and reconstructed decisions — with every claim backed by a
  file:line citation and a confidence label. Use when the user wants to
  document, map, onboard onto, audit, or understand an existing codebase —
  including phrases like "document this repo", "write docs for this project",
  "map this codebase", "how does this legacy system work", "create onboarding
  docs", "reverse-engineer the architecture", or "refresh the codebase docs".
  Not for answering a single question about how some code works — answer that
  directly. Always use this skill instead of improvising a documentation
  format on your own.
---

# Document Codebase Skill

Brownfield code is the only reliable source of truth about a brownfield system —
existing READMEs, wikis, and comments are claims to be checked, not facts. This
skill produces documentation that is **evidence-backed**: every non-trivial
statement points to the code or command output that proves it, and anything
that could not be proven is labelled as such.

Wrong-but-confident documentation is worse than none. When in doubt, write it
down as an Open Question instead of guessing.

The process is: scope (§0) → resolve paths (§1) → explore into an evidence
inventory (§3) → draft sections from the inventory (§4–§6) → quality gate
(§7) → report (§8).

**If generated docs already exist** (any target file starts with
`<!-- generated-by: document-codebase -->`), this is a refresh: read
[references/refresh.md](references/refresh.md) and follow it instead of
starting from §3.

## 0. Scope the job

Ask the user (in one message, skip anything already stated):

1. **Audience & purpose** — onboarding humans, planning a migration/rewrite,
   an audit, or context for AI agents/specs? This decides which sections get
   depth (see §4 priority table). Default: **onboarding**.
2. **Depth** — `overview` (fast; sections 01 and 15 plus the audience's
   "go deep" row in §4) or `full` (all sections). Default: `full`. The
   selected sections are this run's scope; the rest are `Not assessed` (§4).
3. **Boundaries** — whole repo, or specific packages/services? For monorepos,
   show the unit list you detected (§1 "Monorepos") and confirm which units
   to document; each one gets its own full set of sections. Default: whole
   repo, every unit.
4. **Execution** — inspection is always allowed: reading files, searching,
   and local read-only git commands (`git log`, `git shortlog`, `git diff`,
   `git status`, `git blame`, `git cat-file`, `git merge-base`). Executing
   project code or changing local state — installing dependencies, building,
   running tests, linters, or scripts — needs the user's yes. Default:
   **read-only** (inspection only). Never run commands that touch remote
   systems (including `git fetch`/`pull`/`push`), databases outside local
   dev, or deploy targets.

If the user says "just do it", use the defaults and state them in the index.

## 1. Resolve output paths

- If the user provides a destination, use it.
- Otherwise look for the project's documentation space, in order: an existing
  `docs/` tree, a docs site config (`mkdocs.yml`, `docusaurus.config.*`,
  `mdbook.toml`), or the location `CLAUDE.md`/`CONTRIBUTING.md` names. Write
  under `<docs>/codebase/`. If none exists, create `docs/codebase/`.
- **Layout by size** — count source files (excluding vendored, generated, and
  lock files); in a monorepo, count per unit and choose per unit:
  - **< ~50 files** → single file `README.md` with all sections.
  - **Otherwise** → one file per section plus an index (see §5).
- **Monorepo** → each unit is documented as its own system (see "Monorepos"
  below), in a sub-folder at the unit's path in the repo
  (`services/billing/` → `<docs>/codebase/services/billing/`).
- **Mirror the code tree** — per-module docs (capsules, §6) follow the
  repository's folder structure so readers find a module's docs where they
  would find its code:
  - **Folder names are copied from the code, exactly** — same spelling,
    case, and nesting. If services live under `src/services/`, their docs
    live under `capsules/services/`. Never rename, translate, merge, or
    regroup folders in the docs tree. The only folder you may drop is a
    single wrapper that holds all source (`src/`, `lib/`, `app/`); record
    that choice in the index.
  - **File names describe the content**, not the folder or file they came
    from: kebab-case, named after the module's responsibility as recorded
    in the inventory (§3). `src/services/pmt/` →
    `capsules/services/payment-processing.md`, not `pmt.md`;
    `src/services/notif_worker.py` →
    `capsules/services/email-and-sms-notifications.md`. Siblings must not
    collide; if two would, make both names more specific.
  - **Names are stable** — once written, keep a file's name on refresh unless
    the module's responsibility changes; other docs and specs link to it.
- Never overwrite hand-written docs. If a target file exists and has no
  generated header (§5), write to `<name>.generated.md` beside it (e.g.
  `README.generated.md`) and tell the user. Later runs treat that file as
  the target.

### Monorepos — every unit is its own system

A monorepo has no single "whole system" to describe: an overview, an
architecture, or a data model written for the whole repo blurs together
projects that are built, deployed, and owned separately. So the 15 sections
(§4) are written **per unit**, never once for the repo.

- **What a unit is** — each project, service, app, or shared library that
  has its own manifest, entry point, or deploy target. Find them from the
  workspace config (`pnpm-workspace.yaml`, `package.json` workspaces,
  `nx.json`, `turbo.json`, `lerna.json`, `go.work`, Cargo `[workspace]`,
  Gradle/Maven modules, `uv` workspace) or the conventional folders
  (`apps/*`, `services/*`, `packages/*`, `libs/*`). Confirm the unit list
  with the user in §0.
- **Each unit gets the full section set** — `<docs>/codebase/<unit path>/`
  holds its own `00-index.md`, sections `01`–`15` (or its `README.md` in the
  single-file layout), `_inventory.md`, and `capsules/`. Depth, audience
  priority, and `Not assessed`/`N/A` states apply per unit. In every unit
  section, "the system" means that unit: 01 is what this service does, 03
  its architecture, 04 the data it owns, 08 how it is built and deployed.
  A shared library still gets all 15; sections that don't apply (e.g. 10
  Operations for a library with no runtime) are `N/A` with a reason.
- **Sibling units are external dependencies** — when a unit calls, imports,
  or consumes events from another unit, document that edge in the caller's
  02 (internal packages) or 05 (interfaces) and link to the sibling's docs;
  never re-describe the sibling's internals.
- **Repo-level shared tooling** (root CI, root build scripts, shared lint
  or TypeScript config, shared IaC) is documented in each unit's section
  where it applies (08, 09, 12), citing the root files. The repo index
  summarises it once.
- **The repo root holds only cross-unit material** — no `01`–`14` at the top
  level:
  - `00-index.md` — the scoping answers, the unit table (path, kind,
    one-line purpose, link, confidence, `Commit:`), a Mermaid `flowchart` of
    how units depend on each other (imports, calls, events, shared data
    stores — each edge cited), a shared-tooling summary, and the top risks
    across units.
  - `15-open-questions.md` — only questions that span units.

State the resolved paths to the user before exploring — in a monorepo, the
unit list with each unit's docs folder and layout.

## 2. Evidence rules (apply to every section)

1. **Cite everything load-bearing** — use `path/to/file.ext:LINE` (or
   `:START-END`), path relative to the repo root, in backticks. For behavior
   spread across files, cite the entry point and the decisive line. For facts
   from commands, cite the command (`git log --follow …`). A claim is
   load-bearing when a reader would act on it: a contract, a data owner, a
   setup step, a default, a security finding, a flow step.
2. **Label confidence** on each claim that isn't a direct restatement of code:
   - `[verified]` — observed by running it (execution mode only), or a
     conclusion that required reading several cited locations together.
   - `[inferred]` — reasoned from naming, structure, history, or partial
     evidence. Say what the inference rests on.
   - `[unknown]` — investigated, but the evidence is insufficient. Put its
     Open Question ID on the same line: `[unknown] (OQ-004)`.
   Unlabelled statements are direct restatements of code: each must carry a
   citation, and none may rest on inference or on having run something.
3. **Existing docs are claims** — when a README/wiki/comment disagrees with
   the code, document what the code does and record the discrepancy under
   Open Questions (or Tech Debt if clearly stale).
4. **Never include secret values** — document where a secret comes from
   (env var name, vault path), never its value. If you find a committed
   secret, flag it in Security as a finding with the file path only.
5. **Describe, don't redesign** — record what *is*. Recommendations belong
   only in Tech Debt & Risks, clearly marked as recommendations.
6. **No invented intent** — "why" statements come from commits, PRs, ADRs, or
   comments (cite them). Otherwise mark `[inferred]`.
7. **Know what the repository can't establish** — some requested facts live
   outside the code. Each needs the evidence below; without it, write
   `[unknown] (OQ-NNN) — needs <evidence>`. Group these under one Open
   Question per kind (not one per dependency or flag). They don't lower a
   section's confidence (§5) or make the docs incomplete.

   | Claim | Acceptable evidence | What the repo alone supports |
   |---|---|---|
   | Lifecycle status (active / maintenance / sunsetting) | Maintainer statement: deprecation notice, ADR, README, or the user | Commit activity, as `[inferred]` |
   | Dependency EOL / deprecation | Dated upstream source (vendor EOL page, release notes, advisory) — cite URL and access date — compared against the lock-file version | Pinned versions only |
   | Feature flag state | Evidence for a named environment: that environment's checked-in config, or a flag-service export the user supplies | Default value in code and where it is evaluated |
   | Test coverage | A measured report (CI artifact, or a run in execution mode) with its date and commit | Which areas have tests; never a percentage |
   | Ownership / bus factor | `CODEOWNERS`, team docs, or the user | Past contributors from git history, labelled as such |
   | Runtime behavior (effective timeouts, traffic, latency) | Logs/metrics the user supplies, or execution | Configured values only |

   Looking up public upstream sources (EOL pages, release notes) is
   inspection, not execution, when a web tool is available.

**Calibration example** — the four kinds of statement, and an `N/A`:

```markdown
Invoices are created by `POST /invoices`, registered at
`src/api/routes.py:42` and handled by `InvoiceService.create`
(`src/billing/service.py:88-131`).                       ← unlabelled: restates code

A draft invoice is never charged: `charge()` is only reachable from
`finalize()` (`src/billing/service.py:140`), and `finalize()` rejects drafts
without a line item (`src/billing/service.py:152`). [verified]
                                                          ← conclusion across cited lines

Retries are probably meant to be idempotent — the Stripe client sets an
`Idempotency-Key` header (`src/billing/stripe.py:30`), but nothing stores the
key between attempts. [inferred: header present, no persistence found]

Whether the `new_tax_engine` flag is on in production: [unknown] (OQ-007) —
needs the flag-service export for production. Default in code is off
(`src/flags.py:12`).

Message queues: N/A — no queue client in `pyproject.toml`, and no matches
for `publish|subscribe|consume` outside `tests/`.
```

## 3. Explore and build the inventory

Exploration produces an **evidence inventory** before any section prose is
written. Sections are drafted from the inventory rather than from memory of
files read along the way, and refresh re-runs discovery against it.

Work outside-in, from how the system is started to what it touches:

1. **Manifests & docs** — read manifests in full (`package.json`,
   `pyproject.toml`, `go.mod`, `pom.xml`, `Gemfile`, `Cargo.toml`, …),
   Dockerfiles, compose files, CI configs, IaC, and existing docs
   (`README*`, `docs/`, `CLAUDE.md`, `ADR*`, wiki exports). Never read a lock
   file whole: search it for the direct dependencies named in the manifest
   and record name and resolved version only. Build the area map.
2. **Entry points** — `main`, server bootstrap, route/handler registration,
   CLI commands, worker/consumer registration, cron/scheduler definitions.
3. **Interfaces & configuration** — inbound routes and their auth, outbound
   clients, published/consumed events, env vars and config files read,
   feature flags evaluated.
4. **Data layer** — ORM models, schema files, migrations, raw SQL, caches,
   object storage, queues.
5. **Key flows** — pick the 3–7 flows that carry the most business value or
   risk (ask the user if unclear; otherwise rank by route traffic hints, test
   emphasis, and git churn). Trace each from entry point to persistence and
   external calls.
6. **Git history** — mine it for hotspots, contributors, and rationale, always
   with bounded output:
   - churn: `git log --since=12.months --name-only --format= | sort | uniq -c | sort -rn | head -30`
   - contributors: `git shortlog -sn -- <path> | head -10` — who has changed
     it, not who owns it now (§2.7)
   - rationale: `git log --follow -n 20 --format='%h %ad %s' -- <file>` on
     surprising code, then `git show <sha> -- <file>` only for the commits
     whose messages look relevant; read linked PRs.
7. **Verify (only if execution was allowed)** — follow the documented setup
   and run the build and test suite. Skip any step that targets a non-local
   resource (shared databases, cloud accounts, remote seeds or migrations) and
   record it as not run. Record exactly what worked, what failed, and what
   was missing.

**When to stop reading — the coverage policy.** Assign coverage as you go
rather than reading until context runs out:

- Always `inspected`: manifests, entry points, every module a selected flow
  passes through, schema/migration sources, auth and authorization code.
- `sampled` by default: every other area — read its public surface and one
  representative module, and state which files were read.
- `excluded`: vendored, generated, outside boundaries, or deliberately
  skipped — always with a reason.

Upgrade an area from `sampled` to `inspected` only when a section in scope
makes a load-bearing claim about its internals.

**Inventory file** — `<docs>/codebase/_inventory.md` (in the single-file
layout, a final `## Appendix: Inventory` in the README), with the generated
header (§5) and these tables. Every row cites its evidence.

| Table | Columns |
|---|---|
| Areas | path · responsibility · coverage · files read (if `sampled`) or reason (if `excluded`) · doc path (capsule path per §1, or `—`) |
| Entry points | kind (server, CLI, worker, cron, …) · name · location |
| Interfaces | direction (inbound / outbound / publishes / consumes / scheduled) · name (route, host, topic, job) · auth · location |
| Configuration | name (env var, config key, flag) · default · where read |
| Data stores | store · schema source · migrations · writing modules |
| Selected flows | flow · why selected · entry point |
| Docs reviewed | path · agrees with code (yes / partly / no → OQ or Tech Debt) |
| Discovery patterns | target (routes, env reads, events, jobs, migrations) · search pattern or file glob used |

Coverage values:
- `inspected` — read closely enough to support every claim made about it.
- `sampled` — representative files read; generalisations about the rest are
  `[inferred]`.
- `excluded` — claims that depend on it are `Not assessed`.

The discovery patterns are how refresh finds things nothing cites yet
(a new route, env var, or job). Record the patterns you actually used, e.g.
the router's registration call, `os.environ`/`process.env`, the queue
client's publish/subscribe calls, the migrations directory.

**Before drafting**, read the inventory for gaps: an area with no
responsibility, an inbound interface with no auth recorded, a config value
read but never defaulted, a flow that ends before persistence. Resolve each
with a targeted read, or turn it into an `[unknown]` and an Open Question.

**Large repos** — split exploration by area or by unit and run subagents in
parallel. In a monorepo, give each unit its own subagent, which builds that
unit's inventory and writes all of that unit's sections. Give each subagent the evidence rules (§2) verbatim, the coverage
policy, its assigned paths, and the inventory format. Require inventory rows
for its areas first, then draft markdown with citations for its sections.
Merge the inventory first (deduplicate, resolve contradictions against the
code), then the sections, keeping one voice.

## 4. Sections to produce

The sections below describe one system: the repository, or, in a monorepo,
each unit separately (§1 "Monorepos"). "The system" in the table means that
unit.

Every section in scope (§0) ends in exactly one of these states, and so does
every item inside a section. Never silently omit.

- **Filled** — documented with citations.
- `N/A — <reason>` — the thing does not exist in this system (no queues, no
  UI). Say what was searched to establish its absence.
- `Not assessed — <reason>` — outside this run's scope: depth, boundaries, or
  an `excluded` area. This is a scope choice, not a gap.
- `[unknown] (OQ-NNN)` — investigated, but the evidence is insufficient.

In `overview` mode, sections outside the selected set are not written; the
index lists them as `Not assessed — overview depth`.

| # | Section | File | Contents |
|---|---|---|---|
| 01 | Overview | `01-overview.md` | What the system does, for whom, which business problem; lifecycle status (evidence per §2.7); glossary of domain terms *as they appear in code* (term → meaning → where defined). |
| 02 | Tech stack | `02-tech-stack.md` | Languages, frameworks, runtimes with versions; key libraries and the job each does; outdated/deprecated/EOL dependencies (dated upstream source per §2.7, or `not checked`); internal/private packages. |
| 03 | Architecture | `03-architecture.md` | Architectural style and how consistently it holds; system context diagram; container/component diagram; directory & module map (folder → responsibility); dependency direction, cycles, and layering violations. |
| 04 | Domain & data | `04-domain-and-data.md` | Core entities and relationships (ERD); schema source of truth and migration history; data ownership (module → tables it writes); lifecycle/state machines of key entities; business rules and *where* each is enforced (flag rules enforced in multiple places or only in the UI). |
| 05 | Interfaces | `05-interfaces.md` | Inbound (REST/GraphQL/gRPC/CLI/webhooks/UI routes) with auth; outbound third-party integrations with auth, configured timeouts, retries, failure handling; async events/messages published and consumed (topic, payload shape, producer, consumers); scheduled jobs (trigger, frequency, what they do). |
| 06 | Key flows | `06-key-flows.md` | Each selected flow traced step by step with citations; sequence diagram for any flow crossing 3+ components; where errors are handled, retried, or swallowed. |
| 07 | Configuration | `07-configuration.md` | Env vars and config files (name, required?, default, effect, where read); feature flags (name, default in code, where evaluated; per-environment state only with environment evidence per §2.7); per-environment differences; secret sources (never values). |
| 08 | Build, run & deploy | `08-build-run-deploy.md` | Local setup from zero (mark each step `[verified]` only if run, otherwise `[inferred]`); build/packaging; CI/CD stages; infrastructure and hosting; release and versioning process. |
| 09 | Testing & quality | `09-testing-and-quality.md` | Test layout and how to run it; coverage (measured figure with its source, or `not measured` per §2.7); critical paths without tests; lint/format/type-check tooling and whether CI enforces it. |
| 10 | Operations | `10-operations.md` | Logging style, metrics, tracing, alerting; health checks; runbooks; performance-sensitive areas (N+1s, heavy jobs, unbounded queries). |
| 11 | Security | `11-security.md` | Authentication mechanism; authorization model and where it is enforced; PII/sensitive data locations; findings (committed secrets, missing authz checks, unsafe input handling, weak crypto) — class of issue and location only, no exploit steps. |
| 12 | Conventions | `12-conventions.md` | Patterns the code actually follows (naming, layering, error handling, DI, logging, testing style) with a canonical example file for each; where the code deviates and which variant new code should copy. |
| 13 | Tech debt & risks | `13-tech-debt-and-risks.md` | Hotspots (high churn × high complexity); dead code; duplicated logic; TODO/FIXME/HACK clusters; single-contributor areas (past contributors from git, not ownership); risk register ranked by severity (High/Med/Low) with impact and a suggested next step. |
| 14 | Decisions | `14-decisions.md` | Reconstructed ADR-style entries: context → decision → consequences → source (commit/PR/comment). Every entry lacking a primary source is `[inferred]`. |
| 15 | Open questions | `15-open-questions.md` | One `### OQ-NNN — <title>` heading per question the code can't answer, each with what was checked, what evidence would settle it, why it matters, and who likely knows (by role, `CODEOWNERS`, or recent contributor). |

**Priority by audience** — in `full` mode, where to spend depth when time or
context is tight; in `overview` mode, the "go deep" row (plus 01 and 15) is
the section set:

| Audience | Go deep on | Keep brief |
|---|---|---|
| Onboarding | 01, 03, 06, 08, 12 | 11, 13, 14 |
| Migration / rewrite | 03, 04, 05, 06, 13, 14 | 08, 10 |
| Audit | 09, 10, 11, 13 | 01, 12 |
| AI / spec context | 03, 04, 05, 12 + capsules (§6) | 08, 10 |

**Open Question IDs** — `OQ-NNN`, numbered in order and never reused. In a
monorepo, each unit numbers its own questions with the unit's name as a
prefix (`OQ-billing-003`) in its own `15-open-questions.md`. Questions that
span units go in the repo-level `15-open-questions.md` without a prefix.

## 5. Output format

**Generated header** — every generated section, index, and inventory file
starts with the block below. Capsules use the §6 header instead.

```
<!-- generated-by: document-codebase -->
# <Section title>

Scope: <repo or unit path>
Commit: <full 40-character SHA of HEAD> (<branch>)
Worktree: <clean | dirty>
Generated: <YYYY-MM-DD>
Confidence: <High | Medium | Low> — <one-line reason>
```

The header is how later runs recognise generated files and detect staleness.
`Worktree: dirty` means the run documented uncommitted changes on top of
`Commit:` (refresh only).

**Confidence** — one rule, applied per file:

- **High** — every load-bearing claim is unlabelled-and-cited or `[verified]`,
  and every area it describes is `inspected`.
- **Medium** — any load-bearing claim is `[inferred]`, or rests on a
  `sampled` area.
- **Low** — any load-bearing claim is `[unknown]`, other than the §2.7 kinds.

The overall confidence in the index and the closing report is the lowest
confidence of any in-scope file. Label counts are reported next to it, not
folded into it.

**Index** — `00-index.md` (or the top of the single-file README) contains:
scoping answers from §0 (audience, depth, boundaries, execution mode — marking
which were defaults), a one-paragraph system summary, a table of sections with
one-line summaries, state (§4), confidence, and each section's `Commit:`;
inventory coverage counts (areas inspected / sampled / excluded) with a link
to the inventory; the top 5 risks from §13 (or `Not assessed` when 13 is out
of scope); and the count of open questions. In a monorepo, each unit has
this index for its own sections, and the repo-level `00-index.md` has the
cross-unit contents listed in §1 "Monorepos". The repo-level index's
confidence is the lowest of any unit's.

**Diagrams** — Mermaid only, so they render in GitHub and stay diffable:
- `flowchart` for system context and components,
- `erDiagram` for the data model,
- `sequenceDiagram` for key flows,
- `stateDiagram-v2` for entity lifecycles.

Keep diagrams consistent with the text — every node names a real component and
has a citation in the surrounding prose.

**Style** — present tense, indicative mood ("The worker polls `jobs` every 30s"),
short paragraphs, tables for anything enumerable. Link between sections with
relative links rather than repeating content.

## 6. Baseline capsules (optional; default on for AI/spec audience)

For each major module or bounded area, write a context capsule under
`<docs>/codebase/capsules/` (in a monorepo, `<docs>/codebase/<unit>/capsules/`),
at the path the §1 mirroring rule gives: the module's parent folders copied
from the code, and a file name describing what the module does. For example:

```
src/                                 docs/codebase/capsules/
  services/                            services/
    pmt/            ──────────────►      payment-processing.md
    notif_worker.py ──────────────►      email-and-sms-notifications.md
  api/                                 api/
    v2/                                  v2/
      routes/       ──────────────►        public-rest-endpoints.md
```

Section 03's directory & module map links each folder to its capsule. The section layout matches
what `freeze-spec` produces, and `write-spec` reads both kinds as context for
new specs. Capsules use this header in place of the §5 block:

```
<!-- generated-by: document-codebase -->
# Baseline: <module name>

Source: <module path>
Status: EXISTING (undocumented baseline)
Commit: <full 40-character SHA of HEAD> (<branch>)
Worktree: <clean | dirty>
Generated: <YYYY-MM-DD>
Confidence: <High | Medium | Low> — <one-line reason>

## Purpose
## What it does
## Public interfaces / data   ← representative contracts copied verbatim from code, cited
## Key decisions              ← from §14, with confidence labels
## Known limits (still true at capture)
## Deliberately excluded      ← what this capsule leaves out (internals, neighbouring modules)
```

Cap each capsule at ~150 lines. Copy verbatim the contracts other modules
actually use (signatures, payloads, key schema fragments). For large schemas
(OpenAPI, GraphQL SDL, protobuf, a full DB schema), cite and link the source
file instead of inlining it.

**Baseline capsules are mutable**: they describe the code at their `Commit:`,
refresh regenerates them, and nobody hand-edits them. **`freeze-spec` capsules
are immutable** records of a shipped spec, and this skill never modifies
them. If both exist for the same area, the baseline describes current
behavior; record any disagreement as an Open Question.

## 7. Quality gate

First run the mechanical checks — from this skill's directory:

```
python3 scripts/check_docs.py <docs>/codebase --repo <repo root>
```

It fails on: a generated file missing a header field, a missing or
out-of-range citation, an `[unknown]` without an `OQ-` ID, an `OQ-` ID with no
heading in an open-questions file, and text that looks like a secret. Fix
every failure and re-run until it passes. It also prints label counts (for
§8) and a random sample of citations to spot-check.

Then check the judgment calls and fix:

- [ ] Every area in the inventory has a coverage value that follows the
      coverage policy (§3).
- [ ] Every section in this run's scope is filled, `N/A`, `Not assessed`, or
      `[unknown]` per §4; `N/A` says what was searched.
- [ ] Monorepo: every unit in scope has its own index, inventory, and
      section set; the repo root has only `00-index.md` and the cross-unit
      `15-open-questions.md`; no unit section describes a sibling's
      internals instead of linking to it; every edge in the unit
      dependency diagram is cited.
- [ ] Every load-bearing claim has a citation. Re-open every citation in the
      script's sample (10% of all citations, at least 10) and confirm each
      line says what the claim says.
- [ ] Every `[inferred]` states what it rests on.
- [ ] Every §2.7 claim (lifecycle, EOL, flag state, coverage, ownership,
      runtime behavior) has the required evidence or is `[unknown]`.
- [ ] Each file's `Confidence:` follows the §5 rule.
- [ ] Diagrams match the text (same components, same names).
- [ ] The capsule tree mirrors the code's folders (§1), each capsule's name
      describes its content, and the inventory's doc paths match the files.
- [ ] Setup steps in §08 are marked `[verified]` only if actually run.
- [ ] Discrepancies between old docs and code are recorded.
- [ ] No recommendations outside §13.

## 8. After writing

Print:

```
Codebase docs written to <path> (<N> files, commit <short SHA>).
Mode: <overview|full>, <read-only|verified>, audience: <audience>.
Coverage: <n> areas inspected / <n> sampled / <n> excluded — see <path to inventory>.
Confidence: <lowest in-scope file confidence> — labels: <n> verified / <n> inferred / <n> unknown.
Top risks:
  1. <risk> (<section link>)
  ...
Open questions: <count> — see <path to 15-open-questions.md>.
```

In a monorepo, print one line per unit (path, docs folder, confidence, open
questions), then the repo totals, the top risks across units, and the count
of cross-unit open questions.

Then suggest the next step based on the audience: `write-spec` for new work
(it reads the baseline capsules as context) (AI/spec), `ddd-analysis` seeded
with the glossary and domain model (migration), or resolving the open
questions with the listed owners (all audiences).
