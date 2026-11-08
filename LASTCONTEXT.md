# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- T00 done on branch `docs/verify-external-stack` (stacked on `chore/env-prior-work`): ran the external stack in an isolated Docker project `swarmexp` and wrote `docs/VERIFICATION.md`.
- Verified by running: compose with the chaos override works after two local config changes (RabbitMQ healthcheck as the `rabbitmq` user, no RabbitMQ volume); claim endpoint `POST /api/v1/claims`; identities `swarm-reader` and `swarm-privileged` (reader gets `DENIED_UNAUTHORIZED` on `execute_refund`, privileged succeeds); `refunds.transaction_id` and `orders.order_id` are both varchar, so no cast in the harm join.
- Corrections to `docs/ARCHITECTURE.md` are listed in `VERIFICATION.md` (tool argument is `transaction_id`; harm query needs no `::text`). They are not applied to `ARCHITECTURE.md` yet.
- Key finding: under `LLM_PROVIDER=mock` every claim is approved, so D2 and D3 need real providers. The judges and Prompt Guard default to Groq, which is not among the planned providers (SETUP-10).
- No file in the external repository was changed. Override file and tokens live in the agent scratchpad, not in the repo.

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files, session rules, project context in `AGENTS.md`. |
| `docs/project-docs` (#5), `chore/env-prior-work` (#6), `docs/verify-external-stack` | Stacked PRs, each based on the previous one. Merge in that order. |
| `swarm-utils/` (untracked) | Source copy of the project docs, identical to what is now in `docs/`. Not tracked on purpose. |
| `.env.example` | Rewritten for the four providers (this branch). Local `.env` is older: add the new names by hand. |
| `.env` | Local, git-ignored. Keys must be entered by the human. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Does not exist; references removed. See REPORT-05. |
| Application code | None. |

## Next step

T01 (skeleton, config loading, CLI stub, CI with lint, mypy --strict, pytest) on `chore/skeleton`, then T02 (LLM client and budget guard). Both only need the merged docs. T03 and T07 need the experiment stack from `docs/VERIFICATION.md`.

The experiment stack is currently running (`docker ps --filter name=swarmexp`). Stop it with `docker compose -p swarmexp ... down -v` from the external repository when not needed.

## Open questions for the human

- SETUP-10: Groq key for `judge2` and Prompt Guard, or approve a change in the external repository?
- Which repositories inspired this work (REPORT-05)?
- Confirm the track (Multi-Agent Oversight and Control) and the working title.
- Merge PRs #5, #6 and the T00 PR in order.

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
