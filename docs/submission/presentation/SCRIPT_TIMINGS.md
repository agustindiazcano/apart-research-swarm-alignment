# Narration script and timings

Total length: 167.8 s

## cover (0.0 s to 11.4 s)

- [0.8] Infection Chains in LLM Swarms: Spread, Detection and Layered Gating.
- [6.9] Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano.

## problem (11.4 s to 24.2 s)

- [11.4] One compromised agent can talk its peers into helping it.
- [14.8] Per-agent monitors see one message at a time, so each request can look like routine admin work.
- [20.5] We measure how the infection spreads, and what actually stops it.

## threat (24.2 s to 46.2 s)

- [24.2] Ten agents, ten rounds. A 12-character canary credential is split into three 4-character fragments.
- [30.9] The fragments sit at least two hops from patient zero, so no single message holds the secret.
- [36.1] Patient zero must recruit intermediaries, and every hop looks harmless.
- [40.7] Ring and complete networks. Three persuasion styles; the third is held out from training.

## scale (46.2 s to 70.6 s)

- [46.2] 96 real episodes: 3 pilot, 15 training, 78 test.
- [51.5] Gemma 4 31B plays the agents. DeepSeek V4 Flash is the guardrail.
- [57.4] 7,944 model calls logged in the test analysis, under one credit.
- [63.1] Preregistered, separate train and test seeds, deterministic grading, 100-message audit at 100% agreement.

## kinetics (70.6 s to 82.7 s)

- [70.6] The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph.
- [78.6] Splitting the secret does not stop the infection. It makes theft harder.

## exfil (82.7 s to 97.4 s)

- [82.7] Split credential: full exfiltration in 1 of 6 ring episodes, 0 of 6 on the complete graph.
- [89.5] Solo credential: 3 of 6 and 2 of 6.
- [93.2] 30 clean episodes, with and without gates: nothing leaked.

## defenses (97.4 s to 118.5 s)

- [97.4] D1 is a lexical classifier. D2 is a micro-LLM rubric guardrail.
- [103.3] D3 adds graph context: suspicion travels along message edges.
- [108.1] D5 is a tiered filter that calls the LLM only for ambiguous messages.
- [113.6] Each gate is calibrated on training data to a 0.5% false positive rate.

## results (118.5 s to 148.6 s)

- [118.5] Offline AUROC is near 0.998 on seen playbooks.
- [123.6] But the realized false positive rate was 6.4%, not 0.5%, and held-out data had no negatives, so we claim nothing on distribution shift.
- [132.4] Online, gated runs leaked in 0 of 6 episodes versus 1 of 6 unprotected. Not significant: McNemar p equals 1.
- [140.3] Utility loss stayed under 0.02. No hypothesis is clearly confirmed, and H2 was not identifiable. We report that.

## close (148.6 s to 167.8 s)

- [148.6] Infection chains are measurable. At this sample size, a per-message guard alone is not evidence of safety.
- [154.9] Playbooks stay out of the repository, the canary is synthetic, every number comes from committed logs.
- [160.9] Next: more seeds, adaptive attackers, mixed-model swarms. Thank you.
