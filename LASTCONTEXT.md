# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Added `PENDING.md`: prioritized task list with phase codes (SETUP, SCOPE, BUILD, EVAL, REPORT, SUBMIT) and a traffic light system.
- Added this file.
- Updated `AGENTS.md`: session protocol (read both files first, update both and commit after each task), atomic commits rule, and the rule to ask the human to approve a PR when a task is finished.
- Work was done on branch `chore/agent-handoff-docs`, branched from `main`.

## Repository state

| Item | State |
|---|---|
| `main` | Has the scaffold (PR #1 merged). Does not have the hackathon rules and talks digest. |
| `docs/hackathon-rules-and-digest` | Pushed, not merged into `main`. Tracked as SETUP-01. |
| `chore/agent-handoff-docs` | This task. PR opened for human review. |
| Untracked `add_docs_prompt.md` | Not committed, not part of any task. Leave it alone unless asked. |
| Project title and track | Not decided (`TODO(title)`, `TODO(track)`). |
| Application code | None yet. |

## Next step

Top of `PENDING.md`: SCOPE-01 (choose the track) and SCOPE-02 (title and research question). Both need a decision from the human.

## Open questions for the human

- Which track(s) and which research question?
- Approve and merge the PR for this task, then the PR for `docs/hackathon-rules-and-digest`.

## Notes

- The deadline is Monday, November 9, 2026, 11:59 UTC (08:59 in Argentina). Check the date before planning.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
