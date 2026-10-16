# Focus areas by artifact type

Pick 2–4 for the "What I most want checked" section of the brief.

| Artifact | Ask coworkers to check |
|---|---|
| Code diff | Logic errors and off-by-ones; unhandled failure paths; concurrency/ordering; security (injection, authz, secrets); behavior changes not covered by tests; API/contract breaks; whether tests actually assert the new behavior |
| Spec / PRD | Ambiguous or untestable requirements; missing actors, failure modes, non-goals; contradictions between sections; requirements with no acceptance criterion |
| Implementation plan | Ordering/dependency errors; iterations too large to verify; missing rollback/migration steps; requirements not mapped to any iteration |
| Architecture / design | Unstated assumptions; scaling and failure modes; coupling and ownership boundaries; simpler alternatives; operational cost |
| Docs / README | Claims not backed by the code; stale commands; missing prerequisites; steps that fail when followed literally |
| Analysis / research | Conclusions that don't follow from the data; unsupported numbers; missing counter-evidence; wrong or unverifiable citations |
| Prompt / skill | Ambiguous instructions; conflicting rules; missing failure handling; instructions a model would likely skip |

Facts worth including in any brief: how to run tests/linters, the base branch or commit, the relevant spec/requirement IDs, known limitations the author already accepts, and the conventions the code must follow.
