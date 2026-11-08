# TODO(project title)

TODO(one line)

Work in progress, built during the Swarm Alignment Hackathon 2026.

## Hackathon context

- Event: Swarm Alignment Hackathon (Apart Research sprint), organized by Apart Research with the AI Alignment Foundation and AE Studio. Adaption Labs provides platform credits for participants.
- Format: global online sprint, talks from Thursday, November 5, 2026; sprint Friday, November 6 to Sunday, November 8, 2026.
- Submission deadline: Sunday, November 8, 2026, 11:59 PM AoE (Anywhere on Earth, UTC-12) = Monday, November 9, 2026, 11:59 UTC = Monday, November 9, 2026, 08:59 in Argentina (UTC-3).
- Prizes: USD 4,000 in total. Top teams are invited to the Apart Fellowship.
- Tracks: (1) Sandboxes and testbeds, (2) The science of agent networks, (3) Strengthening agent infrastructure, (4) Multi-agent oversight and control. Selected track(s) for this project: `TODO(track)`.
- Team size: 1 to 5 people. Each person may be on at most two projects.

## Submission requirements

- PDF research report on the official template (Guidelines tab).
- 4 to 8 pages excluding references and appendices (8 is a hard cap).
- Mandatory appendix "Limitations and Dual-Use / Ethical Considerations".
- Disclosure of pre-existing work in both this README and the report.
- AI tools are allowed, but the team is responsible for all content. Fabricated results or references can disqualify the project.

## Official links

| Resource | URL | Verified |
|---|---|---|
| Sprint page | https://apartresearch.com/sprints/swarm-alignment-2026 | from organizer email |
| Overview tab | https://apartresearch.com/sprints/swarm-alignment-2026#overview | from organizer email |
| Resources tab | https://apartresearch.com/sprints/swarm-alignment-2026#resources | from organizer email |
| Guidelines tab (rules, rubric, template, FAQ) | https://apartresearch.com/sprints/swarm-alignment-2026#guidelines | from organizer email |
| Schedule tab (talks and recordings) | https://apartresearch.com/sprints/swarm-alignment-2026#schedule | from organizer email |
| Adaption platform | https://adaptionlabs.ai/app | from organizer email |
| Adaption docs | https://docs.adaptionlabs.ai/ | from organizer email |
| Apart Research Discord | `TODO(link)` | no |
| Discord help-desk channel | `TODO(link)` | no |
| Pre-hackathon survey | `TODO(link)` | no |
| Support email | sprints@apartresearch.com | from organizer email |

Project documents:

- [docs/hackathon/RULES.md](docs/hackathon/RULES.md)
- [docs/hackathon/TALKS_DIGEST.md](docs/hackathon/TALKS_DIGEST.md)

## How this project is judged

- Impact potential and innovation
- Execution quality (methodology, implementation, findings)
- Presentation and clarity

Full rules: docs/hackathon/RULES.md

## Pre-existing work vs work done during the sprint

| Path | Origin | Notes |
|---|---|---|
| `mcp-transactional-agent` (external repository, not copied here) | PRE-EXISTING | Direct dependency and system under test for D1 and D3. Run without modifying its code, configuration only. https://github.com/agustindiazcano/mcp-transactional-agent |
| AFAW (anti-fragile agentic workflow) | PRE-EXISTING | Working method only (branch per task, TDD, CI, human approval). No code used. https://github.com/agustindiazcano/afaw-anti-fragile-agentic-workflow |
| AFAW Engine | PRE-EXISTING | Earlier context. No code used. https://github.com/agustindiazcano/afaw-engine-gitlab |
| Waggle Hive (`waggle-agents-meta-muse`) | PRE-EXISTING | Evaluation conventions only (dangerous error first, Wilson intervals, separate counting units). No code used. https://github.com/agustindiazcano/waggle-agents-meta-muse |

Everything else in this repository was written during the sprint. Details: `docs/hackathon/PRIOR_WORK_DIGEST.md`.

Code written before the sprint is marked PRE-EXISTING here and in the report.

## Repository layout

```
README.md
LICENSE
AGENTS.md                      (agent instructions, single source of truth)
CLAUDE.md                      (symlink to AGENTS.md)
PENDING.md                     (prioritized open tasks)
LASTCONTEXT.md                 (handoff note for the next agent)
.gitignore
.env.example
docs/README.md
docs/hackathon/OVERVIEW.md
docs/hackathon/RESOURCES.md
.github/workflows/ci.yml
.github/pull_request_template.md
```

## Author

Agustin Diaz-Cano
MS Candidate,Systems Engineering
Universidad Tecnologica Nacional, FRBA, Argentina

- University: https://www.frba.utn.edu.ar/
- ORCID: https://orcid.org/0009-0001-4336-490X

## License

MIT, see [LICENSE](LICENSE).

## Reproducibility and AI usage

AI tools were used during development. All results and references are checked by the author before inclusion.

- Tools and models used: `TODO(list of AI tools and versions)`
- How to reproduce results: `TODO(reproduction steps)`
