# PENDING

Prioritized list of open tasks. Read this at the start of every session, together with `LASTCONTEXT.md`. Update it after every finished task (see `AGENTS.md`, "Session protocol").

Last updated: 2026-11-08

## Traffic light

| Light | Meaning |
|---|---|
| 🔴 | Blocking or urgent. Nothing downstream can finish without it. |
| 🟡 | Next. Do it once the blockers are clear. |
| 🟢 | Later. Needed before submission but not blocking now. |
| ⚪ | Backlog. Optional; dropped first if time runs out. |

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

Task IDs T01 to T15 are defined in `docs/TASKS.md`. Status below supersedes the previous coordinator handoff. Times use Argentina time (ART).

| Light | ID | Task | Current state |
|---|---|---|---|
| 🔴 | T03 | World generator | PR #22 open against main; human review and merge |
| 🔴 | T02 | LLM budget, limiter and mock | PR #25 open, CI passed; per-result cost and budget review complete |
| 🔴 | T05 | Events and extraction | PR #28 open; fragment, clean-arm, offspring and unknown-retry corrections validated |
| 🔴 | T06 | Lexical and guardrail detectors | PRs #26 and #27 open; CI passed |
| 🔴 | T04 | Swarm and prompts | PR #30 open, CI passed; combines swarm and prompts with world dependency |
| 🔴 | G1 | Provider record and execution configuration | PR #24 open; Adaption credit prices verified, unit conversion and quotas TODO(verify) |
| 🔴 | BUILD-01 | Real provider adapters | PR #29 open, CI passed; coordinator reran mock tests, no real calls |
| 🔴 | BUILD-02 | CLI integration and end-to-end mock episode | In progress on `feat/runtime-cli`; commands, budget aborts, logs and clean arms |
| 🔴 | BUILD-03 | TRAIN and offline scoring pipeline | In progress on `feat/training-pipeline`; episode calibration, frozen thresholds, D3 and D5 |
| 🔴 | BUILD-04 | Unit-aware provider billing | PR #31 open, CI passed; Adaption costs remain in credits |
| 🟡 | T07 | Pilot and model choice | Draft pilot and main configs prepared on integration branch; primary load on Adaption, model choice still requires pilot |
| 🟡 | T08 | Preregistration and human tag | Manifest generator merged; freeze after pilot |
| 🟡 | T10 | TRAIN and reported runs | After pilot and preregistration; no new experiments after Monday 05:00 ART |
| 🟡 | T11 | Analysis and figures | Plots PR #23 open, CI passed; `feat/analysis-pipeline` in progress |
| 🟢 | T14 | Reproduction instructions and report assets | Renderer merged; end-to-end reproduction instructions pending |
| 🟢 | T15 | Report, rules and submission | Human-written report and appendix; deadline Monday 08:59 ART |
| ⚪ | T12 | D4 micro-verifiers | Backlog |
| ⚪ | T13 | Immunity | Backlog; finite offspring means do not establish an immunity threshold |
| ⚪ | SETUP-03 | Require context files in CI | Open |

Human decisions recorded this session: Muse cap USD 20, Vertex cap USD 20, Adaption operational cap 500 credits (explicitly supersedes USD 500 for Adaption); use Adaption for primary load; playbooks remain outside git; coordinator opens pending PRs after review and green CI, human merges each. These are configuration decisions, not experimental measurements.

## Done

| ID | Task | Closed in |
|---|---|---|
| SETUP-00 | Project scaffold (README, AGENTS, CI, PR template, docs) | PR #1 |
| SETUP-05 | `PENDING.md` and `LASTCONTEXT.md` handoff files and session rules | PR #3 |
| SETUP-07 | Local `.env` created from `.env.example` (git-ignored); `.gitignore` and `.env.example` already existed | local only, no commit |
| SETUP-01 | Rules and talks digest on `main` (PR #2 had been merged into the scaffold branch after PR #1, so it never reached `main`) | branch `docs/project-docs` |
| SETUP-06 | Project docs (`PROJECT`, `EXPERIMENT_DESIGN`, `ARCHITECTURE`, `PLAN`, `TASKS`, `REPORT_OUTLINE`, prompts) added to `docs/` | branch `docs/project-docs` |
| T00 | Verify the external stack and write `docs/VERIFICATION.md` | branch `docs/verify-external-stack` |
| REPORT-05 | Prior work named; `docs/hackathon/PRIOR_WORK_DIGEST.md` written, README pre-existing table filled, references restored | branch `docs/prior-work` |
| SETUP-11 | Multi-agent rule in `AGENTS.md`: check branch and worktrees first, assume nothing, one worktree and branch per task | branch `docs/multi-agent-rule` |
| SETUP-13 | Rule in `AGENTS.md`: every PR is based on `main`, no stacked PRs | branch `docs/pr-base-main-rule` |
| SETUP-14 | Content of stacked PRs #6 to #10 brought to `main` | PR #11 |
| SETUP-12 | Removed the Discord, help-desk and survey `TODO(link)` rows from the README links table (SETUP-04 dropped) | branch `docs/readme-remove-todo-links` |
| SETUP-15 | Neutral language rule in `AGENTS.md`, CI check for forbidden words, evaluative wording removed from the project documents | branch `docs/redesign-infected-swarm` |
| SETUP-16 | Data Integrity section at the top of `README.md` and `AGENTS.md`: results are generated and inserted by script, never typed by hand; marked result blocks in the README | branch `docs/redesign-infected-swarm` |
| SETUP-10 | Decision: Groq is not used. Superseded by the redesign: the MCP judge pipeline it applied to is not part of the new design | PR #13 |
| SETUP-09 | `PRIOR_WORK_DIGEST.md` references removed; `.env.example` reduced to Adaption, Vertex, Muse and Modal plus per-provider budget caps | branch `chore/env-prior-work` |
| SETUP-08 | Project context section (hard invariants, claims policy) appended to `AGENTS.md` | PR #4 |

| T01 | Package skeleton, schema and Python CI | PR #15 merged |
| T05a | Statistics module | PR #16 merged |
| T09 | Batch runner | PR #17 merged |
| T08a | Preregistration manifest generator | PR #18 merged |
| T14a | Result renderer | PR #19 merged |
| SETUP-17 | Delegation skill and launch helper | PR #20 merged |
| BUILD-REVIEW-01 | Audit LLM, extraction, lexical and guardrail branches | Corrected on dedicated review branches; PR and integration state above |

Campaign accounting: coordinator integration branch `chore/integration-check` adds a shared persistent ledger and a successful-response audit hook before budget aborts. CLI, TRAIN and analysis integration remain in progress. Docker Desktop was stopped at the maintainer request; the Python runtime does not require it.

| BUILD-PLAN-01 | Draft seed matrices, provider credit configurations and recursive preregistration hashes | Prepared and validated on chore/integration-check; pilot and tag not run |
