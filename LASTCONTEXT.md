# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Created the local `.env` from `.env.example` (git-ignored). `.gitignore` and `.env.example` already existed and were not changed. The API key is still empty and must be entered by the human.
- Read the project docs (found in untracked `swarm_package.zip`, extracted outside the repo) plus `RULES.md` and `TALKS_DIGEST.md` from branch `docs/hackathon-rules-and-digest`.
- On branch `docs/agent-context`: appended the "Project context: swarm-contagion" section (10 hard invariants, working rules, claims policy) to `AGENTS.md`. PR opened, waiting for the human.
- Did not write any application code and did not start T00.

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files and session rules (PR #1 and PR #3 merged). |
| `docs/agent-context` | This task. PR open for human review. |
| `docs/hackathon-rules-and-digest` | Pushed, not merged (SETUP-01). Holds `RULES.md` and `TALKS_DIGEST.md`. |
| Project docs (`PROJECT`, `EXPERIMENT_DESIGN`, `ARCHITECTURE`, `PLAN`, `TASKS`) | Not in the repo. Only inside untracked `swarm_package.zip`. `AGENTS.md` links to them, so those links are dangling until SETUP-06 is done. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Referenced by `AGENTS.md`, does not exist anywhere yet. |
| Untracked files | `add_docs_prompt.md`, `swarm_package.zip`. Not part of any task. |
| Application code | None. |

## Next step

1. Human merges the `docs/agent-context` PR and the `docs/hackathon-rules-and-digest` PR, and decides SETUP-06 (add the project docs to `docs/`).
2. Then T00: run the external stack (mcp-transactional-agent) and write `docs/VERIFICATION.md`, on branch `docs/verify-external-stack`. T00 needs the external repository checked out locally; its location is not known yet.

## Open questions for the human

- Where is the mcp-transactional-agent repository on this machine, and which commit should be pinned?
- Add the project docs to `docs/` in a PR? And is there a `PRIOR_WORK_DIGEST.md` to add?
- Confirm the track (Multi-Agent Oversight and Control) and the working title.

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Do not put payload templates in public docs, and never put API keys in chat, logs or commits.
