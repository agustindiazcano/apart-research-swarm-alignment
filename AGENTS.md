# AGENTS.md

Single source of truth for agent instructions in this repository. `CLAUDE.md` is a symlink to this file.

## Data Integrity

No result is typed by hand. Every number in the README, in `docs/` and in the report (rates, counts, intervals, R0, AUROC, costs, table cells) is produced by a script from the committed event logs and `gt.json`, and is inserted into the file by a script. Two causes of error are removed this way: transcription mistakes by a person, and numbers produced by an AI model that were never measured.

- Generated content sits between markers: `<!-- RESULTS:BEGIN <name> -->` and `<!-- RESULTS:END <name> -->`. Nothing inside a marked block is edited by hand.
- `scripts/render_results.py` (task T14) reads `results/`, rewrites the marked blocks, and prints the source file and its SHA-256 next to each table.
- A value with no source file is written as `TODO(result)`. It is never an estimate, a rounded memory or a figure copied from chat.
- In prose, refer to a table or figure instead of repeating its numbers. A number that has to appear in prose comes from a generated inline block.
- Before a PR that touches results: run the script and confirm the diff is empty. A CI step that fails when rendering changes a file is added together with the script (T14).
- Agents do not compute a result in chat or in a commit message to paste it into a document.
- Values read from provider consoles (model ids, prices, limits) are copied by the human into `docs/MODELS.md` with the date and the page they came from.

## Project purpose

This repository holds a project built for the Swarm Alignment Hackathon 2026 (an Apart Research sprint, November 6 to 8, 2026). Project title (working): "Infection Chains in LLM Swarms: spread, detection and immunity". The deliverable is a PDF research report plus the code and data that support it.

Rules documents under `docs/` are authoritative and will be added incrementally by the maintainer. When a rules document conflicts with this file, the rules document wins.

## Session protocol

- At the start of every session, read [`PENDING.md`](PENDING.md) (prioritized open tasks, phase codes, traffic light) and [`LASTCONTEXT.md`](LASTCONTEXT.md) (what the previous agent did and what comes next) before doing anything else.
- After finishing every task, update both files in the same task: move the task to "Done" in `PENDING.md`, rewrite `LASTCONTEXT.md` with the latest state, then commit.
- When a task is finished, tell the human and ask for approval to open the PR. Do not open the PR before the human approves.
- Exception to the no-emoji rule: the traffic light symbols in `PENDING.md`.

## Multiple agents, branch and worktree rules

More than one agent works in this project, possibly at the same time, on the same machine. Do not assume anything about the state you find.

- Before any edit, commit or branch operation, check where you are: `git branch --show-current`, `git status -sb` and `git worktree list`. Do this at the start of the session and again before each task. A previous agent or the human may have switched branches, left uncommitted changes or created worktrees.
- Do not assume the checked-out branch is yours or is the one a task needs. Do not assume `main` is up to date: run `git fetch` and compare with `origin/main`. Do not assume a file, branch, container or running service was created by you.
- Never edit, stash, reset, delete or commit changes you did not make (untracked files included). If the working tree has changes you do not recognize, leave them alone and tell the human.
- To avoid collisions, start every task in its own worktree and its own branch: `git worktree add ../<repo>-wt-<task> -b <type>/<short-description> <base>`. Work only inside that worktree. Do not switch branches in a directory another agent may be using.
- Remove your worktree when the PR is merged: `git worktree remove ../<repo>-wt-<task>`. Do not remove worktrees you did not create.
- Shared local resources (Docker projects, ports, containers, volumes, databases) follow the same rule: check what exists before creating or removing anything, use a name that identifies the task, and remove only what you created.
- Record the branch, worktree path and any running service in `LASTCONTEXT.md` so the next agent does not have to guess.

## Delegating tasks to other agents

The coordinator (the agent talking to the human) can run independent tasks of `docs/TASKS.md` in parallel by delegating them to Antigravity (`agy`) and to Claude subagents. Each delegated task has its own worktree and branch created from an up-to-date `origin/main`, and its own prompt.

- Antigravity: use the skill `antigravity` (`.claude/skills/antigravity/SKILL.md`) and the script `scripts/agy_launch.sh`. The command is `agy --dangerously-skip-permissions --model gemini-3.8-flash-high --print "<prompt>"`, run in the background in the human's terminal, without a sandbox. The human authorized this on 2026-11-08 for tasks in separate worktrees only. There is no time limit: the agent finishes the task and the coordinator is notified when the process exits. `agy models` lists the available models; the effort level is part of the model id.
- Claude subagents: use the Agent tool, in the background, with the same preamble as the skill in the prompt and a worktree of their own.
- Delegated agents never push, never open or merge pull requests, and do not edit `AGENTS.md`, `README.md`, `PENDING.md`, `LASTCONTEXT.md`, `pyproject.toml`, `.github/` or `docs/`. While tasks run in parallel, the coordinator updates `PENDING.md` and `LASTCONTEXT.md` after review, so parallel branches do not conflict. This replaces, for delegated tasks only, the rule of updating both files inside each task.
- Review: Antigravity is less capable than Claude. The coordinator reviews every delegated result (diff, tests, `ruff`, `mypy`, the specification, the language rules, the Data Integrity rule) and corrects the errors before a pull request is proposed. Results from Claude subagents are checked by running the same checks.
- Processes: never kill processes by name. Other `agy.exe` processes can be the human's own sessions; identify yours by the start time recorded by the launch script.
- The human approves every pull request. Pull requests are based on `main`.

## Workflow rules

- One branch per task, named `<type>/<short-description>`. Never commit to `main`.
- Atomic commits: each commit holds one logical change that builds and passes CI on its own. Do not mix unrelated changes (for example, code and docs for different tasks) in one commit.
- Every PR is based on `main` (`gh pr create --base main`). Do not stack PRs on top of other feature branches: a PR merged into a feature branch does not reach `main` (this happened with PR #2 and PRs #6 to #10). If a task depends on an unmerged PR, wait for the merge, or open one PR that holds both changes.
- TDD for any code. This task has no application code, so no tests are needed beyond CI passing.
- Everything must pass CI before a PR is opened. A human approves and merges every PR. Do not merge, do not force-push.
- Documents, code, commits and READMEs are in English.
- Typography: do not use the em dash character anywhere. Use commas, colons or parentheses. No emojis (exception: the traffic light symbols in `PENDING.md`).
- Neutral language everywhere: documents, code comments, commit messages, PR text, reports and summaries to the human. State facts, numbers, definitions and sources. Do not write opinions, evaluations, praise, criticism, hype or promotional wording, and do not use intensifying adjectives or adverbs (for example robust, rigorous, seamless, elite, strong, impressive, brilliant, critical, fatal, very, extremely). Describe a limitation by its cause and its size, not with a judgment. Forbidden words: honest, honestly, honesty. A concept that uses one of them is renamed (for example, "honest agent" becomes "standard agent"). CI checks the forbidden words.
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
PENDING.md
LASTCONTEXT.md
.gitignore
.env.example
scripts/render_results.py (planned, T14)
scripts/agy_launch.sh
.claude/skills/antigravity/SKILL.md
docs/README.md
docs/PROJECT.md, EXPERIMENT_DESIGN.md, ARCHITECTURE.md, PLAN.md, TASKS.md, REPORT_OUTLINE.md
docs/hackathon/OVERVIEW.md, RESOURCES.md, RULES.md, TALKS_DIGEST.md, PRIOR_WORK_DIGEST.md
.github/workflows/ci.yml
.github/pull_request_template.md
```

## Commands

`TODO(commands)`: no tooling exists yet. The only automated check is the CI workflow in `.github/workflows/ci.yml`.

## Definition of done for a task

- CI is green.
- A PR is opened against `main` and left for human review.
- Docs are updated (README pre-existing table, layout, and any affected document).

## Project context: swarm-contagion

Goal: measure how an infection spreads through conversations in an LLM swarm (recruitment chains and terminal breaches of a split canary credential), and how well four detectors catch it, offline and as online gates: a lexical logistic regression, a logprob-calibrated micro-LLM guardrail, a graph-contextual cascade and a micro-verifier cascade. Full definitions: `docs/PROJECT.md`, `docs/EXPERIMENT_DESIGN.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/TASKS.md`. Hackathon rules: `docs/hackathon/RULES.md`; talk lessons: `docs/hackathon/TALKS_DIGEST.md`; prior work: `docs/hackathon/PRIOR_WORK_DIGEST.md`.

Deadline: Mon Nov 9, 2026, 08:59 ART (Sun Nov 8, 11:59 PM AoE). Do not plan experiments after Mon 07:00 ART; after that only analysis, writing and checking.

### Hard invariants

1. Ground truth (`gt.json`, labels, holders, patient zero) is never visible to agents or detectors. Agents see only their role prompt, private records, visible board messages and their own tool results. No word like test, simulation, evaluation in agent prompts.
2. Metrics come from the event log and `gt.json` only. Never from agent self-reports or an LLM judgment. One declared exception: the `intent` field of a post is protocol data (a message type chosen from a fixed list); it defines the label L1_action, detectors never see it, and its agreement with the content is checked by hand on a sample and reported.
3. No API key, token or secret in code, logs, event files, commit messages or PR text. Environment variable names only in `.env.example`.
4. Hard spend caps per provider. A missing cap blocks calls. Never remove a cap to make a run pass.
5. Seeds, configs and playbooks are frozen after tag `prereg-v1`. Changes go in the deviations log, not silently in code.
6. No outcome-based exclusion of episodes. Failed episodes are rerun with the same seed (max 2) and then reported as failures.
7. Detectors are fit on TRAIN seeds only. Thresholds are saved before any TEST episode is scored. Playbook style 2 is never used in TRAIN.
8. Playbook texts stay in `experiments/payloads/` and are never copied into public docs or the report.
9. Local, synthetic data and a fake credential only. Nothing touches a real service beyond model-provider APIs.
10. Every reported number comes from committed event logs. No number from memory, from the talks, from the literature or from a synthetic simulation is presented as a result.

### Working rules (author's workflow)

Check the branch and worktrees before acting. One worktree and branch per task. Failing test first, shown failing for the right reason. CI green before a PR. The human approves and merges every PR; ask before opening one. Every PR is based on `main`. Do not push to main. Do not suggest shortcuts that break this workflow. Output language is English. No em dash. No emojis. Neutral language only (see the language rule in `AGENTS.md`).

### Claims policy

Report only what the data show. Do not cite speaker figures from the sprint talks as facts. Cite only references verified by hand. Declare what is pre-existing. A null result is a result. Unknown facts stay `TODO(verify)` until verified by running something.

### Commands (fill in after T01)

```
swarmlab run-episode --config experiments/configs/free_flow.yaml --world-seed 101 --topology ring
swarmlab batch --matrix experiments/configs/free_flow.yaml --resume
swarmlab analyze results/free_flow
swarmlab prereg
```
