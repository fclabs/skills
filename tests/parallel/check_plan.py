#!/usr/bin/env python3
"""Plan checker for scenario S1 (VC-003..VC-007, VC-025).

Usage: check_plan.py <plan.md> --run K [--transcript F] [--result-out F]

Prints one `VC-NNN: message` line per violation and exits 1; exits 2 on usage,
missing-file or unparseable input; exits 0 when the plan passes (BR-003).
Read-only apart from the optional result file.
"""
from __future__ import annotations

import argparse
import re
import sys

import hlib
from hlib import Findings, Iteration, Plan

MODULES = ("tinyshop/pricing.py", "tinyshop/inventory.py", "tinyshop/shipping.py")
ORDERS = "tinyshop/orders.py"
CLI = "tinyshop/cli.py"
NOTE_NO_TRANSCRIPT = "D14/D15 skipped: no --transcript"
NOTE_SKILL_SOURCE = "skill-source check skipped"


def _names(it: Iteration, path: str) -> bool:
    return path in it.touches


def check_vc003(plan: Plan, f: Findings) -> None:
    if plan.header is None:
        f.add("VC-003", "no Execution Order table found")
        return
    missing = [k for k, label in (("iteration", "Iteration"), ("depends", "Depends on"),
                                   ("group", "Parallel group"), ("touches", "Touches*"))
               if plan.cols[k] is None]
    if missing:
        f.add("VC-003", f"Execution Order header lacks column(s): {', '.join(missing)}")
    if len(plan.rows) != len(plan.iterations):
        f.add("VC-003", f"{len(plan.rows)} table rows but {len(plan.iterations)} Iteration headings")


def module_owners(plan: Plan) -> dict[str, list[int]]:
    return {m: [it.n for it in plan.iterations if _names(it, m)] for m in MODULES}


def check_vc004(plan: Plan, f: Findings) -> None:
    owners = module_owners(plan)
    bad = False
    for m, ns in owners.items():
        if len(ns) != 1:
            f.add("VC-004", f"{m} is named by {len(ns)} iterations {ns}, expected exactly one")
            bad = True
    if bad:
        return
    ns = [owners[m][0] for m in MODULES]
    if len(set(ns)) != 3:
        f.add("VC-004", f"module files are not in three distinct iterations: {ns}")
        return
    its = [plan.by_n(n) for n in ns]
    groups = {it.group for it in its}
    if len(groups) != 1 or None in groups:
        f.add("VC-004", f"module iterations {ns} lack one common parallel group: "
                        f"{sorted(str(g) for g in (it.group for it in its))}")
    order = sorted(it.n for it in plan.iterations)
    pos = sorted(order.index(n) for n in ns)
    if pos[-1] - pos[0] != 2:
        f.add("VC-004", f"module iterations {sorted(ns)} are not adjacent in iteration order")
    if len({frozenset(it.depends) for it in its}) != 1:
        f.add("VC-004", f"module iterations {sorted(ns)} have different Depends on sets")


def check_vc005(plan: Plan, f: Findings) -> None:
    deps = {it.n: it.depends for it in plan.iterations}
    for it in plan.iterations:
        if it.group is not None:
            for p in it.touches:
                s = hlib.matches_shared(p)
                if s:
                    f.add("VC-005", f"iteration {it.n} is in group {it.group} but touches shared resource {s} ({p})")
            for d in sorted(hlib.transitive_deps(deps, it.n)):
                other = plan.by_n(d)
                if other is not None and other.group == it.group:
                    f.add("VC-005", f"iteration {it.n} depends on iteration {d} in the same group {it.group}")
        if it.row is not None:
            if it.has_group_col and it.group_field != it.table_group:
                f.add("VC-005", f"iteration {it.n}: Parallel group field {it.group_field!r} "
                                f"disagrees with table cell {it.table_group!r}")
            if it.table_depends is not None and it.depends_field != it.table_depends:
                f.add("VC-005", f"iteration {it.n}: Depends on field {sorted(it.depends_field)} "
                                f"disagrees with table cell {sorted(it.table_depends)}")


def check_vc006(plan: Plan, f: Findings) -> None:
    if plan.rows:
        ic = plan.cols["iteration"] if plan.cols["iteration"] is not None else 0
        ends = []
        for r in plan.rows[:1] + plan.rows[-1:]:
            m = re.search(r"\d+", r[ic]) if ic < len(r) else None
            ends.append(int(m.group()) if m else None)
        for label, n in zip(("first", "last"), ends):
            it = plan.by_n(n) if n is not None else None
            if it is not None and it.group is not None:
                f.add("VC-006", f"{label} table row (iteration {n}) is in group {it.group}")
    elif plan.iterations:
        for label, it in (("first", plan.iterations[0]), ("last", plan.iterations[-1])):
            if it.group is not None:
                f.add("VC-006", f"{label} iteration {it.n} is in group {it.group}")
    for it in plan.iterations:
        if it.group is None:
            continue
        if not re.search(r"iterations/\d{2}-", it.body):
            f.add("VC-006", f"grouped iteration {it.n} names no iterations/NN- record file")
        for s in ("Proposed CONTEXT.md changes", "Proposed decisions"):
            if s not in it.body:
                f.add("VC-006", f"grouped iteration {it.n} lacks the string {s!r}")


def check_vc007(plan: Plan, f: Findings) -> None:
    groups: dict[str, list[Iteration]] = {}
    for it in plan.iterations:
        if it.group is not None:
            groups.setdefault(it.group, []).append(it)
    for g, members in groups.items():
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                for pa in a.touches:
                    for pb in b.touches:
                        if hlib.paths_overlap(pa, pb):
                            f.add("VC-007", f"group {g}: iterations {a.n} and {b.n} overlap on {pa} / {pb}")


def check_vc025(plan: Plan, f: Findings) -> None:
    owners = module_owners(plan)
    mod_ns = {m: ns[0] for m, ns in owners.items() if len(ns) == 1}
    mod_groups = {plan.by_n(n).group for n in mod_ns.values()} - {None}
    for m, n in mod_ns.items():
        d = plan.by_n(n).depends
        if d != {1}:
            f.add("VC-025", f"module iteration {n} ({m}) Depends on {sorted(d)}, expected [1]")
    orders = [it for it in plan.iterations if _names(it, ORDERS)]
    if not orders:
        f.add("VC-025", f"no iteration names {ORDERS}")
    need = {mod_ns[m] for m in MODULES[:2] if m in mod_ns}
    for it in orders:
        if it.group is not None and it.group in mod_groups:
            f.add("VC-025", f"orders iteration {it.n} is in the safe group {it.group}")
        if not need <= it.depends:
            f.add("VC-025", f"orders iteration {it.n} Depends on {sorted(it.depends)}, "
                            f"missing {sorted(need - it.depends)}")
    clis = [it for it in plan.iterations if _names(it, CLI)]
    if not clis:
        f.add("VC-025", f"no iteration names {CLI}")
    need_all = set(mod_ns.values())
    for it in clis:
        if not need_all <= it.depends:
            f.add("VC-025", f"cli iteration {it.n} Depends on {sorted(it.depends)}, "
                            f"missing {sorted(need_all - it.depends)}")


def run_checks(plan: Plan) -> Findings:
    f = Findings()
    for chk in (check_vc003, check_vc004, check_vc005, check_vc006, check_vc007, check_vc025):
        chk(plan, f)
    return f


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="check_plan.py", description=__doc__.splitlines()[0])
    ap.add_argument("plan")
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--transcript")
    ap.add_argument("--result-out")
    args = ap.parse_args(argv)
    try:
        plan = hlib.parse_plan(args.plan)
        model = ""
        extra_notes: list[str] = []
        if args.transcript:
            model = hlib.init_model(hlib.read_stream(args.transcript))
            extra_notes.append(NOTE_SKILL_SOURCE)
        else:
            extra_notes.append(NOTE_NO_TRANSCRIPT)
        f = run_checks(plan)
        f.notes.extend(extra_notes)
        if args.result_out:
            hlib.write_result(args.result_out, "plan", args.run, f.violations, f.notes, model)
    except hlib.HarnessError as e:
        print(f"check_plan.py: error: {e}", file=sys.stderr)
        return hlib.EXIT_USAGE
    for line in f.lines():
        print(line)
    for n in f.notes:
        print(f"note: {n}")
    print("check_plan: " + (f"FAIL {' '.join(f.violations)}" if f.violations else "OK"))
    return hlib.exit_code(f.violations)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
