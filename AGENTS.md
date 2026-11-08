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

## Research standards for this project

- Rubric awareness: work is judged on impact and innovation, execution quality, and presentation clarity. Replicating recent work without a new contribution scores low on the first dimension.
- Claims policy: figures from talks are speaker claims. Never cite them as facts in the report. Cite primary sources only after they are verified. Never invent references, numbers or results.
- Experiment design minimums: state the threat model first; include a no-attack control and a baseline without our intervention; fix N per condition before running; define metrics before running; report confidence intervals; log any deviation from the plan.
- Grading: prefer deterministic graders. If an LLM judge is used, store its rubric and spot-check outputs by hand.
- Data handling: keep results in a database or structured files with a schema, not in ad hoc text dumps. Vet any crawled data before publishing.
- Dual-use: use local, toy-sized environments only. Do not target real infrastructure. Do not publish optimized attacker prompts or exploit scripts. When in doubt, ask the maintainer before committing material to a public repository.
- External code: record source, commit hash and license, and mark it EXTERNAL in the README table. Pre-sprint code is marked PRE-EXISTING. Only sprint work is claimed as new.
- Writing: the report must be clear to a reader who has not seen the code. No padding. Text produced with AI assistance is reviewed and rewritten by the maintainer before submission.
- Source of truth: docs/hackathon/RULES.md and docs/hackathon/TALKS_DIGEST.md. The Guidelines tab of the sprint page prevails over both.

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
