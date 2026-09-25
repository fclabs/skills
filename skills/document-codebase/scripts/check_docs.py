#!/usr/bin/env python3
"""Mechanical quality checks for docs written by the document-codebase skill.

Usage: python3 check_docs.py <docs/codebase> [--repo <repo root>] [--seed N]

Exits 1 if any check fails. Judgment calls (is the citation *right*, is the
inference sound) stay with the reviewer; this script prints a citation sample
for that spot-check.
"""

from __future__ import annotations

import argparse
import math
import random
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

MARKER = "<!-- generated-by: document-codebase -->"
SECTION_FIELDS = ("Scope", "Commit", "Worktree", "Generated", "Confidence")
CAPSULE_FIELDS = ("Source", "Status", "Commit", "Worktree", "Generated", "Confidence")
# Files the skill writes; one of these without the marker means a lost header.
GENERATED_NAME = re.compile(r"^(\d\d-[\w-]+|_inventory|README)(\.generated)?\.md$")

CITATION = re.compile(r"`([^`\s:]+):(\d+)(?:-(\d+))?`")
UNKNOWN = re.compile(r"\[unknown\]")
OQ_REF = re.compile(r"\bOQ-(?:[a-z0-9][a-z0-9-]*-)?\d{3,}\b")
OQ_HEADING = re.compile(r"^#{2,}\s*(OQ-(?:[a-z0-9][a-z0-9-]*-)?\d{3,})\b", re.MULTILINE)
LABELS = ("verified", "inferred", "unknown")
SECRETS = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("API secret key", re.compile(r"\bsk-(?:live|proj|ant)?[-_]?[A-Za-z0-9]{20,}\b")),
    ("credential in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:(?![$<{*])[^/\s@]+@")),
]


@dataclass
class Citation:
    doc: Path
    doc_line: int
    path: str
    start: int
    end: int


@dataclass
class Report:
    failures: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=lambda: dict.fromkeys(LABELS, 0))
    generated: int = 0
    skipped: list[Path] = field(default_factory=list)

    def fail(self, doc: Path, line: int, message: str) -> None:
        self.failures.append(f"{doc}:{line}: {message}")


def header_fields(text: str) -> dict[str, str]:
    """Return `Key: value` pairs from the header, i.e. before the first `## `."""
    head = text.split("\n## ", 1)[0]
    return dict(re.findall(r"^([A-Z][\w /]*?):[ \t]*(.+)$", head, re.MULTILINE))


def check_header(doc: Path, text: str, report: Report) -> dict[str, str]:
    fields = header_fields(text)
    is_capsule = "capsules" in doc.parts
    for name in CAPSULE_FIELDS if is_capsule else SECTION_FIELDS:
        if name not in fields:
            report.fail(doc, 1, f"header is missing `{name}:`")
    if not re.search(r"^# \S", text, re.MULTILINE):
        report.fail(doc, 1, "header is missing the `# <title>` line")
    commit = fields.get("Commit", "")
    if commit and not re.match(r"^[0-9a-f]{40}\b", commit):
        report.fail(doc, 1, f"`Commit:` must start with a full 40-character SHA, got {commit!r}")
    worktree = fields.get("Worktree", "")
    if worktree and worktree not in ("clean", "dirty"):
        report.fail(doc, 1, f"`Worktree:` must be clean or dirty, got {worktree!r}")
    generated = fields.get("Generated", "")
    if generated and not re.match(r"^\d{4}-\d{2}-\d{2}$", generated):
        report.fail(doc, 1, f"`Generated:` must be YYYY-MM-DD, got {generated!r}")
    confidence = fields.get("Confidence", "")
    if confidence and not re.match(r"^(High|Medium|Low)\b", confidence):
        report.fail(doc, 1, f"`Confidence:` must start with High, Medium, or Low, got {confidence!r}")
    return fields


class Repo:
    """Reads repo files at a given commit, or from the working tree."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._cache: dict[tuple[str | None, str], int | None] = {}

    def line_count(self, path: str, commit: str | None) -> int | None:
        key = (commit, path)
        if key not in self._cache:
            self._cache[key] = self._read(path, commit)
        return self._cache[key]

    def _read(self, path: str, commit: str | None) -> int | None:
        if commit is None:
            file = self.root / path
            if not file.is_file():
                return None
            return len(file.read_bytes().splitlines())
        result = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            capture_output=True,
            check=False,
        )
        return len(result.stdout.splitlines()) if result.returncode == 0 else None


def looks_like_path(token: str) -> bool:
    return "://" not in token and ("/" in token or re.search(r"\.[A-Za-z]\w*$", token) is not None)


def check_body(doc: Path, text: str, commit: str | None, repo: Repo, report: Report) -> None:
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        for label in LABELS:
            report.labels[label] += line.count(f"[{label}")
        if UNKNOWN.search(line) and not OQ_REF.search(line):
            report.fail(doc, number, "`[unknown]` without an OQ- ID on the same line")
        for name, pattern in SECRETS:
            if pattern.search(line):
                report.fail(doc, number, f"looks like a secret value ({name})")
        if in_fence:
            continue  # copied contracts and examples, not claims
        for match in CITATION.finditer(line):
            path, start, end = match.group(1), int(match.group(2)), match.group(3)
            if not looks_like_path(path):
                continue
            last = int(end) if end else start
            lines = repo.line_count(path, commit)
            if lines is None:
                where = f"at {commit[:12]}" if commit else "in the working tree"
                report.fail(doc, number, f"cites `{path}`, which does not exist {where}")
            elif start < 1 or last < start or last > lines:
                report.fail(doc, number, f"cites `{match.group(0).strip('`')}`, but the file has {lines} lines")
            else:
                report.citations.append(Citation(doc, number, path, start, last))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("docs", type=Path, help="the <docs>/codebase directory")
    parser.add_argument("--repo", type=Path, default=Path("."), help="repository root (default: .)")
    parser.add_argument("--seed", type=int, default=None, help="seed for the citation sample")
    args = parser.parse_args()

    docs: Path = args.docs
    if not docs.is_dir():
        print(f"error: {docs} is not a directory", file=sys.stderr)
        return 2
    repo = Repo(args.repo.resolve())
    report = Report()
    defined: set[str] = set()
    referenced: dict[str, tuple[Path, int]] = {}

    for doc in sorted(docs.rglob("*.md")):
        text = doc.read_text(encoding="utf-8")
        rel = doc.relative_to(docs)
        if not text.startswith(MARKER):
            sibling = doc.with_name(doc.stem + ".generated.md")
            expected = GENERATED_NAME.match(doc.name) or "capsules" in rel.parts
            if expected and not sibling.exists():
                report.fail(rel, 1, "generated file is missing the `<!-- generated-by -->` header")
            else:
                report.skipped.append(rel)
            continue
        report.generated += 1
        fields = check_header(rel, text, report)
        sha = re.match(r"^[0-9a-f]{40}", fields.get("Commit", ""))
        commit = sha.group(0) if sha and fields.get("Worktree") == "clean" else None
        check_body(rel, text, commit, repo, report)
        defined.update(OQ_HEADING.findall(text))
        for number, line in enumerate(text.splitlines(), start=1):
            if OQ_HEADING.match(line):
                continue
            for oq in OQ_REF.findall(line):
                referenced.setdefault(oq, (rel, number))

    for oq, (rel, number) in sorted(referenced.items()):
        if oq not in defined:
            report.fail(rel, number, f"{oq} has no `### {oq} — …` heading in an open-questions file")

    total = len(report.citations)
    size = min(total, max(10, math.ceil(total * 0.10)))
    sample = random.Random(args.seed).sample(report.citations, size)

    print(f"Generated files: {report.generated}   Skipped (hand-written): {len(report.skipped)}")
    print(f"Citations checked: {total}   Open questions defined: {len(defined)}")
    print("Labels: " + " / ".join(f"{report.labels[k]} {k}" for k in LABELS))
    if sample:
        print(f"\nSpot-check sample ({size}) — re-open each and confirm it supports the claim:")
        for c in sorted(sample, key=lambda c: (str(c.doc), c.doc_line)):
            span = f"{c.start}-{c.end}" if c.end != c.start else str(c.start)
            print(f"  {c.doc}:{c.doc_line}  →  {c.path}:{span}")
    if report.failures:
        print(f"\nFAILED — {len(report.failures)} issue(s):")
        for failure in report.failures:
            print(f"  {failure}")
        return 1
    print("\nPASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
