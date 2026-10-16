---
name: ask-your-coworker-for-feedback
description: >-
  Gets independent, actionable feedback on an output you produced (code diff,
  spec, plan, design, doc, analysis) by asking other coding agents installed on
  the machine — Claude Code, Codex, Cursor Agent, Gemini CLI — one subagent per
  coworker, then has a separate reviewer agent triage the feedback and say which
  points are correct and which do not apply. Use when the user asks for a second
  opinion, a peer review from other agents/models, "ask codex/cursor/claude what
  they think", "get feedback from my coworkers", or wants an output
  cross-checked before shipping. Always use this skill instead of improvising a
  multi-agent review.
---

# Ask Your Coworker for Feedback

Send one artifact to every other coding agent available locally, collect their critiques, and have a separate agent judge them. The value is **independence**: different models catch different mistakes, and a final triage keeps you from blindly applying advice that is wrong or irrelevant.

Works the same in Claude Code, Cursor, and Codex. Steps say "subagent" — use your host's mechanism (Claude Code: `Agent` tool; Cursor: Task/subagent tool). If your host has no subagents, run the per-coworker commands as parallel background shell jobs yourself and do the triage in a fresh pass.

`$SKILL_DIR` below = the directory containing this SKILL.md.

## Workflow

### 1. Pin down what is being reviewed
Identify the **subject** (file paths, `git diff` range, or pasted text) and its **intent** (what it was supposed to achieve, constraints, the requirements/spec it must satisfy). If either is unclear, ask the user one short question. Never review something you cannot point the coworkers at.

### 2. Detect coworkers
```
python3 $SKILL_DIR/scripts/coworkers.py detect --json
```
- Returns `available`, `path`, `version`, and `is_host` (true = this is probably the agent you are running in; still usable, but a different vendor is more independent — prefer the others, include the host only if it is the sole option or the user asks).
- "Installed" does not mean "logged in". Auth failures show up in step 4; just report them, don't try to fix auth.
- If the user named specific coworkers, use only those. If none are available, tell the user and stop.

### 3. Write the review brief (one file, shared by all coworkers)
Write to a scratch directory (not the repo), e.g. `<scratch>/brief.md`. Coworkers have **no memory of this conversation**, so the brief must be self-contained. Use this structure:

```markdown
# Review request

## Role
You are a skeptical senior reviewer. You are read-only: do NOT edit files or run
state-changing commands. Reading files, grep, and read-only git commands are fine.

## What to review
[Subject: exact paths / `git diff BASE..HEAD` / inline text]

## Intent and context
[What it should accomplish, requirements, constraints, non-goals, relevant conventions]

## What I most want checked
[2–4 focus areas, e.g. correctness of X, missing edge cases, security of Y]

## Output format (mandatory)
Return a numbered list of findings, most severe first. For EACH finding:
- **Severity**: blocker | major | minor | nit
- **Where**: `path:line` or section heading (verify it by opening the file)
- **Problem**: one or two sentences, stating the observable fact
- **Evidence**: the quoted line/text, a failing input, a command you ran, or a
  reference (spec requirement ID, docs URL, language/library documentation)
- **Fix**: a concrete change — code snippet or exact rewording, not "consider improving"
- **Confidence**: high | medium | low, and what would change your mind

## Rules
- Only report issues you verified against the actual files. Do not guess about code you did not read.
- No praise, no restating the work, no generic best-practice advice without a concrete failure it causes here.
- If a point is a matter of taste, label it `nit`.
- If you find nothing in an area I asked about, say so in one line instead of inventing findings.
- Cite references (docs, specs, standards) only if you are sure they exist; give the URL or section.
- End with a section "Checked and OK" listing what you verified and found sound.
```

Tailor "What I most want checked" to the artifact type (see [references/focus-areas.md](references/focus-areas.md)). Include the **facts** the coworker would otherwise have to rediscover: commands to run tests, file locations, relevant spec IDs, known limitations. Do **not** include your own opinion of whether the work is good — that biases the review.

### 4. One subagent per coworker, in parallel
Spawn all coworker subagents in a single message. Each subagent's whole job:

> Run exactly this command and report back the path of the output file and its full contents. Do not edit anything, do not summarize or alter the coworker's reply.
> `python3 $SKILL_DIR/scripts/coworkers.py ask <agent> --prompt-file <scratch>/brief.md --out <scratch>/feedback-<agent>.md --cwd <repo root>`
>
> If the command exits non-zero, return the error text verbatim and which exit code (2 unavailable, 3 agent failed/auth, 4 timeout). Do not retry more than once, and do not fall back to answering the review yourself.

The script runs each CLI headless and read-only (Claude `-p --permission-mode plan`, Codex `exec -s read-only`, Cursor `-p --mode ask`, Gemini `--approval-mode plan`). `--dry-run` shows the exact command. Use `--model` only if the user asks for a specific model.

A coworker that fails is reported to the user and skipped; continue with the rest. If fewer than one succeeds, stop and say so.

### 5. Triage with a separate agent
Spawn **one new subagent** that did not take part in the review (and, ideally, did not produce the artifact). Give it the subject, the intent, and the paths of all `feedback-*.md` files, with these instructions:

> You are the arbiter. For every finding in every feedback file:
> 1. Merge duplicates across coworkers (note agreement — convergence raises confidence).
> 2. **Verify it yourself** against the real files/spec: open the cited `path:line`, run the cited check if cheap and read-only, check any cited reference actually says what is claimed.
> 3. Assign a verdict: **Correct** (reproduced/verified), **Partially correct** (right symptom, wrong cause or fix), **Does not apply** (wrong premise, out of scope, contradicts a stated requirement/constraint, already handled, or pure taste), or **Cannot verify**.
> 4. Give your own opinion in 1–3 sentences with the evidence for the verdict. Disagree with the coworker whenever the evidence says so; do not defer to them.
> 5. For Correct/Partially correct, state the action: exact change and its priority (must-fix / should-fix / optional).
>
> Output: a table `# | Coworker(s) | Severity (theirs → yours) | Verdict | Action`, then per-finding detail, then "Rejected feedback and why", then a short list of anything *no* coworker raised that you noticed while verifying.

### 6. Report to the user
Give the user: which coworkers answered (and which failed, with reason), the arbiter's table, and the must-fix list. Save the full set to `<scratch>/feedback-summary.md` and tell the user where it is. **Do not apply changes automatically** — ask which to apply, unless the user already said to fix what is valid.

## Guidelines
- Never put secrets in the brief; coworkers send content to their vendors' APIs. If the subject is confidential or proprietary, confirm with the user before sending it out.
- The brief goes to external services, so state in your reply which coworkers received the content.
- Keep reviewers read-only. If a CLI cannot be run read-only, skip it rather than running it with write access.
- Don't rerun the whole round repeatedly; one round, then fix, then (optionally) one more round on the revised output.
