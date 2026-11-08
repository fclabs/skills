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
import subprocess
import sys
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
