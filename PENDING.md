# PENDING

Prioritized list of open tasks. Read this at the start of every session, together with `LASTCONTEXT.md`. Update it after every finished task (see `AGENTS.md`, "Session protocol").

Last updated: 2026-11-09

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

Task IDs T01 to T15 are defined in `docs/TASKS.md`. Status below supersedes previous handoffs. Times use Argentina time (ART).

| Light | ID | Task | Current state |
|---|---|---|---|
| 🔴 | T10 | TRAIN and reported runs | Orchestrator ready on `main`; after `prereg-v1` tag is pushed, run `TRAIN` + detector threshold fitting, then launch parallel TEST campaign before Monday 05:00 ART |
| 🟡 | T11 | Analysis and figures | Run `swarmlab analyze`, `scripts/audit_intent_agreement.py`, `scripts/generate_publication_figures.py`, `scripts/render_results.py`, and `scripts/export_latex_tables.py` on completed campaign logs |
| 🟢 | T15 | Report compilation and submission | Compilers ready on `main`; run `scripts/compile_report.py`, `scripts/build_submission_pdf.py`, and `scripts/verify_submission_package.py` on final rendered results |

Human decisions recorded: Muse cap USD 20, Vertex cap USD 20, Adaption operational cap 500 credits; use Adaption for primary load; playbooks remain outside git; coordinator opens pending PRs after review and green CI, human merges each. These are configuration decisions, not experimental measurements.

## PRs Open (Human Review and Merge)

| PR | Branch | Contents | CI |
|---|---|---|---|
| TBD | chore/prereg-freeze | Set `CallPolicy.backoff_cap_s` to 65.0s and freeze `artifacts/preregistration_manifest.json` and `experiments/PREREGISTRATION.md` (Task T08) | pending |

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
| BUILD-02 | CLI runtime, training and analysis integration | PR #33 |
| T07 | Pilot execution and Gate G2 validation on seeds 901, 902, 903 | PR #41 |
| SETUP-03 | Automated repository hygiene and context checks in CI | PR #45 |
| T14 | Results render manifest and table rendering pipeline | PR #44 |
| T08 | Preregistration manifest freeze and rate-limit backoff resilience | branch `chore/prereg-freeze` |
