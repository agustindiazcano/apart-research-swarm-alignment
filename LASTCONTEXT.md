# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Docker Desktop was stopped; started it (daemon 29.8.0 is running). T00 not started yet.
- On branch `chore/env-prior-work` (stacked on `docs/project-docs`, PR #5 not merged yet): removed the `PRIOR_WORK_DIGEST.md` references from `AGENTS.md`, `docs/AGENTS_SECTION.md` and `docs/AGENT_PROMPT.md` (REPORT-05 tracks writing it later); rewrote `.env.example` for Adaption, Vertex, Muse and Modal only.
- `.env.example` now also has `*_BUDGET_USD` names per provider. I chose those names; T02 (BudgetGuard) may rename them.
- Provider usage was read from `../software-ai-eval` (docs/MODELS.md, config/models.example.yaml, README). Facts found: Vertex uses ADC plus `GOOGLE_CLOUD_PROJECT` and location `global`; Muse uses `META_MUSE_API_KEY`, base URL `https://api.meta.ai/v1`, Responses protocol; Adaption uses `ADAPTION_API_KEY` with the `adaption` SDK. Modal: the current `models.yaml` has no Modal entry, so the variable names and endpoint stay `TODO(verify)`.

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files, session rules, project context in `AGENTS.md`. |
| `docs/project-docs` | This task. PR open for human review. |
| `swarm-utils/` (untracked) | Source copy of the project docs, identical to what is now in `docs/`. Not tracked on purpose. |
| `.env.example` | Rewritten for the four providers (this branch). Local `.env` is older: add the new names by hand. |
| `.env` | Local, git-ignored. Keys must be entered by the human. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Does not exist; references removed. See REPORT-05. |
| Application code | None. |

## Next step

T00 (critical path): run the external stack and write `docs/VERIFICATION.md`, on branch `docs/verify-external-stack` from an up-to-date `main`. Verify every `TODO(verify)` in `docs/ARCHITECTURE.md`. Needs Docker. Do not change code in the external repository, configuration only, and list every change.

## Open questions for the human

- Is it fine to run `docker compose` with the chaos override from `agentic-mcp-engine` (starts Postgres, RabbitMQ, MCP server, gateway, worker locally)? Which commit of that repository should be pinned (it is on `feat/front-desk-eval`, HEAD `37f6d72`)?
- Which repositories inspired this work (REPORT-05)?
- Confirm the track (Multi-Agent Oversight and Control) and the working title.

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
