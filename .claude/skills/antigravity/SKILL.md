---
name: antigravity
description: Launch Antigravity (the `agy` CLI) as a delegated coding agent on one task in its own git worktree, let it run without a time limit, then review and correct its work. Use when a task from docs/TASKS.md is independent of the files other agents are editing and can run in parallel.
---

# Antigravity as a delegated agent

Antigravity (`agy`) is less capable than Claude. Every delegated task ends with a review by the coordinator (Claude), who corrects the errors before anything is proposed for a pull request.

## Preconditions

- The task is independent: its files are not edited by another agent at the same time.
- It has its own worktree and branch created from an up-to-date `origin/main`:
  `git worktree add ../apart-research-swarm-alignment-wt-<task> -b <type>/<name> origin/main`
- The task text is precise: file paths, function names and signatures, behavior, tests, and how expected values are obtained (independent method inside the test, never typed from memory).
- Check `git worktree list` and `git status -sb` first. Do not assume anything about the state.

## Prompt

Write one prompt file outside the repository (the scratchpad) made of two parts: the preamble below, then the task text.

Preamble (copy as is, adjusting nothing except the task text that follows):

- Work only inside the current directory (the worktree). Do not touch any `.env` file or any other directory.
- Do not run `git push`, do not open a pull request, do not merge, do not switch branches, do not use other worktrees.
- Do not edit `AGENTS.md`, `README.md`, `PENDING.md`, `LASTCONTEXT.md`, `pyproject.toml`, `.github/` or `docs/`. The coordinator owns them.
- Do not create `__init__.py` files or `tests/conftest.py`. Add `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))` at the top of each test file.
- Test-driven development: tests first, run `python -m pytest -q`, confirm the expected failure, then implement.
- Atomic commits on the current branch with conventional commit messages. No trailer lines. No history rewriting.
- English. Neutral language (no opinions, praise or intensifiers). No em dash, no emojis. Follow the forbidden-word rule in `AGENTS.md`.
- Never invent numbers. Expected values in tests come from an independent method computed in the test.
- Type hints on every function.
- No time limit: finish the whole task.
- At the end print a report: files created, commands run, last pytest output, deviations from the specification, open questions. Do not claim a test passes unless it was run and passed.

## Launch

Run from the helper script, in the human's terminal, in the background, without a sandbox (the human authorized this on 2026-11-08 for tasks in separate worktrees):

```
scripts/agy_launch.sh <worktree-dir> <prompt-file> <log-file> [model]
```

The default model is `gemini-3.8-flash-high` (the effort is part of the model id; `agy models` lists the options). The script runs:

```
agy --dangerously-skip-permissions --model gemini-3.8-flash-high --print "<prompt>"
```

With the Bash tool use `run_in_background: true` and `dangerouslyDisableSandbox: true`. There is no time limit. The tool reports when the process exits.

## While it runs

- Progress is visible in the worktree (`git status --short`, `git log --oneline`), not in the log: print mode writes its output at the end.
- Other `agy.exe` processes may belong to the human's own sessions. Never kill processes by name. Identify yours by the start time recorded in `<log-file>.start`.

## After it finishes: review and correct

1. Read the final report in the log. Treat its claims as unverified.
2. In the worktree: `git log --oneline origin/main..HEAD`, `git diff origin/main --stat`, read the code and the tests.
3. Run `python -m pytest -q`, `python -m ruff check src tests scripts` and `python -m mypy src` yourself.
4. Check against the specification, the language rules (neutral wording, forbidden words, no em dash), the Data Integrity rule (no hand-typed results), and that nothing outside the allowed files changed.
5. Fix the errors in the worktree with atomic commits. Add the missing tests.
6. Report to the human: what was delegated, what the review found, what was corrected, and ask for approval to open the pull request (base `main`).
