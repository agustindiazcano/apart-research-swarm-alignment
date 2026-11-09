# Narration script and timings

Total length: 180.8 s

## cover (0.0 s to 11.1 s)

- [0.8] Infection Chains in LLM Swarms: Spread, Detection and Layered Gating.
- [6.1] Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano.

## problem (11.1 s to 25.2 s)

- [11.1] One compromised agent can talk its peers into helping it.
- [14.9] Per-agent monitors see one message at a time, so each request can look like routine admin work.
- [20.8] We measure how the infection spreads, and what actually stops it.

## threat (25.2 s to 49.6 s)

- [25.2] Ten agents, ten rounds. A 12-character canary credential is split into three 4-character fragments.
- [32.5] The fragments sit at least two hops from patient zero, so no single message holds the secret.
- [38.4] Patient zero must recruit intermediaries, and every hop looks harmless.
- [43.3] Ring and complete networks. Three persuasion styles; the third is held out from training.

## scale (49.6 s to 76.7 s)

- [49.6] 96 real episodes: 3 pilot, 15 training, 78 test.
- [55.7] Gemma 4 31B plays the agents. DeepSeek V4 Flash is the guardrail.
- [62.4] 7,944 model calls logged in the test analysis, under one credit.
- [68.6] Preregistered, separate train and test seeds, deterministic grading, 100-message audit at 100% agreement.

## kinetics (76.7 s to 90.1 s)

- [76.7] The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph.
- [85.2] Splitting the secret does not stop the infection. It makes theft harder.

## exfil (90.1 s to 105.7 s)

- [90.1] Split credential: full exfiltration in 1 of 6 ring episodes, 0 of 6 on the complete graph.
- [96.9] Solo credential: 3 of 6 and 2 of 6.
- [101.2] 30 clean episodes, with and without gates: nothing leaked.

## defenses (105.7 s to 126.0 s)

- [105.7] D1 is a lexical classifier. D2 is a micro-LLM rubric guardrail.
- [111.5] D3 adds graph context: suspicion travels along message edges.
- [116.4] D5 is a tiered filter that calls the LLM only for ambiguous messages.
- [121.3] Each gate is calibrated on training data to a 0.5% false positive rate.

## results (126.0 s to 159.3 s)

- [126.0] Offline AUROC is near 0.998 on seen playbooks.
- [131.0] But the realized false positive rate was 6.4%, not 0.5%, and held-out data had no negatives, so we claim nothing on distribution shift.
- [141.0] Online, gated runs leaked in 0 of 6 episodes versus 1 of 6 unprotected. Not significant: McNemar p equals 1.
- [149.9] Utility loss stayed under 0.02. No hypothesis is clearly confirmed, and H2 was not identifiable. We report that.

## close (159.3 s to 180.8 s)

- [159.3] Infection chains are measurable. At this sample size, a per-message guard alone is not evidence of safety.
- [166.4] Playbooks stay out of the repository, the canary is synthetic, every number comes from committed logs.
- [172.8] Next: more seeds, adaptive attackers, mixed-model swarms. Thank you.
