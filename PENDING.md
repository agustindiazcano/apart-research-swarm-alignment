# PENDING

Prioritized list of open tasks. Read this at the start of every session, together with `LASTCONTEXT.md`. Update it after every finished task (see `AGENTS.md`, "Session protocol").

Last updated: 2026-11-08

## Traffic light

| Light | Meaning |
|---|---|
| 🔴 | Blocking or urgent. Nothing downstream can finish without it. |
| 🟡 | Next. Do it once the blockers are clear. |
| 🟢 | Later. Needed before submission but not blocking now. |
| ⚪ | Backlog. Nice to have, drop first if time runs out. |

## Phase codes

| Code | Phase | Goal |
|---|---|---|
| SETUP | Repository and process | Scaffold, rules, docs, CI, handoff files |
| SCOPE | Problem definition | Title, track, research question, plan |
| BUILD | Implementation | Code, experiments, data collection |
| EVAL | Analysis | Results, figures, checks against the claims |
| REPORT | Writing | PDF report on the official template, 4 to 8 pages plus appendices |
| SUBMIT | Delivery | Final checks and upload before the deadline |

Task IDs are `<PHASE>-<number>`, for example `SCOPE-01`. Never reuse an ID. Moved or finished tasks keep their ID.

Submission deadline: Monday, November 9, 2026, 11:59 UTC (Sunday, November 8, 11:59 PM AoE), which is 08:59 in Argentina (UTC-3).

## Open tasks

Ordered by priority, top first.

| # | Light | ID | Task | Depends on | Status |
|---|---|---|---|---|---|
| 1 | 🔴 | SCOPE-01 | Choose the track(s) and fill `TODO(track)` in `README.md` and `docs/hackathon/OVERVIEW.md` | none | open |
| 2 | 🔴 | SCOPE-02 | Define the project title, the one-line summary and the research question; fill `TODO(title)` and `TODO(one line)` in `README.md` and `AGENTS.md` | SCOPE-01 | open |
| 3 | 🔴 | SETUP-01 | Merge the open PR for `docs/hackathon-rules-and-digest` so the rules and talks digest are on `main` (human approves) | none | open, branch pushed, not merged |
| 4 | 🟡 | SCOPE-03 | Read the Guidelines tab (rubric, template, FAQ) and record the rubric in `docs/hackathon/` | SETUP-01 | open |
| 5 | 🟡 | SCOPE-04 | Write a short plan: method, what counts as a result, what is cut if time runs short | SCOPE-02 | open |
| 6 | 🟡 | BUILD-01 | Implement the experiment or system. Tests first for any code (TDD) | SCOPE-04 | open |
| 7 | 🟡 | SETUP-02 | Fill `TODO(commands)` in `AGENTS.md` once tooling exists | BUILD-01 | open |
| 8 | 🟢 | EVAL-01 | Run the evaluation and produce figures and tables from real outputs only | BUILD-01 | open |
| 9 | 🟢 | REPORT-01 | Draft the report on the official template (4 to 8 pages, 8 is a hard cap) | EVAL-01 | open |
| 10 | 🟢 | REPORT-02 | Write the appendix "Limitations and Dual-Use / Ethical Considerations" | EVAL-01 | open |
| 11 | 🟢 | REPORT-03 | Disclose pre-existing work in the report and update the README pre-existing table | BUILD-01 | open |
| 12 | 🟢 | SUBMIT-01 | Resolve every `TODO(` marker, verify every citation and URL, check CI is green on `main` | REPORT-01, REPORT-02, REPORT-03 | open |
| 13 | 🟢 | SUBMIT-02 | Export the PDF and submit before the deadline | SUBMIT-01 | open |
| 14 | ⚪ | SETUP-03 | Add `PENDING.md` and `LASTCONTEXT.md` to the required-files check in `.github/workflows/ci.yml` | none | open |
| 15 | ⚪ | SETUP-04 | Fill the remaining `TODO(link)` entries in `README.md` (Discord, help desk, survey) | none | open |
| 16 | ⚪ | REPORT-04 | Fill `TODO(list of AI tools and versions)` and `TODO(reproduction steps)` in `README.md` | BUILD-01 | open |

## Done

| ID | Task | Closed in |
|---|---|---|
| SETUP-00 | Project scaffold (README, AGENTS, CI, PR template, docs) | PR #1 |
| SETUP-05 | `PENDING.md` and `LASTCONTEXT.md` handoff files and session rules | branch `chore/agent-handoff-docs` |
