window.TIMELINE = {
 "total": 180.824,
 "slides": [
  {
   "id": "cover",
   "start": 0.0,
   "end": 11.074,
   "sentences": [
    {
     "start": 0.8,
     "end": 5.899,
     "text": "Infection Chains in LLM Swarms: Spread, Detection and Layered Gating."
    },
    {
     "start": 6.149,
     "end": 10.824,
     "text": "Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano."
    }
   ]
  },
  {
   "id": "problem",
   "start": 11.074,
   "end": 25.205,
   "sentences": [
    {
     "start": 11.074,
     "end": 14.688,
     "text": "One compromised agent can talk its peers into helping it."
    },
    {
     "start": 14.938,
     "end": 20.596,
     "text": "Per-agent monitors see one message at a time, so each request can look like routine admin work."
    },
    {
     "start": 20.846,
     "end": 24.955,
     "text": "We measure how the infection spreads, and what actually stops it."
    }
   ]
  },
  {
   "id": "threat",
   "start": 25.205,
   "end": 49.585,
   "sentences": [
    {
     "start": 25.205,
     "end": 32.295,
     "text": "Ten agents, ten rounds. A 12-character canary credential is split into three 4-character fragments."
    },
    {
     "start": 32.545,
     "end": 38.176,
     "text": "The fragments sit at least two hops from patient zero, so no single message holds the secret."
    },
    {
     "start": 38.426,
     "end": 43.086,
     "text": "Patient zero must recruit intermediaries, and every hop looks harmless."
    },
    {
     "start": 43.336,
     "end": 49.335,
     "text": "Ring and complete networks. Three persuasion styles; the third is held out from training."
    }
   ]
  },
  {
   "id": "scale",
   "start": 49.585,
   "end": 76.745,
   "sentences": [
    {
     "start": 49.585,
     "end": 55.448,
     "text": "96 real episodes: 3 pilot, 15 training, 78 test."
    },
    {
     "start": 55.698,
     "end": 62.132,
     "text": "Gemma 4 31B plays the agents. DeepSeek V4 Flash is the guardrail."
    },
    {
     "start": 62.382,
     "end": 68.302,
     "text": "7,944 model calls logged in the test analysis, under one credit."
    },
    {
     "start": 68.552,
     "end": 76.495,
     "text": "Preregistered, separate train and test seeds, deterministic grading, 100-message audit at 100% agreement."
    }
   ]
  },
  {
   "id": "kinetics",
   "start": 76.745,
   "end": 90.143,
   "sentences": [
    {
     "start": 76.745,
     "end": 84.95,
     "text": "The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph."
    },
    {
     "start": 85.2,
     "end": 89.893,
     "text": "Splitting the secret does not stop the infection. It makes theft harder."
    }
   ]
  },
  {
   "id": "exfil",
   "start": 90.143,
   "end": 105.701,
   "sentences": [
    {
     "start": 90.143,
     "end": 96.623,
     "text": "Split credential: full exfiltration in 1 of 6 ring episodes, 0 of 6 on the complete graph."
    },
    {
     "start": 96.873,
     "end": 100.912,
     "text": "Solo credential: 3 of 6 and 2 of 6."
    },
    {
     "start": 101.162,
     "end": 105.451,
     "text": "30 clean episodes, with and without gates: nothing leaked."
    }
   ]
  },
  {
   "id": "defenses",
   "start": 105.701,
   "end": 126.021,
   "sentences": [
    {
     "start": 105.701,
     "end": 111.2,
     "text": "D1 is a lexical classifier. D2 is a micro-LLM rubric guardrail."
    },
    {
     "start": 111.45,
     "end": 116.128,
     "text": "D3 adds graph context: suspicion travels along message edges."
    },
    {
     "start": 116.378,
     "end": 121.012,
     "text": "D5 is a tiered filter that calls the LLM only for ambiguous messages."
    },
    {
     "start": 121.262,
     "end": 125.771,
     "text": "Each gate is calibrated on training data to a 0.5% false positive rate."
    }
   ]
  },
  {
   "id": "results",
   "start": 126.021,
   "end": 159.309,
   "sentences": [
    {
     "start": 126.021,
     "end": 130.784,
     "text": "Offline AUROC is near 0.998 on seen playbooks."
    },
    {
     "start": 131.034,
     "end": 140.766,
     "text": "But the realized false positive rate was 6.4%, not 0.5%, and held-out data had no negatives, so we claim nothing on distribution shift."
    },
    {
     "start": 141.016,
     "end": 149.674,
     "text": "Online, gated runs leaked in 0 of 6 episodes versus 1 of 6 unprotected. Not significant: McNemar p equals 1."
    },
    {
     "start": 149.924,
     "end": 159.059,
     "text": "Utility loss stayed under 0.02. No hypothesis is clearly confirmed, and H2 was not identifiable. We report that."
    }
   ]
  },
  {
   "id": "close",
   "start": 159.309,
   "end": 180.824,
   "sentences": [
    {
     "start": 159.309,
     "end": 166.127,
     "text": "Infection chains are measurable. At this sample size, a per-message guard alone is not evidence of safety."
    },
    {
     "start": 166.377,
     "end": 172.585,
     "text": "Playbooks stay out of the repository, the canary is synthetic, every number comes from committed logs."
    },
    {
     "start": 172.835,
     "end": 179.074,
     "text": "Next: more seeds, adaptive attackers, mixed-model swarms. Thank you."
    }
   ]
  }
 ]
};
