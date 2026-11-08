# DECISIONS (append-only)

Ids are the plan's `D-NNN`; spec decisions are cited as `spec D5`.

## D-001: Fixture spec adds VC-010 and two business rules  (Iteration 1)
**Context**: The spec table gives FR/VC-001..009, but `write-spec` requires a VC for every BR and `review-spec` asks for an end-to-end check; VC-023 needs the fixture to review READY.
**Decision**: Added BR-001 (integer cents) and BR-002 (stdlib only, Python >= 3.11) covered by VC-002 and VC-001, and an end-to-end VC-010. FR/VC-001..009 map to A1..A9 unchanged.
**Rejected**: Omitting BRs/end-to-end check (risks a NEEDS WORK review verdict).
**Consequences**: Checks scanning `VC-00[1-9]` still see exactly 9 ids; VC-010 is extra. Do not renumber.

## D-002: Fixture plans generated once, committed as static templates  (Iteration 1)
**Context**: Three near-identical complete plans are tedious and error-prone to hand-edit.
**Decision**: Generated them with a throwaway script kept outside the repo; only the resulting `.md.tmpl` files are committed.
**Rejected**: Committing the generator (would add an unplanned `.py` under the harness hygiene rules).
**Consequences**: Edit the templates directly; keep the three in sync by hand.

## D-003: Touches format in templates  (Iteration 1)
**Context**: The checker parsers (Iteration 3) must accept what the templates use.
**Decision**: One line of backticked absolute `@DIR@/...` paths, no trailing parentheticals, grouped members list their own record file; artifact dir is `@DIR@/<stem>-artifacts/`.
**Rejected**: Relative paths or bulleted lists (the spec's parser handles them, but one format keeps templates uniform).
**Consequences**: Iteration 3 golden cases should also cover bulleted/relative forms themselves.
