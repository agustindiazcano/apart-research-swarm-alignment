# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Branch `docs/pr-base-main-rule` (worktree `../apart-research-swarm-alignment-wt-pr-base-rule`, based on `main`): added the rule that every PR is based on `main` and PRs are not stacked.
- PRs #6 to #10 had been stacked and merged into each other's branches, so only #5 reached `main`. PR #11 brought their content to `main` (merged). `main` now has `docs/VERIFICATION.md`, `docs/hackathon/PRIOR_WORK_DIGEST.md` and the multi-agent rule.
- Removed the two merged worktrees created earlier. Old chain branches (`chore/env-prior-work`, `docs/verify-external-stack`, `docs/prior-work`, `docs/multi-agent-rule`, `docs/readme-remove-todo-links`) are merged and can be deleted.
- The experiment Docker stack (project `swarmexp`) is still running.

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files, session rules, project context in `AGENTS.md`. |
| `docs/project-docs` (#5), `chore/env-prior-work` (#6), `docs/verify-external-stack` | Stacked PRs, each based on the previous one. Merge in that order. |
| `swarm-utils/` (untracked) | Source copy of the project docs, identical to what is now in `docs/`. Not tracked on purpose. |
| `.env.example` | Rewritten for the four providers (this branch). Local `.env` is older: add the new names by hand. |
| `.env` | Local, git-ignored. Keys must be entered by the human. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Exists on `docs/prior-work`. Pin the final commit of `mcp-transactional-agent` (`TODO(verify)`); license is MIT, same author. |
| Application code | None. |

## Next step

T01 (skeleton, config loading, CLI stub, CI with lint, mypy --strict, pytest) on `chore/skeleton`, then T02 (LLM client and budget guard). Both only need the merged docs. T03 and T07 need the experiment stack from `docs/VERIFICATION.md`.

The experiment stack is currently running (`docker ps --filter name=swarmexp`). Stop it with `docker compose -p swarmexp ... down -v` from the external repository when not needed.

## Open questions for the human

- SETUP-10: Groq key for `judge2` and Prompt Guard, or approve a change in the external repository?
- Confirm the track (Multi-Agent Oversight and Control) and the working title.
- 

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
