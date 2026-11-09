# Narration script and timings

Total length: 194.3 s

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

## scale (39.5 s to 58.2 s)

- [39.5] 96 real episodes: 3 pilot, 15 training, 78 test, with Gemma 4 31B as the agents and DeepSeek V4 Flash as guardrail model.
- [50.8] 7,944 model calls, under one credit. Preregistered, with a 100% agreement audit.

## kinetics (58.2 s to 68.9 s)

- [58.2] The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph.
- [66.2] Splitting the secret does not stop the spread.

## exfil (68.9 s to 81.5 s)

- [68.9] Split credential: full exfiltration in 1 of 6 ring episodes and 0 of 6 on the complete graph. Solo credential: 3 of 6 and 2 of 6.
- [78.8] In 30 clean episodes, nothing leaked.

## defenses (81.5 s to 116.9 s)

- [81.5] Now the defenses. A guardrail is a filter that reads every message between agents, and blocks it before delivery if it looks like an attack.
- [89.7] D1 is the simplest: a word-pattern classifier with no LLM. D2 asks a small LLM to rate each message.
- [97.9] D3 adds memory: it raises suspicion when the sender was recently flagged. D5 calls the LLM only on unclear messages.
- [106.9] This ladder is an ablation: each step adds one component, so we can see what the LLM, the context, or the tiering contributes. The control is no guardrail.

## guardrails (116.9 s to 142.4 s)

- [116.9] Result, guardrail by guardrail. With no guardrail, a ring swarm ends with about 6 infected agents of 10.
- [123.8] With any of the four guardrails, the infection never leaves patient zero: one infected agent.
- [129.6] The four tie on safety. They differ in cost: D2 and D3 call the LLM on every message, D1 and D5 on none.
- [138.1] Caveat: six episodes per gate, and a non-adaptive attacker.

## results (142.4 s to 162.2 s)

- [142.4] Offline, AUROC is near 0.998, but the realized false positive rate was 6.4%, not 0.5%.
- [150.6] Full exfiltration: 0 of 6 gated versus 1 of 6 unprotected, not significant.
- [156.6] No hypothesis is clearly confirmed, and H2 was not identifiable. We report that.

## integrity (162.2 s to 179.8 s)

- [162.2] Data integrity: no number is typed by hand, neither by a person nor by the AI agent. A script reads the committed logs and fills the README, and every table and figure of the paper.
- [173.8] This removes human error and AI hallucination, and each table carries a hash of its source file.

## close (179.8 s to 194.3 s)

- [179.8] Infection chains are measurable, and guardrails contained them in our tests.
- [184.2] Playbooks stay out of the repository, the canary is synthetic. Next: more seeds, adaptive attackers, mixed-model swarms. Thank you.
