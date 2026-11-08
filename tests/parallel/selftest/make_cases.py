#!/usr/bin/env python3
"""Build the golden selftest cases (spec D7): make_cases.py <outdir>.

Each case is a directory <outdir>/<case>/ holding expect.json plus whatever
inputs the checker needs (plan.md, and for later iterations repo/ and
transcript.jsonl).  expect.json:
  {"checker": "check_plan.py"|"check_run.py", "args": [...], "exit": 0|1|2,
   "violations": [...]}                       # exact set of violation ids
optional keys: "model", "scenario", "run" (expected result-file fields),
"notes_contain" ([str], exact note strings), "passed" (default: exit == 0),
"output_contains" ([str], substrings of stdout+stderr, checked before the
exit-2 early return), "append_result_out" (default true; false for modes whose
args carry --result-out themselves or take none), "result_file" (result file
to validate, default result.json; when append_result_out is false and no
result_file is given, only the violation ids are looked for in stdout).
`args` run with the case directory as cwd; run.sh appends --result-out.
A Case may carry `build(casedir)`, called after its files are written (used
to create synthetic git repos).

HOW TO ADD A CASE: write one function `case_<name>()` returning a Case(files,
expect).  The case directory name is <name> with underscores turned into
hyphens.  Use the plan builder (It, render) for synthetic tinyshop plans; the
token @DIR@ in any file text becomes the case directory's absolute path.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CHECK_PLAN = "check_plan.py"
CHECK_RUN = "check_run.py"
TEST_MODEL = "claude-test-model"


@dataclass
class Case:
    files: dict[str, str]
    expect: dict
    build: Callable[[Path], None] | None = None


# ---------------------------------------------------------------- plan builder

@dataclass
class It:
    n: int
    name: str
    depends: list[int]
    group: str | None
    touches: list[str]
    fgroup: str | None = "auto"        # raw text of the Parallel group field; "auto" derives it
    fdepends: str | None = None        # raw text of the Depends on field; None derives it
    tdepends: str | None = None        # raw text of the table Depends cell
    proto: str = "full"                # full | no-decisions | no-path


def _slug(it: It) -> str:
    return it.name.lower().replace(" ", "-")


def _record(it: It) -> str:
    return f"plan-artifacts/iterations/{it.n:02d}-{_slug(it)}.md"


def _fmt_touches(it: It, style: str) -> str:
    paths = list(it.touches)
    if it.group is not None and it.proto != "no-path":
        paths.append(_record(it))
    if style == "abs":
        return ", ".join(f"`@DIR@/{p}`" for p in paths)
    if style == "rel":
        return "\n" + "\n".join(f"- `{p}`" for p in paths)
    if style == "plain":      # no backticks, trailing parentheticals
        return ", ".join(f"{p} (new)" for p in paths) + " (artifact files implied)"
    if style == "colon":
        return ", ".join(f"`{p}`" for p in paths)
    raise ValueError(style)


def render(its: list[It], style: str = "abs", header: list[tuple[str, str]] | None = None,
           drop_rows: tuple[int, ...] = ()) -> str:
    header = header or [("Iteration", "n"), ("Depends on", "d"), ("Parallel group", "g"),
                        ("Touches (summary)", "t")]
    out = ["# Implementation Plan: Golden", "",
           "**Spec**: @DIR@/specs/tinyshop-spec.md", "",
           "## Artifact Protocol", "", "Artifact directory: @DIR@/plan-artifacts/", "",
           "## Execution Order", "",
           "| " + " | ".join(h for h, _ in header) + " |",
           "|" + "|".join("---" for _ in header) + "|"]
    for it in its:
        if it.n in drop_rows:
            continue
        cell = {"n": str(it.n),
                "d": it.tdepends if it.tdepends is not None else (", ".join(map(str, it.depends)) or "—"),
                "g": it.group or "—",
                "t": ", ".join(f"`{p}`" for p in it.touches)}
        out.append("| " + " | ".join(cell[k] for _, k in header) + " |")
    out.append("")
    for it in its:
        if it.fgroup == "auto":
            fg = f"`{it.group}` — runs concurrently with its group. Safe because disjoint." if it.group else "`none`"
        else:
            fg = it.fgroup or "`none`"
        fd = it.fdepends if it.fdepends is not None else (", ".join(map(str, it.depends)) or "none")
        lab = "**Touches:**" if style == "colon" else "**Touches**:"
        scope = ["- Do the work."]
        if it.group is not None:
            rec = "" if it.proto == "no-path" else f"write only `{_record(it)}`; "
            dec = "" if it.proto == "no-decisions" else " and **Proposed decisions**"
            scope.append(f"- Artifacts (parallel-group member): {rec}include **Proposed CONTEXT.md changes**{dec}.")
        out += [f"## Iteration {it.n}: {it.name.title()}", "",
                f"**Goal**: Goal sentence {it.n}.", "",
                f"**Depends on**: {fd}", "",
                f"**Parallel group**: {fg}", "",
                f"{lab} {_fmt_touches(it, style)}".rstrip(), "",
                "**Scope**:", *scope, "",
                "**Success criteria**:", "- VC: `python -c pass` exits 0.", "", "---", ""]
    out += ["## Final Verification", "", "- Run everything.", ""]
    return "\n".join(out)


def base7() -> list[It]:
    return [
        It(1, "scaffold", [], None, ["pyproject.toml", "tinyshop/__init__.py", "tests/__init__.py"]),
        It(2, "pricing", [1], "A", ["tinyshop/pricing.py", "tests/test_pricing.py"]),
        It(3, "inventory", [1], "A", ["tinyshop/inventory.py", "tests/test_inventory.py"]),
        It(4, "shipping", [1], "A", ["tinyshop/shipping.py", "tests/test_shipping.py"]),
        It(5, "cli", [2, 3, 4], None, ["tinyshop/cli.py", "tests/test_cli.py"]),
        It(6, "orders", [2, 3], None, ["tinyshop/orders.py", "tests/test_orders.py"]),
        It(7, "docs", [5, 6], None, ["docs/overview.md", "docs/usage.md", "README.md"]),
    ]


def base5() -> list[It]:
    return [
        It(1, "scaffold", [], None, ["pyproject.toml", "tinyshop/__init__.py"]),
        It(2, "pricing", [1], "A", ["tinyshop/pricing.py"]),
        It(3, "inventory", [1], "A", ["tinyshop/inventory.py"]),
        It(4, "shipping", [1], "A", ["tinyshop/shipping.py"]),
        It(5, "final", [2, 3, 4], None, ["tinyshop/cli.py", "tinyshop/orders.py", "docs/", "README.md"]),
    ]


def _plan_case(plan: str, exit_: int, violations: list[str], args: list[str] | None = None,
               extra: dict | None = None, files: dict[str, str] | None = None) -> Case:
    expect = {"checker": CHECK_PLAN, "args": args or ["plan.md", "--run", "1"],
              "exit": exit_, "violations": violations}
    expect.update(extra or {})
    return Case({"plan.md": plan, **(files or {})}, expect)


def _good(its: list[It], **kw) -> Case:
    return _plan_case(render(its, **kw), 0, [])


def _bad(its: list[It], vc: str, **kw) -> Case:
    return _plan_case(render(its, **kw), 1, [vc])


def _set(its: list[It], n: int, **kw) -> list[It]:
    for it in its:
        if it.n == n:
            for k, v in kw.items():
                setattr(it, k, v)
    return its


# ------------------------------------------------------------------ good cases

def case_plan_good_7_iterations() -> Case:
    return _good(base7())


def case_plan_good_5_iterations() -> Case:
    # Minimal valid plan. VC-004 (three module iterations, one group) and VC-006
    # (first and last ungrouped) make 3 iterations impossible; user-approved
    # replacement of the spec's "3 iterations" (see iteration record).
    return _good(base5())


def case_plan_good_relative_touches_bullets() -> Case:
    return _good(base7(), style="rel")


def case_plan_good_trailing_parenthetical() -> Case:
    return _good(base7(), style="plain")


def case_plan_good_colon_inside_bold() -> Case:
    return _good(base7(), style="colon")


def case_plan_good_bare_integer_depends() -> Case:
    its = base7()
    _set(its, 1, fdepends="—", tdepends="-")
    for n in (2, 3, 4):
        _set(its, n, fdepends="1", tdepends="1")
    _set(its, 5, fdepends="2,3,4", tdepends="2,3,4")
    return _good(its)


def case_plan_good_tax_discount_group() -> Case:
    # An extra group B after orders (rates.toml edit isolated in its own ungrouped iteration).
    its = base7()
    docs = its.pop()
    its += [
        It(7, "rates", [1], None, ["tinyshop/rates.toml"]),
        It(8, "tax", [7], "B", ["tinyshop/tax.py"]),
        It(9, "discount", [7], "B", ["tinyshop/discount.py"]),
        It(10, "docs", [5, 6, 8, 9], None, docs.touches),
    ]
    return _good(its)


def case_plan_good_with_transcript() -> Case:
    init = {"type": "system", "subtype": "init", "model": "claude-test-model", "skills": [], "plugins": []}
    return _plan_case(render(base7()), 0, [], args=["plan.md", "--run", "2", "--transcript", "transcript.jsonl"],
                      extra={"model": "claude-test-model", "notes_contain": ["skill-source check skipped"]},
                      files={"transcript.jsonl": json.dumps(init) + "\n"})


# ------------------------------------------------------------------- bad cases

def case_plan_bad_vc003_row_count() -> Case:
    return _bad(base7(), "VC-003", drop_rows=(7,))


def case_plan_bad_vc003_header_column() -> Case:
    hdr = [("Iteration", "n"), ("Depends on", "d"), ("Touches (summary)", "t")]
    return _bad(base7(), "VC-003", header=hdr)


def case_plan_bad_vc003_no_table() -> Case:
    text = render(base7())
    start = text.index("## Execution Order")
    end = text.index("## Iteration 1")
    return _plan_case(text[:start] + text[end:], 1, ["VC-003"])


def case_plan_bad_vc004_group_differs() -> Case:
    its = _set(base7(), 4, group="B", fgroup="auto")
    return _bad(its, "VC-004")


def case_plan_bad_vc004_not_adjacent() -> Case:
    its = [
        It(1, "scaffold", [], None, ["pyproject.toml"]),
        It(2, "pricing", [1], "A", ["tinyshop/pricing.py"]),
        It(3, "inventory", [1], "A", ["tinyshop/inventory.py"]),
        It(4, "config", [1], None, ["tinyshop/config.py"]),
        It(5, "shipping", [1], "A", ["tinyshop/shipping.py"]),
        It(6, "cli", [2, 3, 5], None, ["tinyshop/cli.py"]),
        It(7, "orders", [2, 3], None, ["tinyshop/orders.py"]),
        It(8, "docs", [6, 7], None, ["docs/"]),
    ]
    return _bad(its, "VC-004")


def case_plan_bad_vc004_module_split() -> Case:
    its = base7()
    _set(its, 5, touches=["tinyshop/cli.py", "tinyshop/shipping.py"])
    return _bad(its, "VC-004")


def case_plan_bad_vc005_shared_resource_grouped() -> Case:
    its = base7()
    _set(its, 2, touches=["tinyshop/pricing.py", "tinyshop/rates.toml"])
    return _bad(its, "VC-005")


def case_plan_bad_vc005_own_group_dependency() -> Case:
    its = base7()
    docs = its.pop()
    its += [
        It(7, "tax", [1], "B", ["tinyshop/tax.py"]),
        It(8, "discount", [7], "B", ["tinyshop/discount.py"]),
        It(9, "docs", [5, 6, 8], None, docs.touches),
    ]
    return _bad(its, "VC-005")


def case_plan_bad_vc005_group_field_disagrees() -> Case:
    its = _set(base7(), 3, fgroup="`B` — runs concurrently. Safe because disjoint.")
    return _bad(its, "VC-005")


def case_plan_bad_vc005_depends_field_disagrees() -> Case:
    its = _set(base7(), 5, fdepends="2, 3")
    return _bad(its, "VC-005")


def case_plan_bad_vc006_last_grouped() -> Case:
    its = base7()
    # depends only on 1 so its transitive deps stay out of group A (VC-005 not triggered)
    _set(its, 7, group="A", touches=["README.md"], depends=[1], fgroup="auto")
    return _bad(its, "VC-006")


def case_plan_bad_vc006_missing_decisions_string() -> Case:
    its = _set(base7(), 3, proto="no-decisions")
    return _bad(its, "VC-006")


def case_plan_bad_vc006_missing_record_path() -> Case:
    its = _set(base7(), 4, proto="no-path")
    return _bad(its, "VC-006")


def case_plan_bad_vc007_overlap() -> Case:
    # Hand-built overlapping plan (the bad-group template is not a tinyshop plan); also VC-016 plan half.
    its = base7()
    _set(its, 2, touches=["tinyshop/pricing.py", "tinyshop/util.py"])
    _set(its, 3, touches=["tinyshop/inventory.py", "tinyshop/util.py"])
    return _bad(its, "VC-007")


def case_plan_bad_vc007_glob_prefix_overlap() -> Case:
    its = base7()
    _set(its, 2, touches=["tinyshop/pricing.py", "tinyshop/helpers/**"])
    _set(its, 4, touches=["tinyshop/shipping.py", "tinyshop/helpers/a.py"])
    return _bad(its, "VC-007")


def case_plan_bad_vc025_orders_missing_dep() -> Case:
    return _bad(_set(base7(), 6, depends=[2]), "VC-025")


def case_plan_bad_vc025_cli_missing_dep() -> Case:
    return _bad(_set(base7(), 5, depends=[2, 3]), "VC-025")


def case_plan_bad_vc025_module_extra_dep() -> Case:
    its = base7()
    its.insert(1, It(2, "config", [1], None, ["tinyshop/config.py"]))
    for it in its[2:]:
        it.n += 1
        it.depends = [d + 1 if d >= 2 else d for d in it.depends]
    for n in (3, 4, 5):
        _set(its, n, depends=[1, 2])
    return _bad(its, "VC-025")


# ---------------------------------------------------------- usage-error cases

def case_plan_usage_nonexistent_path() -> Case:
    return Case({}, {"checker": CHECK_PLAN, "args": ["does-not-exist.md", "--run", "1"],
                     "exit": 2, "violations": []})


def case_plan_usage_empty_file() -> Case:
    return _plan_case("", 2, [])


def case_plan_usage_unparseable_transcript() -> Case:
    return _plan_case(render(base7()), 2, [], args=["plan.md", "--run", "1", "--transcript", "transcript.jsonl"],
                      files={"transcript.jsonl": "not json\n"})


def case_plan_usage_missing_run() -> Case:
    return _plan_case(render(base7()), 2, [], args=["plan.md"])


# ------------------------------------------------- transcript and repo builders

def ev_init(model: str = TEST_MODEL) -> dict:
    return {"type": "system", "subtype": "init", "model": model, "skills": [], "plugins": []}


def ev_assistant(mid: str, block: dict, parent: str | None = None) -> dict:
    """One stream-json assistant event carrying one content block."""
    return {"type": "assistant", "parent_tool_use_id": parent,
            "message": {"id": mid, "role": "assistant", "content": [block]}}


def ev_text(mid: str, text: str, parent: str | None = None) -> dict:
    return ev_assistant(mid, {"type": "text", "text": text}, parent)


def blk_agent(tuid: str, isolation: str | None = None, name: str = "Agent", prompt: str = "work") -> dict:
    inp = {"description": "member", "prompt": prompt, "subagent_type": "general-purpose"}
    if isolation:
        inp["isolation"] = isolation
    return {"type": "tool_use", "id": tuid, "name": name, "input": inp}


def ev_tool_result(tuid: str, text: str = "ok", parent: str | None = None) -> dict:
    return {"type": "user", "parent_tool_use_id": parent,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tuid, "content": text}]}}


def ev_result(denials: list | tuple = ()) -> dict:
    return {"type": "result", "subtype": "success", "is_error": False,
            "permission_denials": list(denials)}


def build_transcript(*, agents: int = 0, per_message: int = 1, sub_agents: int = 0,
                     isolation: str | None = None, tool_name: str = "Agent",
                     texts: tuple[str, ...] = (), final_text: str = "Done.",
                     denials: tuple = (), model: str = TEST_MODEL, init: bool = True,
                     assistant: bool = True, result: bool = True) -> str:
    """Synthetic stream-json transcript (JSONL text).

    agents: orchestrator-level Agent/Task calls (tool_name), `per_message` per
    assistant message; each is answered by a tool_result.  sub_agents: Agent
    calls emitted by a subagent (parent_tool_use_id set).  texts: orchestrator
    text messages before the calls.  assistant=False drops every assistant
    event (shape error).
    """
    ev: list[dict] = []
    if init:
        ev.append(ev_init(model))
    if assistant:
        for i, t in enumerate(texts):
            ev.append(ev_text(f"msg_t{i}", t))
        ids = [f"toolu_{i}" for i in range(agents)]
        for m, start in enumerate(range(0, agents, max(per_message, 1))):
            chunk = ids[start:start + max(per_message, 1)]
            for tuid in chunk:
                ev.append(ev_assistant(f"msg_a{m}", blk_agent(tuid, isolation, tool_name)))
            for tuid in chunk:
                ev.append(ev_tool_result(tuid))
        for j in range(sub_agents):
            ev.append(ev_assistant(f"msg_s{j}", blk_agent(f"toolu_sub{j}", None, tool_name), parent="toolu_0"))
        ev.append(ev_text("msg_final", final_text))
    if result:
        ev.append(ev_result(denials))
    return "".join(json.dumps(e) + "\n" for e in ev)


def _git(cwd: Path, *args: str) -> None:
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    subprocess.run(["git", "-C", str(cwd), "-c", "user.name=harness",
                    "-c", "user.email=harness@example.invalid", "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True, env=env)


def build_repo(path: Path, *, plan_text: str | None = None, commit_plan: bool = True,
               skills_layout: bool = False, dirty: bool = False) -> None:
    """Synthetic scratch repo on `main`: one commit, optionally with the plan at
    specs/tinyshop-plan.md (committed or left untracked), a skills-repository
    layout (skills/write-spec-plan/SKILL.md), or an untracked file (dirty)."""
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    (path / "README.md").write_text("synthetic\n", encoding="utf-8")
    if skills_layout:
        (path / "skills" / "write-spec-plan").mkdir(parents=True)
        (path / "skills" / "write-spec-plan" / "SKILL.md").write_text("skill\n", encoding="utf-8")
    if plan_text is not None:
        (path / "specs").mkdir()
        (path / "specs" / "tinyshop-plan.md").write_text(plan_text, encoding="utf-8")
    _git(path, "add", "-A")
    if plan_text is not None and not commit_plan:
        _git(path, "reset", "-q", "--", "specs")
    _git(path, "commit", "-q", "-m", "Initial")
    if dirty:
        (path / "stray.txt").write_text("x\n", encoding="utf-8")


# ------------------------------------------------------------ check_run cases

def _run_args(scenario: str, repo: str = "repo", plan: str = "plan.md",
              transcript: str = "transcript.jsonl", run: int = 1) -> list[str]:
    return [repo, plan, "--transcript", transcript, "--run", str(run), "--scenario", scenario]


def _run_case(scenario: str, transcript: str | None, exit_: int, violations: list[str], *,
              repo_kw: dict | None = None, extra: dict | None = None,
              args: list[str] | None = None, no_repo: bool = False,
              no_plan: bool = False) -> Case:
    plan = render(base7())
    files: dict[str, str] = {}
    if not no_plan:
        files["plan.md"] = plan
    if transcript is not None:
        files["transcript.jsonl"] = transcript
    kw = dict(repo_kw or {})
    kw.setdefault("plan_text", plan.replace("@DIR@", "/scratch"))
    expect = {"checker": CHECK_RUN, "args": args or _run_args(scenario), "exit": exit_,
              "violations": violations}
    expect.update(extra or {})
    return Case(files, expect, None if no_repo else (lambda d, kw=kw: build_repo(d / "repo", **kw)))


# refusals (VC-017) and usage errors (VC-016 run half)

def case_run_refuse_skills_repo() -> Case:
    return _run_case("full", build_transcript(), 2, [], repo_kw={"skills_layout": True},
                     extra={"output_contains": ["refusing to check the skills repository"]})


def case_run_refuse_skills_repo_downgrade() -> Case:
    return _run_case("downgrade", build_transcript(), 2, [], repo_kw={"skills_layout": True, "plan_text": None})


def case_run_refuse_uncommitted_plan() -> Case:
    return _run_case("full", build_transcript(), 2, [], repo_kw={"commit_plan": False},
                     extra={"output_contains": ["is not committed on main"]})


def case_run_missing_plan_in_repo_ok_for_downgrade() -> Case:
    return _run_case("downgrade", build_transcript(), 0, [], repo_kw={"plan_text": None})


def case_run_usage_missing_transcript() -> Case:
    return _run_case("downgrade", None, 2, [], extra={"output_contains": ["transcript not found"]})


def case_run_usage_unparseable_transcript() -> Case:
    return _run_case("downgrade", "not json\n", 2, [])


def case_run_usage_no_init_event() -> Case:
    return _run_case("downgrade", build_transcript(init=False), 2, [],
                     extra={"output_contains": ["no system init event"]})


def case_run_usage_no_assistant_events() -> Case:
    return _run_case("downgrade", build_transcript(assistant=False), 2, [],
                     extra={"output_contains": ["no assistant events"]})


def case_run_usage_nonexistent_repo() -> Case:
    return _run_case("downgrade", build_transcript(), 2, [], no_repo=True,
                     extra={"output_contains": ["repository not found"]})


def case_run_usage_missing_plan_file() -> Case:
    return _run_case("downgrade", build_transcript(), 2, [], no_plan=True)


def case_run_usage_plan_scenario_rejected() -> Case:
    return _run_case("downgrade", build_transcript(), 2, [], args=_run_args("plan"))


def case_run_usage_no_scenario() -> Case:
    return _run_case("downgrade", build_transcript(), 2, [],
                     args=["repo", "plan.md", "--transcript", "transcript.jsonl", "--run", "1"])


# cost check (VC-020 / NFR-001): exactly at the limit passes, one over fails

def _nfr(scenario: str, n: int, bad: bool, **kw) -> Case:
    extra = {"output_contains": [f"subagents: {n}"]}
    if scenario == "full":      # a good S2 history plus unattributed extra Agent calls (7 calls are the plan's)
        return _s2_case(base7(), 1 if bad else 0, ["NFR-001"] if bad else [],
                        tr={"extra": n - 7, "extra_per_message": kw.get("per_message", 1)}, extra=extra)
    return _run_case(scenario, build_transcript(agents=n, **kw), 1 if bad else 0,
                     ["NFR-001"] if bad else [], extra=extra)


def case_run_nfr001_full_15_ok() -> Case:
    return _nfr("full", 15, False)


def case_run_nfr001_full_16_fails() -> Case:
    return _nfr("full", 16, True)


def case_run_nfr001_downgrade_6_ok() -> Case:
    return _nfr("downgrade", 6, False)


def case_run_nfr001_downgrade_7_fails() -> Case:
    return _nfr("downgrade", 7, True)


def case_run_nfr001_failing_member_6_ok() -> Case:
    return _nfr("failing-member", 6, False)


def case_run_nfr001_failing_member_7_fails() -> Case:
    return _nfr("failing-member", 7, True)


def case_run_nfr001_counts_calls_not_messages() -> Case:
    return _nfr("full", 16, True, per_message=4)


def case_run_nfr001_task_tool_name_counts() -> Case:
    return _nfr("downgrade", 7, True, tool_name="Task")


def case_run_nfr001_subagent_calls_not_counted() -> Case:
    return _s2_case(base7(), 0, [], tr={"extra": 8, "sub_agents": 5},
                    extra={"output_contains": ["subagents: 15"]})


def case_run_nfr001_subagent_calls_not_counted_other() -> Case:
    return _run_case("failing-member", build_transcript(agents=6, sub_agents=3), 0, [],
                     extra={"output_contains": ["subagents: 6"]})


# result file content (BR-004): model, notes, permission_denials

def case_run_good_result_notes() -> Case:
    denial = {"tool_name": "Bash", "tool_use_id": "toolu_x"}
    return _run_case("downgrade", build_transcript(agents=2, denials=(denial,), model="claude-other"), 0, [],
                     repo_kw={"dirty": True},
                     extra={"model": "claude-other", "scenario": "downgrade", "run": 1,
                            "notes_contain": ["subagents: 2", "skill-source check skipped",
                                              "working tree is dirty",
                                              'permission_denials: [{"tool_name": "Bash", "tool_use_id": "toolu_x"}]']})


def case_run_good_result_run_number() -> Case:
    return _run_case("failing-member", build_transcript(agents=3), 0, [],
                     args=_run_args("failing-member", run=3),
                     extra={"scenario": "failing-member", "run": 3, "model": TEST_MODEL})


def case_run_note_no_result_event() -> Case:
    return _run_case("downgrade", build_transcript(result=False), 0, [],
                     extra={"notes_contain": ["transcript has no result event"]})


# --summary (BR-004)

def _res(scenario: str, k: int, passed: bool, violations: list[str] | None = None) -> dict[str, str]:
    data = {"scenario": scenario, "run": k, "passed": passed, "violations": violations or [],
            "notes": [], "model": TEST_MODEL}
    return {f"results/{scenario}-{k}.json": json.dumps(data)}


def _summary_case(scenario: str, files: dict[str, str], exit_: int, violations: list[str],
                  output: list[str], args: list[str] | None = None) -> Case:
    return Case(files, {"checker": CHECK_RUN, "args": args or ["--summary", "results", "--scenario", scenario],
                        "exit": exit_, "violations": violations, "append_result_out": False,
                        "output_contains": output})


def case_summary_true_true_false_exits_0() -> Case:
    f = {**_res("full", 1, True), **_res("full", 2, True), **_res("full", 3, False, ["VC-009"])}
    return _summary_case("full", f, 0, [], ["violations: VC-009"])


def case_summary_true_false_false_exits_1() -> Case:
    f = {**_res("downgrade", 1, True), **_res("downgrade", 2, False, ["VC-014", "NFR-001"]),
         **_res("downgrade", 3, False, ["VC-014", "error"])}
    return _summary_case("downgrade", f, 1, ["VC-014", "NFR-001", "error"],
                         ["violations: VC-014 NFR-001 error"])


def case_summary_two_files_exits_2() -> Case:
    f = {**_res("failing-member", 1, True), **_res("failing-member", 2, False, ["VC-015"])}
    return _summary_case("failing-member", f, 2, [], ["violations: VC-015", "fewer than 3"])


def case_summary_all_pass_prints_none() -> Case:
    f = {**_res("plan", 1, True), **_res("plan", 2, True), **_res("plan", 3, True)}
    return _summary_case("plan", f, 0, [], ["violations: none"])


def case_summary_ignores_other_scenarios() -> Case:
    f = {**_res("full", 1, False, ["VC-008"]), **_res("full", 2, True), **_res("full", 3, True),
         **_res("downgrade", 1, False, ["VC-014"]), **_res("plan", 1, False, ["VC-003"])}
    return _summary_case("full", f, 0, [], ["violations: VC-008", "3 files, 2 passed"])


def case_summary_missing_dir_exits_2() -> Case:
    return _summary_case("full", {}, 2, [], ["results directory not found"],
                         args=["--summary", "nope", "--scenario", "full"])


def case_summary_bad_result_file_exits_2() -> Case:
    f = {**_res("full", 1, True), **_res("full", 2, True), "results/full-3.json": "[]"}
    return _summary_case("full", f, 2, [], ["BR-004 shape"])


# --mark-failed (D8, D10)

def _mark_case(scenario: str, run: int, violation: str | None, **extra) -> Case:
    args = ["--mark-failed", "--scenario", scenario, "--run", str(run), "--result-out", "result.json"]
    if violation:
        args += ["--violation", violation]
    expect = {"checker": CHECK_RUN, "args": args, "exit": 0, "passed": False,
              "violations": [violation or "skipped"], "append_result_out": False,
              "result_file": "result.json", "scenario": scenario, "run": run, "model": ""}
    expect.update(extra)
    return Case({}, expect)


def case_mark_failed_full_run_2_skipped() -> Case:
    return _mark_case("full", 2, None)


def case_mark_failed_error_violation() -> Case:
    return _mark_case("downgrade", 1, "error")


def case_mark_failed_plan_scenario() -> Case:
    return _mark_case("plan", 3, "error")


def case_mark_failed_failing_member() -> Case:
    return _mark_case("failing-member", 2, "skipped")


def case_mark_failed_needs_result_out() -> Case:
    return Case({}, {"checker": CHECK_RUN, "args": ["--mark-failed", "--scenario", "full", "--run", "1"],
                     "exit": 2, "violations": [], "append_result_out": False})


def case_mark_failed_rejects_other_violation() -> Case:
    return Case({}, {"checker": CHECK_RUN,
                     "args": ["--mark-failed", "--scenario", "full", "--run", "1", "--result-out", "r.json",
                              "--violation", "VC-008"],
                     "exit": 2, "violations": [], "append_result_out": False})


def case_mark_failed_rejects_unknown_scenario() -> Case:
    return Case({}, {"checker": CHECK_RUN,
                     "args": ["--mark-failed", "--scenario", "smoke", "--run", "1", "--result-out", "r.json"],
                     "exit": 2, "violations": [], "append_result_out": False})


# ------------------------------------------------- S2 builders (VC-008..011, VC-013)

ART = "specs/tinyshop-plan-artifacts"
SMOKE_TEST = ("import unittest\nimport tinyshop\n\n\nclass SmokeTest(unittest.TestCase):\n"
              "    def test_import(self):\n        self.assertTrue(tinyshop)\n")
FINAL_STUBS = {
    "tinyshop/tax.py": "import tomllib\nfrom pathlib import Path\n\n\ndef tax_cents(amount):\n"
                       "    rates = tomllib.loads((Path(__file__).parent / 'rates.toml').read_text())\n"
                       "    return amount * rates['tax_bp'] // 10000\n",
    "tinyshop/discount.py": "import tomllib\nfrom pathlib import Path\n\n\ndef discount_cents(amount):\n"
                            "    rates = tomllib.loads((Path(__file__).parent / 'rates.toml').read_text())\n"
                            "    return amount * rates['discount_bp'] // 10000\n",
    "tinyshop/rates.toml": "tax_bp = 800\ndiscount_bp = 1000\n",
}
CONTENT = {"tinyshop/pricing.py": "def price_cents(items):\n    return sum(u * q for u, q in items)\n"}


def _commit(path: Path, files: dict[str, str], msg: str) -> None:
    for rel, text in files.items():
        p = path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", msg)


def _s2_record(it: It) -> str:
    return f"{ART}/iterations/{it.n:02d}-{_slug(it)}.md"


def _touch_files(it: It) -> dict[str, str]:
    out = {}
    for t in it.touches:
        if t.endswith("**"):
            continue
        rel = t + "index.md" if t.endswith("/") else t
        out[rel] = CONTENT.get(rel, f"# stub {rel}\n")
    return out


def build_s2_repo(path: Path, its: list[It], plan_text: str, *, defect: str | None = None,
                  sep: str = "–", decisions: str | None = None,
                  final_files: dict[str, str] | None = None) -> None:
    """Synthetic S2 scratch repo with a realistic history for plan `its` (shell-out to git).

    "Add plan" commit; ungrouped iterations are one commit `Iteration N: name`
    (record, CONTEXT.md, DECISIONS.md); a group is member branches off one commit,
    `git merge --no-ff` as `Merge iteration N: name` in ascending order, then
    `Reconcile artifacts for iterations N<sep>M` touching CONTEXT.md.  The final
    (ungrouped) iteration also writes the tinyshop stubs for VC-013.
    defect: diverged-base | merge-order | extra-commit | no-reconcile-context |
    no-reconcile | worktree-left | late-unmapped | member-context | member-outside |
    missing-record.  decisions overrides DECISIONS.md in the final commit;
    final_files overrides/adds files there.
    """
    path.mkdir(parents=True, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    ctx_lines: list[str] = []
    entries: list[tuple[int, int]] = []     # (decision id, iteration)

    def ctx_file() -> dict[str, str]:
        return {f"{ART}/CONTEXT.md": "# CONTEXT\n" + "".join(ctx_lines)}

    def dec_file() -> dict[str, str]:
        body = "".join(f"## D-{i:03d}: decision {i}  (Iteration {n})\nbody\n\n" for i, n in entries)
        return {f"{ART}/DECISIONS.md": "# DECISIONS\n\n" + body}

    _commit(path, {"README.md": "synthetic\n", "specs/tinyshop-plan.md": plan_text, **ctx_file(), **dec_file()},
            "Add plan")
    i = 0
    while i < len(its):
        it = its[i]
        if it.group is None:
            ctx_lines.append(f"- iteration {it.n}\n")
            entries.append((len(entries) + 1, it.n))
            files = {**_touch_files(it), _s2_record(it): f"# Iteration {it.n}\n", **ctx_file(), **dec_file()}
            if it.n == 1:
                files.update({"tests/__init__.py": "", "tests/test_smoke.py": SMOKE_TEST})
            if i == len(its) - 1:
                files.update(FINAL_STUBS)
                if decisions is not None:
                    files[f"{ART}/DECISIONS.md"] = decisions
                files.update(final_files or {})
            _commit(path, files, f"Iteration {it.n}: {it.name}")
            if i == len(its) - 1 and defect == "late-unmapped":
                _commit(path, {"notes.txt": "late\n"}, "Fix typo")
            i += 1
            continue
        j = i
        while j < len(its) and its[j].group == it.group:
            j += 1
        members = its[i:j]
        for k, m in enumerate(members):
            if defect == "diverged-base" and k == 1:
                _commit(path, {"notes.txt": "interim\n"}, "Interim housekeeping")
            _git(path, "checkout", "-q", "-b", f"member-{m.n}", "main")
            files = _touch_files(m)
            if not (defect == "missing-record" and k == len(members) - 1):
                files[_s2_record(m)] = f"# Iteration {m.n}\n"
            if defect == "member-context" and k == 0:
                files[f"{ART}/CONTEXT.md"] = "# CONTEXT\nmember edit\n"
            if defect == "member-outside" and k == 1:
                files["tinyshop/stray.py"] = "# outside Touches\n"
            _commit(path, files, f"Iteration {m.n}: {m.name}")
            _git(path, "checkout", "-q", "main")
        order = list(reversed(members)) if defect == "merge-order" else members
        for m in order:
            _git(path, "merge", "-q", "--no-ff", "-m", f"Merge iteration {m.n}: {m.name}", f"member-{m.n}")
        if defect == "extra-commit":
            _commit(path, {"notes.txt": "between\n"}, "Tidy notes")
        for m in members:
            entries.append((len(entries) + 1, m.n))
        ctx_lines.append(f"- reconciled {members[0].n}-{members[-1].n}\n")
        if defect != "no-reconcile":
            files = dec_file() if defect == "no-reconcile-context" else {**ctx_file(), **dec_file()}
            _commit(path, files, f"Reconcile artifacts for iterations {members[0].n}{sep}{members[-1].n}")
        if defect == "worktree-left":
            _git(path, "worktree", "add", "-q", str(path.parent / "leftover-wt"), "-b", "leftover")
        i = j


def s2_transcript(its: list[It], *, extra: int = 0, extra_per_message: int = 1, sub_agents: int = 0,
                  prompt_style: str = "goal", split_group: bool = False, no_isolation: tuple = (),
                  skip_members: tuple = (), final_text: str = "Done.") -> str:
    """Synthetic S2 transcript: one Agent call per iteration (a group's calls share one
    assistant message with isolation "worktree"), then `extra` unattributed Agent calls.
    prompt_style "goal" quotes the Goal sentence; "name" only `Iteration N: Name`.
    split_group puts the first member in its own message; no_isolation / skip_members
    list iteration numbers whose call lacks isolation / is not dispatched."""
    ev: list[dict] = [ev_init()]
    counters = {"m": 0, "t": 0}

    def prompt(it: It) -> str:
        if prompt_style == "goal":
            return f"Execute Iteration {it.n}.\nGoal: Goal sentence {it.n}.\nScope: do the work."
        return f"Please carry out Iteration {it.n}: {it.name.title()} now."

    def emit(calls: list[tuple[str, str | None]]) -> None:
        counters["m"] += 1
        ids = []
        for p, iso in calls:
            counters["t"] += 1
            tid = f"toolu_{counters['t']}"
            ids.append(tid)
            ev.append(ev_assistant(f"msg_a{counters['m']}", blk_agent(tid, iso, prompt=p)))
        for tid in ids:
            ev.append(ev_tool_result(tid))

    i = 0
    while i < len(its):
        it = its[i]
        j = i + 1
        while it.group is not None and j < len(its) and its[j].group == it.group:
            j += 1
        step = [m for m in its[i:j] if m.n not in skip_members]
        iso = "worktree" if it.group is not None else None
        calls = [(prompt(m), None if m.n in no_isolation else iso) for m in step]
        if it.group is not None and split_group and len(calls) > 1:
            emit(calls[:1])
            emit(calls[1:])
        elif it.group is not None:
            emit(calls)
        else:
            for c in calls:
                emit([c])
        i = j
    for start in range(0, extra, max(extra_per_message, 1)):
        emit([("extra unrelated work", None)] * min(extra_per_message, extra - start))
    for s in range(sub_agents):
        ev.append(ev_assistant(f"msg_s{s}", blk_agent(f"toolu_sub{s}", None), parent="toolu_1"))
    ev.append(ev_text("msg_final", final_text))
    ev.append(ev_result())
    return "".join(json.dumps(e) + "\n" for e in ev)


def _s2_case(its: list[It], exit_: int, violations: list[str], *, repo: dict | None = None,
             tr: dict | None = None, extra: dict | None = None) -> Case:
    plan = render(its)
    transcript = s2_transcript(its, **(tr or {}))
    repo_kw = dict(repo or {})
    expect = {"checker": CHECK_RUN, "args": _run_args("full"), "exit": exit_, "violations": violations}
    expect.update(extra or {})
    return Case({"plan.md": plan, "transcript.jsonl": transcript}, expect,
                lambda d, its=its, kw=repo_kw, plan=plan: build_s2_repo(
                    d / "repo", its, plan.replace("@DIR@", "/scratch"), **kw))


# good S2 histories (5 and 7 iterations: D-007 applies, a plan this small has 5 at least)

def case_s2_good_7_iterations() -> Case:
    return _s2_case(base7(), 0, [], extra={"output_contains": ["subagents: 7"]})


def case_s2_good_5_iterations() -> Case:
    return _s2_case(base5(), 0, [], extra={"output_contains": ["subagents: 5"]})


def case_s2_good_reconcile_ascii_hyphen() -> Case:
    return _s2_case(base7(), 0, [], repo={"sep": "-"})


def case_s2_good_empty_decisions() -> Case:
    return _s2_case(base7(), 0, [], repo={"decisions": ""})


def case_s2_good_attribution_by_iteration_name() -> Case:
    return _s2_case(base7(), 0, [], tr={"prompt_style": "name"})


def case_s2_good_no_groups() -> Case:
    its = base5()
    for it in its:
        it.group = None
    return _s2_case(its, 0, [])


def case_s2_good_result_notes() -> Case:
    return _s2_case(base7(), 0, [], extra={"notes_contain": ["subagents: 7", "skill-source check skipped"]})


# VC-008: transcript and fork point

def case_s2_bad_vc008_members_in_two_messages() -> Case:
    return _s2_case(base7(), 1, ["VC-008"], tr={"split_group": True})


def case_s2_bad_vc008_missing_isolation() -> Case:
    return _s2_case(base7(), 1, ["VC-008"], tr={"no_isolation": (3,)})


def case_s2_bad_vc008_member_not_dispatched() -> Case:
    return _s2_case(base7(), 1, ["VC-008"], tr={"skip_members": (4,)})


def case_s2_bad_vc008_diverged_fork_points() -> Case:
    return _s2_case(base7(), 1, ["VC-008"], repo={"defect": "diverged-base"})


# VC-009: merge/reconcile history

def case_s2_bad_vc009_merge_order() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "merge-order"})


def case_s2_bad_vc009_extra_commit_before_reconcile() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "extra-commit"})


def case_s2_bad_vc009_reconcile_without_context() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "no-reconcile-context"})


def case_s2_bad_vc009_no_reconcile_commit() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "no-reconcile"})


def case_s2_bad_vc009_worktree_left_behind() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "worktree-left"})


def case_s2_bad_vc009_unmapped_commit_after_reconcile() -> Case:
    return _s2_case(base7(), 1, ["VC-009"], repo={"defect": "late-unmapped"})


# VC-010: member branch content and records

def case_s2_bad_vc010_member_changes_context() -> Case:
    return _s2_case(base7(), 1, ["VC-010"], repo={"defect": "member-context"})


def case_s2_bad_vc010_member_outside_touches() -> Case:
    return _s2_case(base7(), 1, ["VC-010"], repo={"defect": "member-outside"})


def case_s2_bad_vc010_member_record_missing() -> Case:
    return _s2_case(base7(), 1, ["VC-010"], repo={"defect": "missing-record"})


# VC-011: DECISIONS.md

_DEC_HEAD = "# DECISIONS\n\n"


def case_s2_bad_vc011_placeholder_id() -> Case:
    return _s2_case(base7(), 1, ["VC-011"], repo={
        "decisions": _DEC_HEAD + "## D-001: a  (Iteration 1)\n\n## D-?: b  (Iteration 2)\n"})


def case_s2_bad_vc011_id_gap() -> Case:
    return _s2_case(base7(), 1, ["VC-011"], repo={
        "decisions": _DEC_HEAD + "## D-001: a  (Iteration 1)\n\n## D-003: b  (Iteration 2)\n"})


def case_s2_bad_vc011_decreasing_iterations() -> Case:
    return _s2_case(base7(), 1, ["VC-011"], repo={
        "decisions": _DEC_HEAD + "## D-001: a  (Iteration 5)\n\n## D-002: b  (Iteration 2)\n"})


# VC-013: end to end on a copy

def case_s2_bad_vc013_unittest_fails() -> Case:
    bad = SMOKE_TEST + "\n    def test_fail(self):\n        self.fail('broken')\n"
    return _s2_case(base7(), 1, ["VC-013"], repo={"final_files": {"tests/test_smoke.py": bad}})


def case_s2_bad_vc013_wrong_tax() -> Case:
    return _s2_case(base7(), 1, ["VC-013"], repo={
        "final_files": {"tinyshop/tax.py": "def tax_cents(amount):\n    return amount * 9 // 100\n"}})


# ------------------------------------------------------------------- framework

def all_cases() -> list[tuple[str, object]]:
    g = globals()
    return [(n[len("case_"):].replace("_", "-"), g[n]) for n in sorted(g) if n.startswith("case_")]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: make_cases.py <outdir>", file=sys.stderr)
        return 2
    out = Path(argv[0]).resolve()
    cases = all_cases()
    for name, fn in cases:
        case = fn()
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        for rel, text in case.files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text.replace("@DIR@", str(d)), encoding="utf-8")
        if case.build is not None:
            case.build(d)
        (d / "expect.json").write_text(json.dumps(case.expect, indent=2) + "\n", encoding="utf-8")
    print(f"built {len(cases)} cases in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
