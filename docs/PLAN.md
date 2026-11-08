# Plan (hour by hour) and Gates

Clock: ART (UTC-3). Written Sun Nov 8, about 04:30 ART. Deadline Mon Nov 9, 08:59 ART. About 28.5 hours remain. Rules: one branch per task, TDD, CI green, human merges every PR. The human approval step is on the critical path: keep PRs small and merge as soon as CI is green.

## Timeline

| When (ART) | Work | Output |
|---|---|---|
| Sun 04:30 to 06:00 | T00 run the external stack and answer every `TODO(verify)`; T01 skeleton; start T02 | `docs/VERIFICATION.md`, repo skeleton |
| Sun 06:00 to 09:00 | T02 LLM client and budget guard; T03 world and ground truth; T04 events and metrics; T05 board and topology | unit-tested modules |
| Sun 09:00 | GATE G1 | end-to-end episode with scripted mock agents, D0 and D1, metrics computed from events and SQL, `docs/MODELS.md` with real model ids, prices and limits |
| Sun 09:00 to 12:00 | T06 agent loop; T07 tool layer; T08 runner; T09 D0/D1 | real-LLM pilot possible |
| Sun 12:00 to 13:00 | T13 pilot (N = 10, 3 to 5 episodes), manipulation check, prompt freeze | pilot report (excluded from analysis) |
| Sun 13:00 | GATE G2 | attack works under D0 (H1 sanity); T14 preregistration tag `prereg-v1` |
| Sun 13:00 to 15:30 | T10 D2; T11 D3; T12 D5; T15 batch runner | all defenses runnable |
| Sun 15:30 | GATE G3 | one episode per defense per topology passes end to end |
| Sun 15:30 to Mon 00:30 | main arm (450 episodes) and controls; T16 analysis on partial data; report skeleton | results/main |
| Sun 18:00 to Mon 00:30 | scale arm in parallel when quotas allow | results/scale |
| Mon 00:30 | GATE G4 | main arm complete, or balanced truncation applied (minimum 20 seeds per cell) |
| Mon 00:30 to 03:00 | frontier substitution arm; adaptive attacker arm; optional D4 and insider variant | results/frontier, results/adaptive |
| Mon 03:00 to 05:00 | final analysis, figures, tables | `results/summary`, figures |
| Mon 05:00 to 05:30 | assemble a complete draft and submit it as insurance (resubmitting with the same title replaces it) | first submission |
| Mon 05:30 to 07:30 | write the report by hand from the outline; appendix; pre-existing declaration; check against RULES.md | final PDF |
| Mon 07:30 | submit final | submission |
| Mon 07:30 to 08:59 | buffer only; no new work; the grace period is not guaranteed | |

## Gates and fallbacks

- G1 fail: cut T10 to T12 scope first (D2 and D5 can wait); never cut the ground truth or the event log.
- G2 fail (attack does not work under D0): adjust the payload templates and agent prompts only before the preregistration tag; if still failing at 14:00, switch the primary framing to "persuasion does not spread in this setup" and report the manipulation check as the main result (still valid, smaller).
- F1 (D3 integration): if the full gateway-worker stack is unstable by 15:00, use the in-process path; record it in the report.
- F2: if D3 cannot run by 17:00, drop D3 from the ladder, state it as not evaluated, and keep D0, D1, D2, D5.
- F3 (quotas): reduce to 20 seeds per cell, balanced across cells.
- F4: drop the frontier arm first, then the adaptive arm, then the scale arm points above N = 50, then D4. Never drop the controls or the preregistration.
- Final rule: from Mon 05:00 onward, no new experiments. Writing and checking only.

## Human-only steps

Merging PRs; verifying model ids and prices in provider consoles; entering API keys into `.env` (never in chat or logs); the pre-hackathon survey (prize eligibility); using the same email for Adaption credits; asking the help-desk about reuse of work from another hackathon; writing the final report text by hand (the organizers recommend rewriting AI-drafted text); submitting on the sprint website.

## Cost watch

Check cumulative spend at each gate against `docs/EXPERIMENT_DESIGN.md` section 6. Stop an arm if its spend exceeds 2x the estimate.
