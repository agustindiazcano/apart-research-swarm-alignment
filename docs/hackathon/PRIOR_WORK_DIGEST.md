# Prior work digest

Status: updated 2026-11-08 from the author's own list. This is the source for the pre-existing work declaration in the README and in the report. Rule: building on existing work is allowed; it must be disclosed in both places (see `RULES.md`, section 4). Only sprint work is judged.

All items are earlier work by the same author (Agustin Diaz-Cano), who owns the repositories.

## Declared prior work

| Name | Link | Relation to this project | What is reused |
|---|---|---|---|
| AFAW (anti-fragile agentic workflow) | https://github.com/agustindiazcano/afaw-anti-fragile-agentic-workflow | Working method | Method only: branch per task, TDD, CI, human approval. No code is copied. |
| AFAW Engine | https://github.com/agustindiazcano/afaw-engine-gitlab and https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43344247/showcase | Earlier context | Context of previous work. No code is used. |
| Waggle Hive (`waggle-agents-meta-muse`) | https://github.com/agustindiazcano/waggle-agents-meta-muse | Evaluation conventions | Conventions only: report the dangerous error first, Wilson intervals, separate counting units. No code is used. |
| `software-ai-eval` | local project of the author | Provider configuration facts | Endpoints and authentication variable names for Vertex, Muse, Modal and Adaption were read from it. No code is copied. |

## Dropped

`mcp-transactional-agent` was considered as the system under test and was dropped on 2026-11-08. It is not used in this project.

## Disclosure text to reuse

> Pre-existing work by the same author, disclosed here: the AFAW working method and the Waggle Hive evaluation conventions are reused as methods, and provider configuration facts were read from an earlier evaluation project. No code from AFAW, AFAW Engine, Waggle Hive or that project is used. All code in this repository was written during the sprint.

## Not claimed

- No result, figure or text from the earlier projects is presented as sprint work.
- Synthetic numpy simulations made by another agent on a separate branch are not results and are not part of the submission unless clearly labeled as analytical priors.
- Whether reuse of work from another hackathon has restrictions is an open question for the Discord help-desk.
