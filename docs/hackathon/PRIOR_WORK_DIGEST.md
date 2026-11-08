# Prior work digest

Status: written 2026-11-08 from the author's own list. This is the source for the pre-existing work declaration in the README and in the report. Rule: building on existing work is allowed; it must be disclosed in both places (see `RULES.md`, section 4). Only sprint work is judged.

All four items are earlier work by the same author (Agustin Diaz-Cano), who owns all four repositories. `mcp-transactional-agent` is under the MIT license (stated by the author; matches the MIT badge in its README).

## Declared prior work

| Name | Link | Relation to this project | What is reused |
|---|---|---|---|
| AFAW (anti-fragile agentic workflow) | https://github.com/agustindiazcano/afaw-anti-fragile-agentic-workflow | Working method | Method only: branch per task, TDD, CI, human approval. No code is copied. |
| AFAW Engine | https://github.com/agustindiazcano/afaw-engine-gitlab and https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43344247/showcase | Earlier context | Context of previous work. No code is used. |
| Waggle Hive (`waggle-agents-meta-muse`) | https://github.com/agustindiazcano/waggle-agents-meta-muse | Evaluation conventions | Conventions only: report the dangerous error first, Wilson intervals, separate counting units. No code is used. |
| `mcp-transactional-agent` | https://github.com/agustindiazcano/mcp-transactional-agent | Direct dependency, system under test for D1 and D3 | The whole repository, run without modifying its code; only configuration changes. |

## How `mcp-transactional-agent` is used

- Pre-existing and external to this repository. It is run as a separate Docker Compose stack; nothing from it is copied here.
- Code changes: none. Configuration changes only (compose override, MCP client registry entries). Every change is listed in `docs/VERIFICATION.md`, section 8.
- Version verified on 2026-11-08: branch `feat/front-desk-eval`, commit `37f6d72`. `TODO(verify)`: pin the exact commit used for the final runs.
- License: MIT. The author owns the repository.
- Role in the experiment: the MCP security boundary (identity-based tool permissions) is the defense under test in D1; the claim pipeline (evidence check, judges, deterministic executor) is the defense under test in D3.

## Disclosure text to reuse

Short form for the README and the report:

> Pre-existing work by the same author, disclosed here: `mcp-transactional-agent` is used unmodified as the system under test (configuration only). The AFAW working method and the Waggle Hive evaluation conventions are reused as methods; no code from AFAW, AFAW Engine or Waggle Hive is used. All other code in this repository was written during the sprint.

## Not claimed

- No result, figure or text from the earlier projects is presented as sprint work.
- No code from AFAW, AFAW Engine or Waggle Hive is copied or adapted.
- Whether reuse of work from another hackathon has restrictions is an open question for the Discord help-desk (see `PROJECT.md`, section 7).
