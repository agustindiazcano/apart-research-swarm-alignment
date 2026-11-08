# AGENTS.md

Single source of truth for agent instructions in this repository. `CLAUDE.md` is a symlink to this file.

## Project purpose

This repository holds a project built for the Swarm Alignment Hackathon 2026 (an Apart Research sprint, November 6 to 8, 2026). Project title: `TODO(title)`. The deliverable is a PDF research report plus the code and data that support it.

Rules documents under `docs/` are authoritative and will be added incrementally by the maintainer. When a rules document conflicts with this file, the rules document wins.

## Session protocol

- At the start of every session, read [`PENDING.md`](PENDING.md) (prioritized open tasks, phase codes, traffic light) and [`LASTCONTEXT.md`](LASTCONTEXT.md) (what the previous agent did and what comes next) before doing anything else.
- After finishing every task, update both files in the same task: move the task to "Done" in `PENDING.md`, rewrite `LASTCONTEXT.md` with the latest state, then commit.
- When a task is finished, tell the human and ask for approval to open the PR. Do not open the PR before the human approves.
- Exception to the no-emoji rule: the traffic light symbols in `PENDING.md`.

## Workflow rules

- One branch per task, named `<type>/<short-description>`. Never commit to `main`.
- Atomic commits: each commit holds one logical change that builds and passes CI on its own. Do not mix unrelated changes (for example, code and docs for different tasks) in one commit.
- TDD for any code. This task has no application code, so no tests are needed beyond CI passing.
- Everything must pass CI before a PR is opened. A human approves and merges every PR. Do not merge, do not force-push.
- Documents, code, commits and READMEs are in English.
- Typography: do not use the em dash character anywhere. Use commas, colons or parentheses. No emojis. Avoid filler adjectives (robust, rigorous, seamless, etc.).
- Never invent facts, URLs, citations, versions or results. If a value is unknown, write `TODO(<what is missing>)` and list it in the PR description. Fabricated references can disqualify the project.
- Commit messages: conventional commits (`chore:`, `docs:`).

## Pre-existing vs sprint work policy

Any file not created during the sprint must be listed in the README section "Pre-existing work vs work done during the sprint" with Origin set to PRE-EXISTING. Never delete that marking. Do not modify, move or reformat pre-existing code unless a task explicitly asks for it.

## Hackathon hard constraints

- The report is 4 to 8 pages, excluding references and appendices. 8 pages is a hard cap.
- The report must include the appendix "Limitations and Dual-Use / Ethical Considerations".
- No fabricated results or references.
- Pre-existing work is disclosed in both the README and the report.

## Repository layout

```
README.md
LICENSE
AGENTS.md
CLAUDE.md                      (symlink to AGENTS.md)
PENDING.md
LASTCONTEXT.md
.gitignore
.env.example
docs/README.md
docs/hackathon/OVERVIEW.md
docs/hackathon/RESOURCES.md
.github/workflows/ci.yml
.github/pull_request_template.md
```

## Commands

`TODO(commands)`: no tooling exists yet. The only automated check is the CI workflow in `.github/workflows/ci.yml`.

## Definition of done for a task

- CI is green.
- A PR is opened against `main` and left for human review.
- Docs are updated (README pre-existing table, layout, and any affected document).
