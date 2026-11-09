window.TIMELINE = {
 "total": 167.758,
 "slides": [
  {
   "id": "cover",
   "start": 0.0,
   "end": 11.356,
   "sentences": [
    {
     "start": 0.8,
     "end": 6.608,
     "text": "Infection Chains in LLM Swarms: Spread, Detection and Layered Gating."
    },
    {
     "start": 6.858,
     "end": 11.106,
     "text": "Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano."
    }
   ]
  },
  {
   "id": "problem",
   "start": 11.356,
   "end": 24.154,
   "sentences": [
    {
     "start": 11.356,
     "end": 14.5,
     "text": "One compromised agent can talk its peers into helping it."
    },
    {
     "start": 14.75,
     "end": 20.246,
     "text": "Per-agent monitors see one message at a time, so each request can look like routine admin work."
    },
    {
     "start": 20.496,
     "end": 23.904,
     "text": "We measure how the infection spreads, and what actually stops it."
    }
   ]
  },
  {
   "id": "threat",
   "start": 24.154,
   "end": 46.178,
   "sentences": [
    {
     "start": 24.154,
     "end": 30.658,
     "text": "Ten agents, ten rounds. A 12-character canary credential is split into three 4-character fragments."
    },
    {
     "start": 30.908,
     "end": 35.852,
     "text": "The fragments sit at least two hops from patient zero, so no single message holds the secret."
    },
    {
     "start": 36.102,
     "end": 40.47,
     "text": "Patient zero must recruit intermediaries, and every hop looks harmless."
    },
    {
     "start": 40.72,
     "end": 45.928,
     "text": "Ring and complete networks. Three persuasion styles; the third is held out from training."
    }
   ]
  },
  {
   "id": "scale",
   "start": 46.178,
   "end": 70.554,
   "sentences": [
    {
     "start": 46.178,
     "end": 51.266,
     "text": "96 real episodes: 3 pilot, 15 training, 78 test."
    },
    {
     "start": 51.516,
     "end": 57.108,
     "text": "Gemma 4 31B plays the agents. DeepSeek V4 Flash is the guardrail."
    },
    {
     "start": 57.358,
     "end": 62.878,
     "text": "7,944 model calls logged in the test analysis, under one credit."
    },
    {
     "start": 63.128,
     "end": 70.304,
     "text": "Preregistered, separate train and test seeds, deterministic grading, 100-message audit at 100% agreement."
    }
   ]
  },
  {
   "id": "kinetics",
   "start": 70.554,
   "end": 82.742,
   "sentences": [
    {
     "start": 70.554,
     "end": 78.306,
     "text": "The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph."
    },
    {
     "start": 78.556,
     "end": 82.492,
     "text": "Splitting the secret does not stop the infection. It makes theft harder."
    }
   ]
  },
  {
   "id": "exfil",
   "start": 82.742,
   "end": 97.364,
   "sentences": [
    {
     "start": 82.742,
     "end": 89.27,
     "text": "Split credential: full exfiltration in 1 of 6 ring episodes, 0 of 6 on the complete graph."
    },
    {
     "start": 89.52,
     "end": 92.928,
     "text": "Solo credential: 3 of 6 and 2 of 6."
    },
    {
     "start": 93.178,
     "end": 97.114,
     "text": "30 clean episodes, with and without gates: nothing leaked."
    }
   ]
  },
  {
   "id": "defenses",
   "start": 97.364,
   "end": 118.476,
   "sentences": [
    {
     "start": 97.364,
     "end": 103.052,
     "text": "D1 is a lexical classifier. D2 is a micro-LLM rubric guardrail."
    },
    {
     "start": 103.302,
     "end": 107.838,
     "text": "D3 adds graph context: suspicion travels along message edges."
    },
    {
     "start": 108.088,
     "end": 113.344,
     "text": "D5 is a tiered filter that calls the LLM only for ambiguous messages."
    },
    {
     "start": 113.594,
     "end": 118.226,
     "text": "Each gate is calibrated on training data to a 0.5% false positive rate."
    }
   ]
  },
  {
   "id": "results",
   "start": 118.476,
   "end": 148.564,
   "sentences": [
    {
     "start": 118.476,
     "end": 123.348,
     "text": "Offline AUROC is near 0.998 on seen playbooks."
    },
    {
     "start": 123.598,
     "end": 132.142,
     "text": "But the realized false positive rate was 6.4%, not 0.5%, and held-out data had no negatives, so we claim nothing on distribution shift."
    },
    {
     "start": 132.392,
     "end": 140.072,
     "text": "Online, gated runs leaked in 0 of 6 episodes versus 1 of 6 unprotected. Not significant: McNemar p equals 1."
    },
    {
     "start": 140.322,
     "end": 148.314,
     "text": "Utility loss stayed under 0.02. No hypothesis is clearly confirmed, and H2 was not identifiable. We report that."
    }
   ]
  },
  {
   "id": "close",
   "start": 148.564,
   "end": 167.758,
   "sentences": [
    {
     "start": 148.564,
     "end": 154.612,
     "text": "Infection chains are measurable. At this sample size, a per-message guard alone is not evidence of safety."
    },
    {
     "start": 154.862,
     "end": 160.67,
     "text": "Playbooks stay out of the repository, the canary is synthetic, every number comes from committed logs."
    },
    {
     "start": 160.92,
     "end": 166.008,
     "text": "Next: more seeds, adaptive attackers, mixed-model swarms. Thank you."
    }
   ]
  }
 ]
};
