#!/usr/bin/env python3
"""Build the golden selftest cases (spec D7): make_cases.py <outdir>.

Each case is a directory <outdir>/<case>/ holding expect.json plus whatever
inputs the checker needs (plan.md, and for later iterations repo/ and
transcript.jsonl).  expect.json:
  {"checker": "check_plan.py"|"check_run.py", "args": [...], "exit": 0|1|2,
   "violations": [...]}                       # exact set of violation ids
optional keys: "model" (expected result-file model), "notes_contain" ([str]).
`args` run with the case directory as cwd; run.sh appends --result-out.

HOW TO ADD A CASE: write one function `case_<name>()` returning a Case(files,
expect).  The case directory name is <name> with underscores turned into
hyphens.  Use the plan builder (It, render) for synthetic tinyshop plans; the
token @DIR@ in any file text becomes the case directory's absolute path.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

CHECK_PLAN = "check_plan.py"


@dataclass
class Case:
    files: dict[str, str]
    expect: dict


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
        (d / "expect.json").write_text(json.dumps(case.expect, indent=2) + "\n", encoding="utf-8")
    print(f"built {len(cases)} cases in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
