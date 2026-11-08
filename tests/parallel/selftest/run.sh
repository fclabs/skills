#!/usr/bin/env bash
# Run every golden selftest case (spec D7 / VC-019).
# Builds the cases with make_cases.py into a temp dir, runs each case's checker
# (cwd = case dir, --result-out appended), and asserts the exit code, the exact
# violation set, the BR-004 result shape and that stdout names every violation.
# Exits 0 only if every case behaves.
set -u
HERE=$(cd "$(dirname "$0")" && pwd -P)
HARNESS=$(dirname "$HERE")
export PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

python3 "$HERE/make_cases.py" "$TMP/cases" >/dev/null || { echo "make_cases.py failed" >&2; exit 1; }

python3 - "$HARNESS" "$TMP/cases" <<'PY'
import json, subprocess, sys
from pathlib import Path

harness, cases = Path(sys.argv[1]), Path(sys.argv[2])
KEYS = {"scenario": str, "run": int, "passed": bool, "violations": list, "notes": list, "model": str}
passed = failed = 0


def check(case):
    exp = json.loads((case / "expect.json").read_text())
    checker = harness / exp["checker"]
    if not checker.is_file():
        return f"checker {exp['checker']} is missing"
    res = case / "result.json"
    cp = subprocess.run([sys.executable, str(checker), *exp["args"], "--result-out", str(res)],
                        cwd=case, capture_output=True, text=True)
    if cp.returncode != exp["exit"]:
        return f"exit {cp.returncode}, expected {exp['exit']}: {(cp.stdout + cp.stderr).strip()[-300:]}"
    if exp["exit"] == 2:
        return None
    if not res.is_file():
        return "no result file written"
    data = json.loads(res.read_text())
    if set(data) != set(KEYS) or any(type(data[k]) is not t for k, t in KEYS.items()):
        return f"result file shape wrong: {data}"
    if not all(isinstance(v, str) for v in data["violations"] + data["notes"]):
        return "violations/notes must be lists of str"
    if set(data["violations"]) != set(exp["violations"]) or len(data["violations"]) != len(set(data["violations"])):
        return f"violations {data['violations']}, expected {exp['violations']}"
    if data["passed"] != (exp["exit"] == 0):
        return "passed flag disagrees with exit code"
    for v in exp["violations"]:
        if v not in cp.stdout:
            return f"stdout does not name {v}"
    if "model" in exp and data["model"] != exp["model"]:
        return f"model {data['model']!r}, expected {exp['model']!r}"
    for s in exp.get("notes_contain", []):
        if s not in data["notes"]:
            return f"note {s!r} missing from {data['notes']}"
    return None


for case in sorted(p for p in cases.iterdir() if (p / "expect.json").is_file()):
    try:
        err = check(case)
    except Exception as e:  # a broken case is a failed case
        err = f"{type(e).__name__}: {e}"
    if err is None:
        passed += 1
        print(f"PASS {case.name}")
    else:
        failed += 1
        print(f"FAIL {case.name}: {err}")
total = passed + failed
print(f"selftest: {passed}/{total} cases passed")
sys.exit(0 if total > 0 and failed == 0 else 1)
PY
