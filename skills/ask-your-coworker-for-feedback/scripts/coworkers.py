#!/usr/bin/env python3
"""Detect and invoke other coding-agent CLIs ("coworkers") for read-only feedback.

Subcommands:
  detect [--json]                      list coworkers installed on this machine
  ask AGENT --prompt-file F --out F    run one coworker headlessly, read-only

Stdlib only. Works from Claude Code, Cursor, Codex, or a plain shell.
Exit codes for `ask`: 0 ok, 2 bad usage / agent unavailable, 3 agent failed, 4 timeout.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Each coworker: binary, how to detect the host we are running inside, and a
# read-only headless invocation. `{model}` args are appended only if --model is given.
COWORKERS = {
    "claude": {
        "binary": "claude",
        "vendor": "Anthropic Claude Code",
        "host_env": ["CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT"],
        "model_flag": "--model",
    },
    "codex": {
        "binary": "codex",
        "vendor": "OpenAI Codex CLI",
        "host_env": ["CODEX_SANDBOX", "CODEX_CI", "CODEX_THREAD_ID"],
        "model_flag": "-m",
    },
    "cursor": {
        "binary": "cursor-agent",
        "alt_binaries": ["agent"],
        "vendor": "Cursor Agent CLI",
        "host_env": ["CURSOR_AGENT", "CURSOR_TRACE_ID"],
        "model_flag": "--model",
    },
    "gemini": {
        "binary": "gemini",
        "vendor": "Google Gemini CLI",
        "host_env": ["GEMINI_CLI"],
        "model_flag": "-m",
    },
}


def find_binary(spec: dict) -> str | None:
    for name in [spec["binary"], *spec.get("alt_binaries", [])]:
        path = shutil.which(name)
        if path:
            return path
    return None


def version_of(path: str) -> str:
    try:
        out = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
        return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr).strip() else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def is_host(spec: dict) -> bool:
    return any(os.environ.get(v) for v in spec["host_env"])


def build_command(name: str, binary: str, prompt: str, out_file: Path, model: str | None):
    """Return (argv, stdin_text). All invocations are read-only and non-interactive."""
    model_args = [COWORKERS[name]["model_flag"], model] if model else []
    if name == "claude":
        # plan mode = no edits/commands; read-only tools only. Prompt via stdin.
        argv = [binary, "-p", "--permission-mode", "plan", "--no-session-persistence",
                "--allowedTools", "Read", "Grep", "Glob", *model_args]
        return argv, prompt
    if name == "codex":
        argv = [binary, "exec", "-s", "read-only", "--skip-git-repo-check", "--ephemeral",
                "-o", str(out_file), *model_args, "-"]
        return argv, prompt
    if name == "cursor":
        # --mode ask = read-only Q&A; --trust avoids the workspace-trust prompt.
        argv = [binary, "-p", "--mode", "ask", "--trust", "--output-format", "text",
                *model_args, prompt]
        return argv, None
    if name == "gemini":
        argv = [binary, "--approval-mode", "plan", "-o", "text", *model_args, "-p", ""]
        return argv, prompt
    raise KeyError(name)


def cmd_detect(args: argparse.Namespace) -> int:
    rows = []
    for name, spec in COWORKERS.items():
        path = find_binary(spec)
        rows.append({
            "name": name,
            "vendor": spec["vendor"],
            "available": bool(path),
            "path": path,
            "version": version_of(path) if path else "",
            "is_host": is_host(spec),  # heuristic: we appear to be running inside this agent
        })
    if args.json:
        print(json.dumps({"coworkers": rows}, indent=2))
        return 0
    for r in rows:
        mark = "OK " if r["available"] else "-- "
        extra = " (host: same agent running this skill; less independent)" if r["is_host"] and r["available"] else ""
        print(f"{mark}{r['name']:<7} {r['vendor']:<22} {r['path'] or 'not installed'} {r['version']}{extra}")
    avail = [r["name"] for r in rows if r["available"]]
    print(f"\navailable: {' '.join(avail) if avail else '(none)'}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    spec = COWORKERS[args.agent]
    binary = find_binary(spec)
    if not binary:
        print(f"error: {args.agent} CLI not found on PATH", file=sys.stderr)
        return 2
    prompt = Path(args.prompt_file).read_text()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    scratch = Path(tempfile.mkdtemp(prefix=f"coworker-{args.agent}-"))
    last_msg = scratch / "last-message.txt"
    argv, stdin_text = build_command(args.agent, binary, prompt, last_msg, args.model)
    if args.dry_run:
        shown = [a if len(a) < 120 else a[:117] + "..." for a in argv]
        print(json.dumps({"argv": shown, "stdin": stdin_text is not None, "cwd": args.cwd}, indent=2))
        return 0

    try:
        proc = subprocess.run(argv, input=stdin_text, capture_output=True, text=True,
                              cwd=args.cwd, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(f"error: {args.agent} timed out after {args.timeout}s", file=sys.stderr)
        return 4
    text = proc.stdout
    if args.agent == "codex" and last_msg.exists() and last_msg.read_text().strip():
        text = last_msg.read_text()  # stdout of codex exec includes progress noise
    if proc.returncode != 0 or not text.strip():
        print(f"error: {args.agent} exit={proc.returncode}\n{proc.stderr.strip()[-2000:]}", file=sys.stderr)
        return 3
    out_path.write_text(text)
    print(str(out_path))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="list installed coworkers")
    d.add_argument("--json", action="store_true")
    d.set_defaults(fn=cmd_detect)
    a = sub.add_parser("ask", help="ask one coworker for feedback (read-only)")
    a.add_argument("agent", choices=sorted(COWORKERS))
    a.add_argument("--prompt-file", required=True)
    a.add_argument("--out", required=True, help="file to write the coworker's reply to")
    a.add_argument("--cwd", default=os.getcwd(), help="working dir the coworker can read (default: cwd)")
    a.add_argument("--model", help="optional model override for that CLI")
    a.add_argument("--timeout", type=int, default=600)
    a.add_argument("--dry-run", action="store_true", help="print the command, do not run")
    a.set_defaults(fn=cmd_ask)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
