#!/usr/bin/env python3
"""Run checker for scenarios S2-S4 plus result bookkeeping.

Modes:
  check_run.py <repo> <plan.md> --transcript F --run K
               --scenario {full,downgrade,failing-member} [--result-out F]
  check_run.py --summary <results-dir> --scenario S          (BR-004)
  check_run.py --mark-failed --scenario S --run K --result-out F [--violation skipped|error]

Prints one `VC-NNN: message` line per violation (NFR-001 for cost), `note:`
lines, `subagents: N`, and exits 1 on violations; exits 2 on usage, missing or
unparseable input and on refused repositories; 0 on success (BR-003).
Read-only on <repo>; the only file it writes is the result file.

Checks plug into CHECKS (see `check`): each is fn(ctx, findings).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import hlib
from hlib import Findings, HarnessError, Plan, Transcript

MAX_AGENTS_S2 = 15       # NFR-001, scenario full
MAX_AGENTS_OTHER = 6     # NFR-001, scenarios downgrade and failing-member
RUN_SCENARIOS = ("full", "downgrade", "failing-member")
ALL_SCENARIOS = ("plan",) + RUN_SCENARIOS
PLAN_IN_REPO = "specs/tinyshop-plan.md"
NOTE_SKILL_SOURCE = "skill-source check skipped"
NOTE_SKILL_SOURCE_UNIMPLEMENTED = "skill-source check requested but not implemented"


# --------------------------------------------------------------------------
# git wrapper: always `-C <repo>` and GIT_OPTIONAL_LOCKS=0
# --------------------------------------------------------------------------

def git(repo: str | Path, *args: str, check: bool = True) -> str:
    """Run `git -C <repo> <args>`, return stdout. HarnessError on failure when check."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        cp = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)
    except OSError as e:
        raise HarnessError(f"cannot run git: {e}")
    if check and cp.returncode != 0:
        raise HarnessError(f"git {' '.join(args)} failed in {repo}: {cp.stderr.strip()}")
    return cp.stdout if cp.returncode == 0 else ""


def git_ok(repo: str | Path, *args: str) -> bool:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    cp = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)
    return cp.returncode == 0


# --------------------------------------------------------------------------
# check registry
# --------------------------------------------------------------------------

@dataclass
class Context:
    """What every check function receives."""
    repo: Path
    plan: Plan
    tr: Transcript
    scenario: str
    run: int


@dataclass
class Check:
    vc_id: str
    scenarios: tuple[str, ...]
    fn: Callable[[Context, Findings], None]


CHECKS: list[Check] = []


def check(vc_id: str, scenarios: tuple[str, ...] = RUN_SCENARIOS):
    """Decorator registering fn(ctx, findings) for the given scenarios.

    A check reports with `findings.add(vc_id, msg)` (violation) or
    `findings.notes.append(text)` (note).  Notes never affect `passed`.
    """
    def deco(fn: Callable[[Context, Findings], None]):
        CHECKS.append(Check(vc_id, tuple(scenarios), fn))
        return fn
    return deco


def max_agents(scenario: str) -> int:
    return MAX_AGENTS_S2 if scenario == "full" else MAX_AGENTS_OTHER


@check("NFR-001")
def check_nfr001(ctx: Context, f: Findings) -> None:
    n = len(hlib.agent_calls(ctx.tr.events))
    limit = max_agents(ctx.scenario)
    if n > limit:
        f.add("NFR-001", f"{n} orchestrator-level Agent calls exceed the maximum {limit} for scenario {ctx.scenario}")


# --------------------------------------------------------------------------
# git history helpers (S2): Commit -> iteration, Member Agent calls
# --------------------------------------------------------------------------

RECORD_RE = re.compile(r"(?:^|/)iterations/(\d+)-[^/]+\.md$")
MERGE_RE = re.compile(r"^Merge iteration (\d+): ")
RECONCILE_RE = re.compile(r"^Reconcile artifacts for iterations (\d+)[–-](\d+)")
SUBJECT_ITER_RE = re.compile(r"\bIteration (\d+)\b", re.I)
ARTIFACT_FILES = ("CONTEXT.md", "DECISIONS.md")


@dataclass
class Commit:
    sha: str
    parents: list[str]
    subject: str


def first_parent_commits(repo: Path) -> list[Commit]:
    """main's first-parent history, oldest first."""
    out = git(repo, "log", "--first-parent", "--reverse", "--format=%H%x1f%P%x1f%s", "main")
    commits = []
    for line in out.splitlines():
        sha, parents, subject = line.split("\x1f", 2)
        commits.append(Commit(sha, parents.split(), subject))
    return commits


def commit_iteration(repo: Path, c: Commit) -> int | None:
    """Commit -> iteration rule: the iteration whose iterations/NN-*.md the commit
    adds (for a merge, what its second parent's branch adds); else the
    `Iteration N` in the subject; else None."""
    if len(c.parents) >= 2:
        out = git(repo, "log", "--diff-filter=A", "--name-only", "--format=",
                  f"{c.parents[0]}..{c.parents[1]}")
    else:
        out = git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root",
                  "--diff-filter=A", c.sha)
    ns = sorted({int(m.group(1)) for p in out.splitlines() if (m := RECORD_RE.search(p))})
    if ns:
        return ns[0]
    m = SUBJECT_ITER_RE.search(c.subject)
    return int(m.group(1)) if m else None


def plan_groups(plan: Plan) -> dict[str, list[int]]:
    """group value -> member iteration numbers, ascending (table cells, per the Parsing rules)."""
    groups: dict[str, list[int]] = {}
    for it in sorted(plan.iterations, key=lambda i: i.n):
        if it.group is not None:
            groups.setdefault(it.group, []).append(it.n)
    return groups


def _norm(s: str) -> str:
    return " ".join(s.split())


def attribute_agent_calls(plan: Plan, calls: list[hlib.ToolUse]) -> dict[int, list[hlib.ToolUse]]:
    """Member Agent calls rule: a call belongs to the iteration whose Goal sentence it
    quotes verbatim (earliest in the prompt wins), else to the iteration whose
    `Iteration N: <name>` string occurs earliest; otherwise it is unattributed (dropped)."""
    out: dict[int, list[hlib.ToolUse]] = {}
    for call in calls:
        prompt = _norm(str(call.input.get("prompt", "")))
        best: tuple[int, int] | None = None
        for it in plan.iterations:
            if it.goal and _norm(it.goal) in prompt:
                pos = prompt.index(_norm(it.goal))
                if best is None or pos < best[0]:
                    best = (pos, it.n)
        if best is None:
            for it in plan.iterations:
                tag = f"Iteration {it.n}: {it.name}" if it.name else ""
                if tag and tag in prompt:
                    pos = prompt.index(tag)
                    if best is None or pos < best[0]:
                        best = (pos, it.n)
        if best is not None:
            out.setdefault(best[1], []).append(call)
    return out


def find_merge(repo: Path, fp: list[Commit], n: int) -> Commit | None:
    """The merge commit of member n on main's first-parent line: subject
    `Merge iteration N: ...`, else a merge commit that maps to n."""
    for c in fp:
        m = MERGE_RE.match(c.subject)
        if m and int(m.group(1)) == n:
            return c
    for c in fp:
        if len(c.parents) >= 2 and commit_iteration(repo, c) == n:
            return c
    return None


def branch_base(repo: Path, merge: Commit, main_fp: set[str]) -> str | None:
    """Walk the merge's second-parent chain back to the commit whose parent lies on
    main's first-parent history; return that parent (the fork point)."""
    c = merge.parents[1]
    for _ in range(1000):
        if c in main_fp:
            return c
        parents = git(repo, "rev-list", "--parents", "-n", "1", c).split()[1:]
        if not parents:
            return None
        if parents[0] in main_fp:
            return parents[0]
        c = parents[0]
    return None


# --------------------------------------------------------------------------
# S2 checks: VC-008 .. VC-011, VC-013
# --------------------------------------------------------------------------

@check("VC-008", ("full",))
def check_vc008(ctx: Context, f: Findings) -> None:
    """Each group: members' Agent calls in one assistant message, all isolation
    "worktree", and the members' branches share one fork point."""
    groups = plan_groups(ctx.plan)
    if not groups:
        return
    attributed = attribute_agent_calls(ctx.plan, hlib.agent_calls(ctx.tr.events))
    fp = first_parent_commits(ctx.repo)
    main_fp = {c.sha for c in fp}
    for g, ns in groups.items():
        calls: list[hlib.ToolUse] = []
        for n in ns:
            mine = attributed.get(n, [])
            if not mine:
                f.add("VC-008", f"group {g}: no Agent call attributed to iteration {n}")
            calls += mine
            for c in mine:
                if c.input.get("isolation") != "worktree":
                    f.add("VC-008", f"group {g}: Agent call for iteration {n} lacks isolation \"worktree\"")
        msgs = {c.msg_index for c in calls}
        if len(msgs) > 1:
            f.add("VC-008", f"group {g}: member Agent calls span {len(msgs)} assistant messages, expected 1")
        bases: dict[int, str | None] = {}
        for n in ns:
            merge = find_merge(ctx.repo, fp, n)
            if merge is None or len(merge.parents) < 2:
                f.notes.append(f"group {g}: no merge commit for iteration {n}; fork point not checked")
                continue
            bases[n] = branch_base(ctx.repo, merge, main_fp)
        if len(set(bases.values())) > 1:
            f.add("VC-008", f"group {g}: member branches do not share one fork point: "
                  + ", ".join(f"{n}={(b or 'none')[:10]}" for n, b in sorted(bases.items())))


@check("VC-009", ("full",))
def check_vc009(ctx: Context, f: Findings) -> None:
    """Per group: ascending `Merge iteration N:` commits, then exactly one Reconcile
    commit touching CONTEXT.md, then only later-iteration commits; one worktree left."""
    fp = first_parent_commits(ctx.repo)
    for g, ns in plan_groups(ctx.plan).items():
        lo, hi = ns[0], ns[-1]
        idx: dict[int, int] = {}
        for n in ns:
            for i, c in enumerate(fp):
                m = MERGE_RE.match(c.subject)
                if m and int(m.group(1)) == n:
                    idx[n] = i
                    break
        missing = [n for n in ns if n not in idx]
        if missing:
            f.add("VC-009", f"group {g}: no `Merge iteration N:` commit for iteration(s) "
                  + ", ".join(map(str, missing)))
            continue
        recs = [i for i, c in enumerate(fp)
                if (m := RECONCILE_RE.match(c.subject)) and (int(m.group(1)), int(m.group(2))) == (lo, hi)]
        if len(recs) != 1:
            f.add("VC-009", f"group {g}: {len(recs)} `Reconcile artifacts for iterations {lo}-{hi}` commits, expected 1")
            continue
        i0 = idx[lo]
        if [idx[n] for n in ns] + [recs[0]] != list(range(i0, i0 + len(ns) + 1)):
            f.add("VC-009", f"group {g}: merges in ascending order directly followed by the Reconcile "
                  "commit expected; found a different order or an extra commit in between")
        rec = fp[recs[0]]
        paths = git(ctx.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", rec.sha).split()
        if not any(p.rsplit("/", 1)[-1] == "CONTEXT.md" for p in paths):
            f.add("VC-009", f"group {g}: the Reconcile commit does not modify CONTEXT.md")
        for c in fp[recs[0] + 1:]:
            n = commit_iteration(ctx.repo, c)
            if n is None or n <= hi:
                f.add("VC-009", f"group {g}: commit after the Reconcile ({c.subject!r}) belongs to "
                      + ("no iteration" if n is None else f"iteration {n}, not a later one"))
                break
    wt = [ln for ln in git(ctx.repo, "worktree", "list", "--porcelain").splitlines() if ln.startswith("worktree ")]
    if len(wt) != 1:
        f.add("VC-009", f"git worktree list shows {len(wt)} worktrees, expected only the main one")


@check("VC-010", ("full",))
def check_vc010(ctx: Context, f: Findings) -> None:
    """Member branches stay inside Touches plus their own record, never touch CONTEXT.md
    or DECISIONS.md; main's iterations/ holds one record per iteration."""
    fp = first_parent_commits(ctx.repo)
    for g, ns in plan_groups(ctx.plan).items():
        for n in ns:
            merge = find_merge(ctx.repo, fp, n)
            if merge is None or len(merge.parents) < 2:
                continue            # absence is VC-009's finding
            out = git(ctx.repo, "log", "--name-only", "--format=", f"{merge.parents[0]}..{merge.parents[1]}")
            touches = ctx.plan.by_n(n).touches
            own = re.compile(rf"(?:^|/)iterations/0*{n}-[^/]+\.md$")
            for p in sorted({ln for ln in out.splitlines() if ln}):
                if p.rsplit("/", 1)[-1] in ARTIFACT_FILES:
                    f.add("VC-010", f"iteration {n}: member branch changes {p}")
                elif not own.search(p) and not any(hlib.paths_overlap(p, t) for t in touches):
                    f.add("VC-010", f"iteration {n}: member branch changes {p}, outside its Touches")
    names = git(ctx.repo, "ls-tree", "-r", "--name-only", "main").splitlines()
    counts: dict[int, int] = {}
    for p in names:
        if m := RECORD_RE.search(p):
            counts[int(m.group(1))] = counts.get(int(m.group(1)), 0) + 1
    for it in ctx.plan.iterations:
        if counts.get(it.n, 0) != 1:
            f.add("VC-010", f"main holds {counts.get(it.n, 0)} iterations/{it.n:02d}-*.md records, expected 1")


@check("VC-011", ("full",))
def check_vc011(ctx: Context, f: Findings) -> None:
    """DECISIONS.md on main: no `D-?`, ids D-001..D-k gap-free, (Iteration N) non-decreasing."""
    paths = [p for p in git(ctx.repo, "ls-tree", "-r", "--name-only", "main").splitlines()
             if p.rsplit("/", 1)[-1] == "DECISIONS.md"]
    if not paths:
        f.add("VC-011", "no DECISIONS.md on main")
        return
    for p in paths:
        text = git(ctx.repo, "show", f"main:{p}")
        if "D-?" in text:
            f.add("VC-011", f"{p} contains the placeholder D-?")
        heads = [ln for ln in text.splitlines() if re.match(r"#{1,6}\s+D-", ln)]
        ids = [int(m.group(1)) for ln in heads if (m := re.match(r"#{1,6}\s+D-(\d+)", ln))]
        if ids != list(range(1, len(ids) + 1)):
            f.add("VC-011", f"{p}: decision ids {ids} are not D-001..D-{len(ids):03d} without gaps")
        its = [int(m.group(1)) for ln in heads if (m := re.search(r"\(Iteration (\d+)\)", ln))]
        if its != sorted(its):
            f.add("VC-011", f"{p}: (Iteration N) values {its} are not non-decreasing")


# VC-013 driver: runs inside the temporary copy with the copy as working directory.
VC013_DRIVER = """
import tomllib
from tinyshop.pricing import price_cents
from tinyshop.tax import tax_cents
from tinyshop.discount import discount_cents
assert price_cents([(250, 2)]) == 500, "price_cents([(250, 2)]) != 500"
assert tax_cents(1000) == 80, "tax_cents(1000) != 80"
assert discount_cents(1000) == 100, "discount_cents(1000) != 100"
with open("tinyshop/rates.toml", "rb") as fh:
    rates = tomllib.load(fh)
assert rates.get("tax_bp") == 800, "rates.toml tax_bp != 800"
assert rates.get("discount_bp") == 1000, "rates.toml discount_bp != 1000"
"""


@check("VC-013", ("full",))
def check_vc013(ctx: Context, f: Findings) -> None:
    """End to end on a copy of the working tree. The copy lives in a tempfile
    directory outside the scratch repo (the only directory check_run.py creates)
    and is removed in the finally block; nothing is written inside <repo>."""
    tmp = tempfile.TemporaryDirectory(prefix="vc013-")
    try:
        work = Path(tmp.name) / "work"
        shutil.copytree(ctx.repo, work, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".claude", "*.pyc"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for label, cmd in (("python -m unittest discover", [sys.executable, "-m", "unittest", "discover"]),
                           ("end-to-end driver", [sys.executable, "-c", VC013_DRIVER])):
            try:
                cp = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300)
            except subprocess.TimeoutExpired:
                f.add("VC-013", f"{label} timed out")
                return
            if cp.returncode != 0:
                tail = (cp.stderr.strip().splitlines() or ["no output"])[-1]
                f.add("VC-013", f"{label} exited {cp.returncode}: {tail}")
                return
    finally:
        tmp.cleanup()


# --------------------------------------------------------------------------
# S2 notes, S3, S4: transcript-text checks (VC-012, VC-014, VC-015)
# --------------------------------------------------------------------------

DOC_PATH_RE = re.compile(r"`(docs/[^`\s]+)`")
DOC_FORBIDDEN_RE = re.compile(r"plan\.md|-artifacts|iterations?\b", re.I)
DOC_SPEC_RE = re.compile(r"\bspec\b", re.I)
GROUP_A_RE = re.compile(r"\b[Gg]roup\W{0,3}A\b")           # VC-014: capital-or-small g, capital A
SEQUENTIAL_RE = re.compile(r"sequential|downgrad", re.I)
ITERATION_2_RE = re.compile(r"iteration 2", re.I)


def find_text_block(blocks: list[hlib.TextBlock], *patterns: re.Pattern[str]) -> hlib.TextBlock | None:
    """First orchestrator text block (transcript order) that matches EVERY pattern.
    Matching is per block: a message's several text blocks are judged one by one."""
    for b in blocks:
        if all(p.search(b.text) for p in patterns):
            return b
    return None


def final_text(blocks: list[hlib.TextBlock]) -> str:
    """Text of the last orchestrator-level assistant text block ('' when none)."""
    return blocks[-1].text if blocks else ""


def first_call(calls: list[hlib.ToolUse]) -> hlib.ToolUse | None:
    return min(calls, key=lambda c: c.event_index) if calls else None


def merge_count(repo: Path) -> int:
    return int(git(repo, "rev-list", "--merges", "--count", "main").strip() or "0")


def doc_files(plan: Plan) -> list[str]:
    """Doc files (Parsing rules): backticked `docs/...` paths in the final iteration's
    Scope, in order and de-duplicated, plus README.md."""
    out: list[str] = []
    if plan.iterations:
        last = max(plan.iterations, key=lambda i: i.n)
        scope = hlib.field_text(last.body, "Scope") or ""
        for m in DOC_PATH_RE.finditer(scope):
            p = m.group(1).rstrip(".,;:")
            if p not in out and not p.endswith("/") and ".." not in p.split("/"):
                out.append(p)
    return out + ["README.md"]


@check("VC-012", ("full",))
def check_vc012(ctx: Context, f: Findings) -> None:
    """NON-GATING (spec D12): every doc file exists and avoids plan/artifact/iteration
    references and the word `spec`. Findings go to notes only, never to violations."""
    files = doc_files(ctx.plan)
    problems = 0
    for rel in files:
        p = ctx.repo / rel
        if not p.is_file():
            f.notes.append(f"VC-012: doc file missing: {rel}")
            problems += 1
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        hits = sorted({m.group(0).lower() for m in DOC_FORBIDDEN_RE.finditer(text)})
        if hits:
            f.notes.append(f"VC-012: {rel} contains plan/iteration references: {', '.join(hits)}")
            problems += 1
        if DOC_SPEC_RE.search(text):
            f.notes.append(f"VC-012: {rel} contains the word 'spec'")
            problems += 1
    if not problems:
        f.notes.append(f"VC-012: ok: {len(files)} doc file(s) checked")


@check("VC-014", ("downgrade",))
def check_vc014(ctx: Context, f: Findings) -> None:
    """S3: group A is announced (text block naming group A, pyproject.toml and
    sequential/downgrade) before the first member call; no worktree isolation;
    iteration 2's call returned before iteration 3's was issued, in separate
    messages; no merge commit on main; commits for 2 and 3 in ascending order."""
    calls = hlib.agent_calls(ctx.tr.events)
    attributed = attribute_agent_calls(ctx.plan, calls)
    c2, c3 = first_call(attributed.get(2, [])), first_call(attributed.get(3, []))
    if c2 is None and c3 is None:
        f.add("VC-014", "no Agent call is attributable to iteration 2 or 3")
    else:
        for n, c in ((2, c2), (3, c3)):
            if c is None:
                f.add("VC-014", f"no Agent call is attributable to iteration {n}")
        first = min(c.event_index for c in (c2, c3) if c is not None)
        block = find_text_block(hlib.text_blocks(ctx.tr.events),
                                GROUP_A_RE, re.compile(r"pyproject\.toml"), SEQUENTIAL_RE)
        if block is None:
            f.add("VC-014", "no assistant text block names group A, pyproject.toml and "
                  "sequential/downgrade together")
        elif block.event_index > first:
            f.add("VC-014", "the group A announcement comes after the first member Agent call")
        if c2 is not None and c3 is not None:
            res = hlib.tool_results(ctx.tr.events).get(c2.id)
            if c2.msg_index == c3.msg_index:
                f.add("VC-014", "the Agent calls for iterations 2 and 3 are in one assistant message")
            elif res is None or res.event_index > c3.event_index:
                f.add("VC-014", "iteration 3's Agent call was issued before iteration 2's returned")
    for c in calls:
        if c.input.get("isolation") == "worktree":
            f.add("VC-014", "an Agent call has isolation \"worktree\" (the group must be downgraded)")
            break
    n = merge_count(ctx.repo)
    if n:
        f.add("VC-014", f"main has {n} merge commit(s), expected 0")
    fp = first_parent_commits(ctx.repo)
    pos: dict[int, int] = {}
    for i, c in enumerate(fp):
        it = commit_iteration(ctx.repo, c)
        if it in (2, 3) and it not in pos:
            pos[it] = i
    if 2 not in pos or 3 not in pos:
        f.add("VC-014", "main lacks a commit for iteration " + " and ".join(
            str(n) for n in (2, 3) if n not in pos))
    elif pos[2] > pos[3]:
        f.add("VC-014", "the commit for iteration 3 precedes the commit for iteration 2")


@check("VC-015", ("failing-member",))
def check_vc015(ctx: Context, f: Findings) -> None:
    """S4: no merge on main; final text names iteration 2, price_cents and -1; each
    group's member calls were issued in one assistant message with isolation worktree.
    The unmerged branches are a note only (spec D3 does not require them)."""
    n = merge_count(ctx.repo)
    if n:
        f.add("VC-015", f"main has {n} merge commit(s), expected 0")
    text = final_text(hlib.text_blocks(ctx.tr.events))
    if not ITERATION_2_RE.search(text):
        f.add("VC-015", "the final assistant text does not name iteration 2")
    for needle in ("price_cents", "-1"):
        if needle not in text:
            f.add("VC-015", f"the final assistant text does not mention {needle}")
    groups = plan_groups(ctx.plan)
    if not groups:
        f.add("VC-015", "the plan has no parallel group")
    attributed = attribute_agent_calls(ctx.plan, hlib.agent_calls(ctx.tr.events))
    for g, ns in groups.items():
        members: list[hlib.ToolUse] = []
        for m in ns:
            mine = attributed.get(m, [])
            if not mine:
                f.add("VC-015", f"group {g}: no Agent call attributed to iteration {m}")
            members += mine
            if any(c.input.get("isolation") != "worktree" for c in mine):
                f.add("VC-015", f"group {g}: Agent call for iteration {m} lacks isolation \"worktree\"")
        if len({c.msg_index for c in members}) > 1:
            f.add("VC-015", f"group {g}: member Agent calls were not issued in one assistant message")
    unmerged = sorted(ln.strip().lstrip("*+ ").strip()
                      for ln in git(ctx.repo, "branch", "--no-merged", "main").splitlines() if ln.strip())
    f.notes.append("VC-015: unmerged branches: " + (", ".join(unmerged) if unmerged else "none"))


# --------------------------------------------------------------------------
# mode (a): check a run
# --------------------------------------------------------------------------

def refuse_repo(repo: Path, scenario: str) -> None:
    """VC-017: refuse the skills repository itself and, for full, an uncommitted plan."""
    if not repo.is_dir():
        raise HarnessError(f"repository not found: {repo}")
    top = git(repo, "rev-parse", "--show-toplevel").strip()
    if (Path(top) / "skills" / "write-spec-plan" / "SKILL.md").is_file():
        raise HarnessError(f"refusing to check the skills repository itself: {top}")
    if scenario == "full" and not git_ok(repo, "cat-file", "-e", f"main:{PLAN_IN_REPO}"):
        raise HarnessError(f"{PLAN_IN_REPO} is not committed on main in {repo}")


def run_checks(ctx: Context) -> Findings:
    f = Findings()
    for c in CHECKS:
        if ctx.scenario in c.scenarios:
            c.fn(ctx, f)
    return f


def mode_check(args: argparse.Namespace) -> int:
    if not args.repo or not args.plan or not args.transcript or args.run is None:
        raise HarnessError("usage: check_run.py <repo> <plan.md> --transcript F --run K --scenario S")
    if args.scenario not in RUN_SCENARIOS:
        raise HarnessError(f"--scenario must be one of {', '.join(RUN_SCENARIOS)}")
    repo = Path(args.repo)
    plan = hlib.parse_plan(args.plan)
    refuse_repo(repo, args.scenario)
    tr = hlib.load_transcript(args.transcript)
    ctx = Context(repo, plan, tr, args.scenario, args.run)
    n = len(hlib.agent_calls(tr.events))
    f = run_checks(ctx)
    f.notes.append(f"subagents: {n}")
    f.notes.append(NOTE_SKILL_SOURCE_UNIMPLEMENTED if args.check_skill_source else NOTE_SKILL_SOURCE)
    denials = hlib.permission_denials(tr.events)
    if denials:
        f.notes.append(f"permission_denials: {json.dumps(denials, sort_keys=True)}")
    if tr.result is None:
        f.notes.append("transcript has no result event")
    if git(repo, "status", "--porcelain").strip():
        f.notes.append("working tree is dirty")
    if args.result_out:
        hlib.write_result(args.result_out, args.scenario, args.run, f.violations, f.notes, tr.model)
    print(f"subagents: {n}")
    for line in f.lines():
        print(line)
    for note in f.notes:
        if not note.startswith("subagents: "):
            print(f"note: {note}")
    print("check_run: " + (f"FAIL {' '.join(f.violations)}" if f.violations else "OK"))
    return hlib.exit_code(f.violations)


# --------------------------------------------------------------------------
# mode (b): --summary
# --------------------------------------------------------------------------

def mode_summary(args: argparse.Namespace) -> int:
    if args.scenario not in ALL_SCENARIOS:
        raise HarnessError(f"--scenario must be one of {', '.join(ALL_SCENARIOS)}")
    d = Path(args.summary)
    if not d.is_dir():
        raise HarnessError(f"results directory not found: {d}")
    files = sorted(d.glob(f"{args.scenario}-*.json"))
    results = []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise HarnessError(f"unreadable result file {p}: {e}")
        if not isinstance(data, dict) or not isinstance(data.get("passed"), bool) \
                or not isinstance(data.get("violations"), list):
            raise HarnessError(f"result file {p} does not have the BR-004 shape")
        results.append(data)
    union: list[str] = []
    for r in results:
        for v in r["violations"]:
            if v not in union:
                union.append(v)
    passed = sum(1 for r in results if r["passed"])
    print(f"summary {args.scenario}: {len(results)} files, {passed} passed")
    print("violations: " + (" ".join(union) if union else "none"))
    if len(results) < 3:
        print(f"summary {args.scenario}: fewer than 3 result files", file=sys.stderr)
        return hlib.EXIT_USAGE
    return hlib.EXIT_OK if passed >= 2 else hlib.EXIT_FAIL


# --------------------------------------------------------------------------
# mode (c): --mark-failed
# --------------------------------------------------------------------------

def mode_mark_failed(args: argparse.Namespace) -> int:
    if args.scenario not in ALL_SCENARIOS:
        raise HarnessError(f"--scenario must be one of {', '.join(ALL_SCENARIOS)}")
    if args.run is None or not args.result_out:
        raise HarnessError("--mark-failed needs --scenario, --run and --result-out")
    hlib.write_result(args.result_out, args.scenario, args.run, [args.violation],
                      [f"marked failed: {args.violation}"], "")
    print(f"marked {args.scenario} run {args.run} failed: {args.violation}")
    return hlib.EXIT_OK


# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="check_run.py", description=__doc__.splitlines()[0])
    ap.add_argument("repo", nargs="?")
    ap.add_argument("plan", nargs="?")
    ap.add_argument("--transcript")
    ap.add_argument("--run", type=int)
    ap.add_argument("--scenario")
    ap.add_argument("--result-out")
    ap.add_argument("--summary", metavar="RESULTS_DIR")
    ap.add_argument("--mark-failed", action="store_true")
    ap.add_argument("--violation", choices=("skipped", "error"), default="skipped")
    ap.add_argument("--check-skill-source", action="store_true",
                    help="wired in, off by default; completed in Iteration 9")
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.summary and args.mark_failed:
            raise HarnessError("--summary and --mark-failed are exclusive")
        if args.summary:
            return mode_summary(args)
        if args.mark_failed:
            return mode_mark_failed(args)
        return mode_check(args)
    except HarnessError as e:
        print(f"check_run.py: error: {e}", file=sys.stderr)
        return hlib.EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
