# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- PR #4 (project context in `AGENTS.md`) is merged.
- Found that PR #2 (rules and talks digest) was merged into `chore/project-scaffold` after PR #1 had already merged, so `RULES.md` and `TALKS_DIGEST.md` never reached `main`. Merged that branch into `docs/project-docs`.
- On branch `docs/project-docs`: copied the project docs from `swarm-utils/` into `docs/` (`PROJECT`, `EXPERIMENT_DESIGN`, `ARCHITECTURE`, `PLAN`, `TASKS`, `REPORT_OUTLINE`, `AGENT_PROMPT`, `AGENTS_SECTION`) and extended the `docs/README.md` index. PR open, waiting for the human.
- Located the external repository: `C:\projects\projects-github-agustindiazcano\agentic-mcp-engine` (git remote is `mcp-transactional-agent`, branch `feat/front-desk-eval`, has `docker-compose.chaos.yml` and `mcp_clients.json`). Not modified.
- No application code written. T00 not started.

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files, session rules, project context in `AGENTS.md`. |
| `docs/project-docs` | This task. PR open for human review. |
| `swarm-utils/` (untracked) | Source copy of the project docs, identical to what is now in `docs/`. Not tracked on purpose. |
| `.env.example` | Modified in the working tree by the human (provider key names added). Not committed by the agent. Commit it as its own task only if the human asks. |
| `.env` | Local, git-ignored. Keys must be entered by the human. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Referenced by `AGENTS.md`, does not exist. |
| Application code | None. |

## Next step

T00 (critical path): run the external stack and write `docs/VERIFICATION.md`, on branch `docs/verify-external-stack` from an up-to-date `main`. Verify every `TODO(verify)` in `docs/ARCHITECTURE.md`. Needs Docker. Do not change code in the external repository, configuration only, and list every change.

## Open questions for the human

- Is it fine to run `docker compose` with the chaos override from `agentic-mcp-engine` (starts Postgres, RabbitMQ, MCP server, gateway, worker locally)? Which commit of that repository should be pinned (it is on `feat/front-desk-eval`, HEAD `37f6d72`)?
- Is there a `PRIOR_WORK_DIGEST.md` to add, or should the references be removed?
- Confirm the track (Multi-Agent Oversight and Control) and the working title.

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
