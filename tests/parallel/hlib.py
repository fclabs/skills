"""Shared helpers for the parallel-skills test harness (stdlib only, Python >= 3.11).

Plan parsing (the spec's "Parsing rules for checkers"), the BR-004 result
writer, the BR-003 exit-code convention and a minimal stream-json reader.
Imported by check_plan.py and, later, check_run.py.  Never writes inside a
scratch repo; the only file it writes is the result file it is asked to.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2

SHARED_RESOURCES = (
    "pyproject.toml",
    "tinyshop/__init__.py",
    "tinyshop/cli.py",
    "tinyshop/rates.toml",
    "docs/",
)
RESULT_KEYS = ("scenario", "run", "passed", "violations", "notes", "model")
_UNGROUPED_TOKENS = {"-", "—", "–", "none"}


class HarnessError(Exception):
    """Usage, missing-file or unparseable-input error (exit 2, BR-003)."""


# --------------------------------------------------------------------------
# text helpers
# --------------------------------------------------------------------------

def split_sections(text: str) -> list[tuple[str, str]]:
    """Split on level-2 headings: [(heading text, body text)], preamble first with heading ''."""
    out: list[tuple[str, str]] = []
    head, buf = "", []
    for line in text.splitlines():
        if line.startswith("## "):
            out.append((head, "\n".join(buf)))
            head, buf = line[3:].strip(), []
        else:
            buf.append(line)
    out.append((head, "\n".join(buf)))
    return out


def _label_re(label: str) -> str:
    return rf"^\*\*{re.escape(label)}(?::\*\*|\*\*:?)"


_ANY_LABEL = re.compile(r"^\*\*[^*\n]+(?::\*\*|\*\*:)|^---\s*$")


def field_text(body: str, label: str) -> str | None:
    """Text of a `**Label**:` / `**Label:**` field (may span lines); None if absent."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        m = re.match(_label_re(label), line)
        if not m:
            continue
        parts = [line[m.end():]]
        for nxt in lines[i + 1:]:
            if _ANY_LABEL.match(nxt):
                break
            parts.append(nxt)
        return "\n".join(parts).strip()
    return None


def split_row(line: str) -> list[str]:
    """Cells of a markdown table row."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def find_table(body: str) -> tuple[list[str], list[list[str]]] | None:
    """First markdown table in body: (header cells, data rows); None if there is none."""
    rows: list[list[str]] = []
    started = False
    for line in body.splitlines():
        if line.strip().startswith("|"):
            started = True
            cells = split_row(line)
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells):
                continue
            rows.append(cells)
        elif started:
            break
    if not rows:
        return None
    return rows[0], rows[1:]


# --------------------------------------------------------------------------
# Touches / Group / Depends parsing
# --------------------------------------------------------------------------

def parse_touches(raw: str, prefixes: tuple[str, ...] = (), artifact_name: str = "") -> list[str]:
    """Parse a Touches field into normalised path strings.

    Strips parenthetical notes, splits on commas/newlines, strips bullets and
    backticks (backticked tokens win when present), strips a leading scratch
    directory prefix and drops paths under `artifact_name` (a directory name).
    """
    spans: list[str] = []

    def hide(m: re.Match[str]) -> str:
        spans.append(m.group(1))
        return f"\0{len(spans) - 1}\0"

    t = re.sub(r"`([^`]*)`", hide, raw)
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r"\([^()]*\)", "", t)
    if "\0" in t:
        tokens = [spans[int(i)] for i in re.findall(r"\0(\d+)\0", t)]
    else:
        tokens = []
        for piece in re.split(r"[,\n]", t):
            piece = re.sub(r"^\s*(?:[-*•]\s+)", "", piece).strip()
            tokens.append(piece)
    out: list[str] = []
    for tok in tokens:
        tok = tok.strip()
        if not tok or tok.lower() in _UNGROUPED_TOKENS:
            continue
        tok = strip_prefix(tok, prefixes)
        while tok.startswith("./"):
            tok = tok[2:]
        comps = [c for c in tok.split("/") if c]
        if not comps:
            continue
        if artifact_name and artifact_name in comps:
            continue
        norm = "/".join(comps)
        if tok.endswith("/") and not norm.endswith("**"):
            norm += "/"
        if norm not in out:
            out.append(norm)
    return out


def strip_prefix(path: str, prefixes: tuple[str, ...]) -> str:
    for pre in sorted(prefixes, key=len, reverse=True):
        pre = pre.rstrip("/")
        if pre and path.startswith(pre + "/"):
            return path[len(pre) + 1:]
    return path


def _components(path: str) -> list[str]:
    comps = [c for c in path.split("/") if c]
    if comps and comps[-1] == "**":
        comps.pop()
    return comps


def paths_overlap(a: str, b: str) -> bool:
    """True when either path is a path-component prefix of the other (globs literal)."""
    ca, cb = _components(a), _components(b)
    n = min(len(ca), len(cb))
    return n > 0 and ca[:n] == cb[:n]


def matches_shared(path: str, shared: tuple[str, ...] = SHARED_RESOURCES) -> str | None:
    """The shared resource `path` overlaps, or None."""
    for s in shared:
        if paths_overlap(path, s):
            return s
    return None


def parse_group(raw: str | None) -> str | None:
    """Group value from a table cell or `**Parallel group**` field; None = ungrouped."""
    if raw is None:
        return None
    t = raw.replace("`", "").strip().lstrip(":").strip()
    if not t:
        return None
    tok = t.split()[0].strip(".,;:*")
    if not tok or tok.lower() in _UNGROUPED_TOKENS:
        return None
    return tok


def parse_depends(raw: str | None) -> set[int]:
    """All integers in a Depends-on field or cell."""
    if raw is None:
        return set()
    return {int(x) for x in re.findall(r"\d+", raw)}


def transitive_deps(deps: dict[int, set[int]], n: int) -> set[int]:
    """Transitive closure of dependencies of `n` (cycle safe)."""
    seen: set[int] = set()
    stack = list(deps.get(n, ()))
    while stack:
        d = stack.pop()
        if d in seen:
            continue
        seen.add(d)
        stack.extend(deps.get(d, ()))
    return seen


# --------------------------------------------------------------------------
# plan model
# --------------------------------------------------------------------------

@dataclass
class Iteration:
    n: int
    name: str
    body: str
    goal: str | None
    touches: list[str]
    depends_field: set[int]
    group_field: str | None
    row: list[str] | None = None          # table cells for this iteration, if any
    table_group: str | None = None
    table_depends: set[int] | None = None
    has_group_col: bool = False

    @property
    def group(self) -> str | None:
        """Group per the Execution Order table (field value when the table lacks the data)."""
        return self.table_group if (self.row is not None and self.has_group_col) else self.group_field

    @property
    def depends(self) -> set[int]:
        return self.table_depends if self.table_depends is not None else self.depends_field


@dataclass
class Plan:
    path: Path
    text: str
    artifact_name: str
    header: list[str] | None
    rows: list[list[str]]
    cols: dict[str, int | None]
    iterations: list[Iteration] = field(default_factory=list)

    def by_n(self, n: int) -> Iteration | None:
        for it in self.iterations:
            if it.n == n:
                return it
        return None


def _col(header: list[str], pred) -> int | None:
    for i, c in enumerate(header):
        if pred(c.lower()):
            return i
    return None


def scratch_prefixes(path: Path) -> tuple[str, ...]:
    """Candidate scratch-directory prefixes for a plan file (plain and resolved forms)."""
    out: list[str] = []
    for p in (Path(os.path.abspath(path)), path.resolve()):
        d = p.parent
        cands = [d] + ([d.parent] if d.name == "specs" else [])
        for c in cands:
            if str(c) not in out:
                out.append(str(c))
    return tuple(out)


def parse_plan(path: str | Path) -> Plan:
    """Parse a plan file. Raises HarnessError for a missing, empty or undecodable file."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HarnessError(f"plan not found: {path}")
    except (OSError, UnicodeDecodeError) as e:
        raise HarnessError(f"cannot read plan {path}: {e}")
    if not text.strip():
        raise HarnessError(f"plan is empty: {path}")
    stem = p.name[:-3] if p.name.endswith(".md") else p.name
    artifact_name = stem + "-artifacts"
    prefixes = scratch_prefixes(p)

    header, rows = None, []
    sections = split_sections(text)
    for head, body in sections:
        if head.lower().startswith("execution order"):
            tbl = find_table(body)
            if tbl:
                header, rows = tbl
            break
    cols: dict[str, int | None] = {"iteration": None, "depends": None, "group": None, "touches": None}
    if header:
        cols["iteration"] = _col(header, lambda c: "iteration" in c)
        cols["depends"] = _col(header, lambda c: "depends on" in c)
        cols["group"] = _col(header, lambda c: "parallel group" in c)
        cols["touches"] = _col(header, lambda c: c.startswith("touches"))
    plan = Plan(p, text, artifact_name, header, rows, cols)

    row_by_n: dict[int, list[str]] = {}
    ic = cols["iteration"] if cols["iteration"] is not None else 0
    for r in rows:
        m = re.search(r"\d+", r[ic]) if ic < len(r) else None
        if m and int(m.group()) not in row_by_n:
            row_by_n[int(m.group())] = r

    for head, body in sections:
        m = re.match(r"Iteration\s+(\d+)\b[:\s—-]*(.*)", head)
        if not m:
            continue
        n = int(m.group(1))
        raw_touch = field_text(body, "Touches") or ""
        it = Iteration(
            n=n,
            name=m.group(2).strip(),
            body=body,
            goal=field_text(body, "Goal"),
            touches=parse_touches(raw_touch, prefixes, artifact_name),
            depends_field=parse_depends(field_text(body, "Depends on")),
            group_field=parse_group(field_text(body, "Parallel group")),
        )
        r = row_by_n.get(n)
        if r is not None:
            it.row = r
            gc, dc = cols["group"], cols["depends"]
            it.has_group_col = gc is not None
            if gc is not None and gc < len(r):
                it.table_group = parse_group(r[gc])
            if dc is not None and dc < len(r):
                it.table_depends = parse_depends(r[dc])
        plan.iterations.append(it)
    return plan


# --------------------------------------------------------------------------
# findings, results, exit codes
# --------------------------------------------------------------------------

@dataclass
class Findings:
    """Accumulates violations (id + message) and notes for one checker run."""
    items: list[tuple[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, vc: str, msg: str) -> None:
        self.items.append((vc, msg))

    @property
    def violations(self) -> list[str]:
        out: list[str] = []
        for vc, _ in self.items:
            if vc not in out:
                out.append(vc)
        return out

    def lines(self) -> list[str]:
        return [f"{vc}: {msg}" for vc, msg in self.items]


def write_result(path: str | Path, scenario: str, run: int, violations: list[str],
                 notes: list[str], model: str) -> dict:
    """Write the BR-004 result file and return its content."""
    data = {
        "scenario": scenario,
        "run": run,
        "passed": not violations,
        "violations": list(violations),
        "notes": list(notes),
        "model": model,
    }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
    except OSError as e:
        raise HarnessError(f"cannot write result file {path}: {e}")
    return data


def exit_code(violations: list[str]) -> int:
    """BR-003: 0 when nothing violated, 1 otherwise (usage errors are raised as HarnessError)."""
    return EXIT_FAIL if violations else EXIT_OK


# --------------------------------------------------------------------------
# stream-json
# --------------------------------------------------------------------------

def read_stream(path: str | Path) -> list[dict]:
    """Read a stream-json transcript: one JSON object per line. HarnessError if unusable."""
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HarnessError(f"transcript not found: {path}")
    except (OSError, UnicodeDecodeError) as e:
        raise HarnessError(f"cannot read transcript {path}: {e}")
    events: list[dict] = []
    for i, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            raise HarnessError(f"transcript line {i} is not JSON: {path}")
        if not isinstance(ev, dict):
            raise HarnessError(f"transcript line {i} is not an object: {path}")
        events.append(ev)
    if not events:
        raise HarnessError(f"transcript is empty: {path}")
    return events


def orchestrator_events(events: list[dict]) -> list[dict]:
    """Events not emitted by a subagent (null/absent parent_tool_use_id)."""
    return [e for e in events if e.get("parent_tool_use_id") is None]


def init_event(events: list[dict]) -> dict:
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            return e
    raise HarnessError("transcript has no system init event")


def init_model(events: list[dict]) -> str:
    """Model id from the init event (D15). HarnessError if absent."""
    model = init_event(events).get("model")
    if not isinstance(model, str) or not model:
        raise HarnessError("init event carries no model")
    return model


# --------------------------------------------------------------------------
# transcript helpers (orchestrator level; Iteration 4)
# --------------------------------------------------------------------------
# A "message" is the set of orchestrator assistant events sharing one
# message.id (stream-json emits one event per content block).  `msg_index` is
# the ordinal of the message by first appearance; `event_index` is the index in
# the full event list, so tool_use and tool_result positions are comparable.

AGENT_TOOL_NAMES = ("Agent", "Task")


@dataclass
class ToolUse:
    event_index: int
    msg_id: str
    msg_index: int
    id: str
    name: str
    input: dict


@dataclass
class TextBlock:
    event_index: int
    msg_id: str
    msg_index: int
    text: str


@dataclass
class ToolResult:
    event_index: int
    tool_use_id: str
    content: object
    is_error: bool


@dataclass
class Transcript:
    events: list[dict]
    init: dict
    model: str
    result: dict | None


def _blocks(ev: dict) -> list[dict]:
    msg = ev.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


def assistant_blocks(events: list[dict]) -> list[tuple[int, str, int, dict]]:
    """(event_index, msg_id, msg_index, block) for orchestrator assistant content blocks."""
    out: list[tuple[int, str, int, dict]] = []
    order: dict[str, int] = {}
    for i, ev in enumerate(events):
        if ev.get("type") != "assistant" or ev.get("parent_tool_use_id") is not None:
            continue
        msg = ev.get("message")
        mid = msg.get("id") if isinstance(msg, dict) else None
        if not isinstance(mid, str) or not mid:
            mid = f"_event{i}"
        idx = order.setdefault(mid, len(order))
        for b in _blocks(ev):
            out.append((i, mid, idx, b))
    return out


def tool_uses(events: list[dict], names: tuple[str, ...] | None = None) -> list[ToolUse]:
    """Orchestrator-level tool_use blocks, optionally filtered by tool name."""
    out = []
    for i, mid, idx, b in assistant_blocks(events):
        if b.get("type") == "tool_use" and (names is None or b.get("name") in names):
            inp = b.get("input")
            out.append(ToolUse(i, mid, idx, str(b.get("id", "")), str(b.get("name", "")),
                               inp if isinstance(inp, dict) else {}))
    return out


def agent_calls(events: list[dict]) -> list[ToolUse]:
    """Orchestrator-level Agent/Task calls (subagent-emitted calls excluded)."""
    return tool_uses(events, AGENT_TOOL_NAMES)


def group_by_message(uses: list[ToolUse]) -> dict[int, list[ToolUse]]:
    """Group tool uses by assistant message ordinal (the spec's 'single assistant message')."""
    out: dict[int, list[ToolUse]] = {}
    for u in uses:
        out.setdefault(u.msg_index, []).append(u)
    return out


def text_blocks(events: list[dict]) -> list[TextBlock]:
    """Orchestrator assistant text blocks in transcript order."""
    return [TextBlock(i, mid, idx, str(b.get("text", "")))
            for i, mid, idx, b in assistant_blocks(events) if b.get("type") == "text"]


def tool_results(events: list[dict]) -> dict[str, ToolResult]:
    """Orchestrator-level tool_result blocks keyed by tool_use_id."""
    out: dict[str, ToolResult] = {}
    for i, ev in enumerate(events):
        if ev.get("type") != "user" or ev.get("parent_tool_use_id") is not None:
            continue
        for b in _blocks(ev):
            if b.get("type") == "tool_result" and isinstance(b.get("tool_use_id"), str):
                out[b["tool_use_id"]] = ToolResult(i, b["tool_use_id"], b.get("content"),
                                                   bool(b.get("is_error")))
    return out


def result_event(events: list[dict]) -> dict | None:
    """The last `result` event, or None."""
    found = None
    for e in events:
        if e.get("type") == "result":
            found = e
    return found


def permission_denials(events: list[dict]) -> list:
    r = result_event(events)
    d = r.get("permission_denials") if r else None
    return d if isinstance(d, list) else []


def load_transcript(path: str | Path) -> Transcript:
    """Read and shape-check a stream-json transcript (spec 'Transcript').

    HarnessError (exit 2) when missing, unparseable, without an init event with
    a model id, or without orchestrator-level assistant events.
    """
    events = read_stream(path)
    init = init_event(events)
    model = init_model(events)
    if not assistant_blocks(events):
        raise HarnessError(f"transcript has no assistant events: {path}")
    return Transcript(events, init, model, result_event(events))
