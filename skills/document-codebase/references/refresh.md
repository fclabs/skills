# Incremental refresh

Use this when generated docs already exist (a target file starts with
`<!-- generated-by: document-codebase -->`). Everything in SKILL.md §2–§8
still applies; this file replaces "explore from scratch" with "re-run
discovery on what changed".

## Choose the refresh unit

- **Per-section layout** — refresh section by section, as below.
- **Single-file layout** (`README.md` with an `## Appendix: Inventory`) — the
  file has one header, so it cannot record which sections are older than
  others. Use the appendix as the inventory for steps 1–5, then regenerate the
  whole file in step 8.
- **Monorepo** — refresh each unit on its own, against that unit's inventory
  and headers. Units added or removed since the last run are those that
  differ from the unit list in the top-level `00-index.md`; document new units
  from scratch (SKILL.md §3) and mark removed units as removed in the
  top-level index. Refresh the top-level index last.

## Steps

1. **Collect the recorded commits** — read `Commit:` from the inventory and
   from every generated file in the unit. If the inventory is missing (docs
   predate it), rebuild it with SKILL.md §3 before continuing.
2. **Check every commit is in HEAD's history** — for each SHA, run
   `git merge-base --is-ancestor <sha> HEAD`. `git cat-file -e` is not
   enough: a commit that exists only on another branch passes it, and a diff
   from it lists the wrong files. If any SHA fails (rebased or squashed
   history, shallow clone, docs generated on another branch), say which and
   do a full regeneration of the unit instead of a partial one.
3. **Pick the baseline** — `git merge-base --octopus <all SHAs>` (with one SHA,
   the baseline is that SHA). This is the newest commit every recorded SHA
   descends from, so diffing from it can only list too many files, never too
   few.
4. **Handle the working tree** — run `git status --porcelain`.
   - If it is dirty, ask whether to document `HEAD` only (default) or include
     uncommitted changes. Including them means also diffing the working tree
     against `HEAD`, taking untracked files from `git status`, and writing
     `Worktree: dirty` in every header this run writes. `Commit:` stays the
     full SHA of `HEAD`.
   - If any existing file says `Worktree: dirty`, its content may describe
     changes that were later discarded, so the diff cannot be trusted for it:
     treat that file as affected in step 7, whatever the diff says.
5. **List changes** — `git diff --name-status -M <baseline>..HEAD`, which
   reports added, modified, deleted, and renamed files separately.
6. **Re-run discovery on changed areas** — map each changed path to an area
   in the inventory. For paths in no known area, add a new area and explore
   it (SKILL.md §3 steps 1–5, scoped to it, with the coverage policy). For
   every changed or new area, re-run the inventory's discovery patterns to
   find new or removed entry points, interfaces, config values, data stores,
   and jobs. If manifests, lock files, CI, or IaC changed, redo SKILL.md §3 step 1 for
   them. Update the inventory rows and their coverage.
7. **Work out affected sections** — a section is affected if it:
   - cites a changed, renamed, or deleted file;
   - draws on an inventory row that was added, changed, or removed (areas →
     03; entry points and interfaces → 05, 06; configuration → 07, 11; data
     stores → 04; manifests → 02; CI/IaC → 08; tests → 09);
   - depends on an affected section: a key flow (06) or capsule that runs
     through a changed interface, a diagram whose nodes changed, a decision
     (14) about changed code;
   - has `Worktree: dirty` in its header (step 4).
8. **Apply renames and deletions everywhere** — rewrite citations to renamed
   files across all sections, including unaffected ones; an unaffected
   section's `Commit:` can then move to `HEAD`, because nothing else it cites
   changed. For deleted files, remove or re-source the claims that cited
   them; never leave a citation to a file that no longer exists.
9. **Regenerate** the affected sections and capsules (or the whole file in the
   single-file layout); re-check every citation in them and fix drifted
   lines; update their header `Commit:`, `Worktree:`, `Generated:`, and
   `Confidence:`.
10. **Refresh the derived artifacts every time**: the index (summaries,
    states, confidence, per-section `Commit:`, coverage counts, top risks),
    section 13 if hotspots or risks changed, and section 15. In section 15, close Open Questions
    the new code answers (mark them `Resolved in <short SHA>`, don't delete
    them) and number new ones after the highest existing ID in that unit;
    never reuse an ID.
11. **Run the quality gate** (SKILL.md §7) over the whole docs tree, not only
    the regenerated files — renames and deletions can break citations
    anywhere.
12. **Report** which sections and capsules were refreshed and why, which were
    left untouched, which units or areas were added to or removed from the
    inventory, and whether a full regeneration was forced (and by which SHA).
