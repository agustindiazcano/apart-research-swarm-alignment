# AGENTS.md

Single source of truth for agent instructions in this repository. `CLAUDE.md` is a symlink to this file.

## Project purpose

This repository holds a project built for the Swarm Alignment Hackathon 2026 (an Apart Research sprint, November 6 to 8, 2026). Project title: `TODO(title)`. The deliverable is a PDF research report plus the code and data that support it.

Rules documents under `docs/` are authoritative and will be added incrementally by the maintainer. When a rules document conflicts with this file, the rules document wins.

## Workflow rules

- One branch per task. For this task: `chore/project-scaffold`. Never commit to `main`.
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
