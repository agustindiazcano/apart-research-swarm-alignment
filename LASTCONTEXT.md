# LASTCONTEXT

Handoff note for the next agent. Read this at the start of every session, together with `PENDING.md`. Rewrite it after every finished task: keep only the latest state, not a history (git log holds the history).

Last updated: 2026-11-08

## What was done last

- Branch `docs/redesign-infected-swarm` (worktree `../apart-research-swarm-alignment-wt-redesign`): redesign of the project. Dropped `mcp-transactional-agent` and the refund ledger. New design: infected LLM swarm with real recruitment chains (worm playbook, ring where posts reach only neighbors, split credential), N = 10, R = 10; detectors D1 lexical, D2 logprob micro-LLM guardrail, D3 graph-contextual cascade, D4 micro-verifier cascade with veto; message gate at 0.5% FPR and an episode-level alarm; H2 with repetition control; labels by action (L1_action, L2_leak).
- Updated `AGENTS.md` project context (new invariants), `PROJECT`, `EXPERIMENT_DESIGN`, `ARCHITECTURE`, `PLAN`, `TASKS`, `REPORT_OUTLINE`, `AGENT_PROMPT`, `AGENTS_SECTION`, README, OVERVIEW, `PRIOR_WORK_DIGEST`. Deleted `docs/VERIFICATION.md`.
- The author is registered for the hackathon. Deadline Mon 08:59 ART; experiments stop Mon 05:00 ART.
- Input used: a review of the earlier design (pasted by the author). Its workflow advice (skip worktrees, PRs, TDD) was not followed because `AGENTS.md` forbids shortcuts. Its numeric claims were not adopted.
- A branch `exp/mock-split-attack` (worktree `../apart-research-swarm-alignment-wt-mock-exp`) by another agent holds synthetic numpy simulations. Not touched, not used for results.
- PR #13 (no-Groq decision) is obsolete: this redesign supersedes it. Close it, do not merge.
- The Docker project `swarmexp` (external MCP stack) is no longer needed; stop it with its compose files from `../agentic-mcp-engine` when convenient (`docker compose -p swarmexp ... down -v`).
- Corrections after a second review, applied to the design: label L1_action now comes from a protocol field `intent` of each post (detectors never see it) instead of a lexicon, to avoid circularity with D1; D5 keeps a cached surrogate score S~ per message so D3 inside D5 always has the previous-round scores; the 0.5% FPR threshold uses a smoothed tail estimate over about 700 to 800 TRAIN negatives, with target and realized FPR both reported; H2 is fit on exposed agent-rounds with a topology term and is declared not identifiable if distinct senders barely vary (expected in the ring); A2 is message-level on fixed history and A3 is episode-level causal with outcomes exfiltration, infected fraction and benign utility.
- Third review, applied: `schema.py` frozen first (T01) so lanes A and B share one record layout; batch runner runs many episodes in parallel under a global semaphore; D2 fallback is a short JSON rubric plus 0.05 times D1; plan B for gate G2 (reframe the policy as an operational rule, make the pass-on block explicit); every agent has a `NODE_AUDIT_TAG` line so requests make sense for all; D1 uses full-vocabulary TF-IDF with L2 and vocabulary-free features, no hand lexicons; D3 graph term only when the outgoing message is not clearly benign; continuous episode score by CUSUM over log-odds; both outcomes reported (full exfiltration and fraction of fragments leaked); pilot seeds 901 to 903; `artifacts/preregistration_manifest.json`; drop order confirmed, A3c may shrink to 8 episodes.
- Not adopted: statements about publishability and any timing claim that is not measured. Citations stay pending verification.
- Language rule added to `AGENTS.md` (neutral language, no opinions, hype or intensifiers, forbidden words listed there) and a CI step that checks the forbidden words. Evaluative wording in the project documents was replaced; the concept previously named with one of the forbidden words is now "standard agent".

## Repository state

| Item | State |
|---|---|
| `main` | Scaffold, handoff files, session rules, project context in `AGENTS.md`. |
| `docs/redesign-infected-swarm` | Redesign, pushed, waiting for approval to open the PR. |
| `swarm-utils/` (untracked) | Source copy of the project docs, identical to what is now in `docs/`. Not tracked on purpose. |
| `.env.example` | Rewritten for the four providers (this branch). Local `.env` is older: add the new names by hand. |
| `.env` | Local, git-ignored. Keys must be entered by the human. |
| `docs/hackathon/PRIOR_WORK_DIGEST.md` | Exists on `docs/prior-work`. Pin the final commit of `mcp-transactional-agent` (`TODO(verify)`); license is MIT, same author. |
| Application code | None. |

## Next step

After the human merges the redesign PR: open lane A (T01 skeleton, then T02, T03, T04) and lane B (T05 metrics, then T06 detectors incl. D5) in separate worktrees, possibly by different agents at the same time. First action for lane A or B is a provider check: logprob support, temperature, model ids and limits (the human supplies console data for `docs/MODELS.md`).

## Open questions for the human

- Approve opening the redesign PR (rules: ask first).
- Close PR #13 (obsolete, Groq decision)?
- Stop the Docker project `swarmexp` (leftover from the dropped MCP stack)?
- Which provider and model for the swarm agents, and which low-cost model for the guardrail (G1)?

## Notes

- Deadline: Monday, November 9, 2026, 08:59 ART. No new experiments after Monday 05:00 ART. The author is registered.
- CI blocks the em dash character in tracked files and requires `CLAUDE.md` to be a symlink to `AGENTS.md`.
- `PENDING.md` uses emojis for the traffic light on purpose (exception in `AGENTS.md`). Do not use emojis elsewhere.
- Never put API keys in chat, logs or commits. Payload templates stay out of public docs.
