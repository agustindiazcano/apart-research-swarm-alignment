# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Branch `docs/no-groq-decision` (worktree `../apart-research-swarm-alignment-wt-no-groq`, based on `main`): recorded the author's decision that Groq is not used. Providers for this project: Apart Research (Adaption), Muse and Vertex (Modal stays in `.env.example`). The judges and the Prompt Guard of the external repo default to Groq in its code; they are remapped in T10 and T11 and declared in `docs/VERIFICATION.md`. Do not ask again about Groq keys.
- PRs #5 to #12 are in `main`. Remove merged chain branches when convenient.
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

- Confirm the track (Multi-Agent Oversight and Control) and the working title.

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
