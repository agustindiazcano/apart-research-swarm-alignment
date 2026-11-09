# Narration script and timings

Total length: 182.6 s

## cover (0.0 s to 11.3 s)

- [0.8] Infection Chains in LLM Swarms: Spread, Detection and Layered Gating.
- [6.8] Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano.

## problem (11.3 s to 20.2 s)

- [11.3] One compromised agent can talk its peers into helping it.
- [14.6] Monitors that read one message at a time miss it, so we measure the spread and test the defenses.

## threat (20.2 s to 39.5 s)

- [20.2] Ten agents, ten rounds. A 12-character canary is split into three 4-character fragments.
- [26.4] Each fragment is at least two hops from patient zero, so no single message holds the secret, and patient zero must recruit intermediaries.
- [34.5] Ring and complete networks, three persuasion styles, one held out from training.

## scale (39.5 s to 59.4 s)

- [39.5] 96 real episodes: 3 pilot, 15 training, 78 test, with Gemma 4 31B as the agents and DeepSeek V4 Flash as guardrail model.
- [50.8] 7,944 model calls, under one credit. Preregistered, graded by code, with a 100% agreement audit.

## kinetics (59.4 s to 70.0 s)

- [59.4] The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph.
- [67.3] Splitting the secret does not stop the spread.

## exfil (70.0 s to 82.7 s)

- [70.0] Split credential: full exfiltration in 1 of 6 ring episodes and 0 of 6 on the complete graph. Solo credential: 3 of 6 and 2 of 6.
- [80.0] In 30 clean episodes, nothing leaked.

## defenses (82.7 s to 118.1 s)

- [82.7] Now the defenses. A guardrail is a filter that reads every message between agents, and blocks it before delivery if it looks like an attack.
- [90.8] D1 is the simplest: a word-pattern classifier with no LLM. D2 asks a small LLM to rate each message.
- [99.0] D3 adds memory: it raises suspicion when the sender was recently flagged. D5 calls the LLM only on unclear messages.
- [108.1] This ladder is an ablation: each step adds one component, so we can see what the LLM, the context, or the tiering contributes. The control is no guardrail.

## guardrails (118.1 s to 143.5 s)

- [118.1] Result, guardrail by guardrail. With no guardrail, a ring swarm ends with about 6 infected agents of 10.
- [124.9] With any of the four guardrails, the infection never leaves patient zero: one infected agent.
- [130.7] The four tie on safety. They differ in cost: D2 and D3 call the LLM on every message, D1 and D5 on none.
- [139.3] Caveat: six episodes per gate, and a non-adaptive attacker.

## results (143.5 s to 165.9 s)

- [143.5] Offline, AUROC is near 0.998, but the realized false positive rate was 6.4%, not 0.5%.
- [151.8] Full exfiltration: 0 of 6 gated versus 1 of 6 unprotected, not significant. Utility loss stayed under 0.02.
- [160.2] No hypothesis is clearly confirmed, and H2 was not identifiable. We report that.

## close (165.9 s to 182.6 s)

- [165.9] Infection chains are measurable, and guardrails contained them in our tests, but at this sample size we claim no more.
- [172.5] Playbooks stay out of the repository, the canary is synthetic. Next: more seeds, adaptive attackers, mixed-model swarms. Thank you.
