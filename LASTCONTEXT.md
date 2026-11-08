# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Parallel work launched from the coordinator session: T01 (coordinator), T05a statistics, T08a preregistration manifest and T14a results renderer (Antigravity, model `gemini-3.8-flash-high`, `agy --dangerously-skip-permissions`, unsandboxed, no time limit), T09 batch runner (Claude subagent). Each ran in its own worktree and branch from `origin/main`.
- Every delegated result was reviewed and corrected by the coordinator: tests, ruff and mypy run again, specification checked. Corrections: range checks and lint in statistics; LF line endings in the manifest writer (text mode wrote CRLF on Windows); escaped pipes, JSON literals and marker lines with spaces in the renderer; unused `noqa` comments in the batch runner.
- Added the skill `antigravity` (`.claude/skills/antigravity/SKILL.md`), `scripts/agy_launch.sh`, a `.gitattributes` for LF in shell scripts, and the delegation section of `AGENTS.md` on `docs/agy-skill`.
- The repository is public (GitHub reports `private: false`). The design keeps playbook texts private until judging. Decision pending: private repository, or playbooks outside git.

## Repository state

| Branch | Worktree | Content | State |
|---|---|---|---|
| `chore/skeleton` | `../apart-research-swarm-alignment-wt-skeleton` | T01: package, `schema.py`, CLI stub, Python CI job | pushed, 13 tests, no PR |
| `feat/stats` | `..-wt-stats` | T05a statistics module | pushed, 14 tests, no PR |
| `feat/batch-runner` | `..-wt-batch` | T09 batch runner | pushed, 17 tests, no PR |
| `feat/prereg` | `..-wt-prereg` | T08a manifest generator | pushed, 9 tests, no PR |
| `feat/render-results` | `..-wt-render` | T14a results renderer | pushed, 14 tests, no PR |
| `docs/agy-skill` | `..-wt-agy-skill` | skill, launch script, delegation rules | pushed, no PR |
| `docs/handoff-parallel` | `..-wt-handoff` | this update | no PR |
| `exp/mock-split-attack` | `..-wt-mock-exp` | numpy simulations by another agent, untracked files | not mine, not pushed |

Notes:

- Worktrees `wt-stats`, `wt-batch`, `wt-prereg` and `wt-render` contain an untracked local `pyproject.toml` (copy from `chore/skeleton`) used to run ruff and mypy; `wt-batch` also has untracked copies of `schema.py` and `__init__.py`. Delete these untracked files before merging or rebasing onto `main` after T01 is merged.
- The batch runner and the other branches are independent of each other; only `feat/batch-runner` needs `schema.py` from T01.
- Merge order: `chore/skeleton` first, then the rest (each PR based on `main`).
- Remove the worktrees after their PR is merged (not the ones of other agents).

## Next step

1. Human approves the PRs; merge `chore/skeleton` first.
2. Open the remaining lane-A and lane-B tasks that depend on T01: T02 (LLM client, budget guard), T03 (world and ground truth), T06 (detectors), T05b (extraction); then T04 (swarm core), T04b (prompts and playbooks, after the playbook decision).
3. Provider check for G1: logprob support, temperature 0, model ids and limits (the human supplies console data for `docs/MODELS.md`).

## Open questions for the human

- Approve opening the redesign PR (rules: ask first).
- Close PR #13 (obsolete, Groq decision)?
- Stop the Docker project `swarmexp` (leftover from the dropped MCP stack)?
- Which provider and model for the swarm agents, and which low-cost model for the guardrail (G1)?

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART. The author is registered.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
