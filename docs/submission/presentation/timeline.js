window.TIMELINE = {
 "total": 182.64,
 "slides": [
  {
   "id": "cover",
   "start": 0.0,
   "end": 11.256,
   "sentences": [
    {
     "start": 0.8,
     "end": 6.608,
     "text": "Infection Chains in LLM Swarms: Spread, Detection and Layered Gating."
    },
    {
     "start": 6.808,
     "end": 11.056,
     "text": "Apart Research Swarm Alignment Hackathon. Agustin Diaz-Cano."
    }
   ]
  },
  {
   "id": "problem",
   "start": 11.256,
   "end": 20.224,
   "sentences": [
    {
     "start": 11.256,
     "end": 14.4,
     "text": "One compromised agent can talk its peers into helping it."
    },
    {
     "start": 14.6,
     "end": 20.024,
     "text": "Monitors that read one message at a time miss it, so we measure the spread and test the defenses."
    }
   ]
  },
  {
   "id": "threat",
   "start": 20.224,
   "end": 39.496,
   "sentences": [
    {
     "start": 20.224,
     "end": 26.224,
     "text": "Ten agents, ten rounds. A 12-character canary is split into three 4-character fragments."
    },
    {
     "start": 26.424,
     "end": 34.32,
     "text": "Each fragment is at least two hops from patient zero, so no single message holds the secret, and patient zero must recruit intermediaries."
    },
    {
     "start": 34.52,
     "end": 39.296,
     "text": "Ring and complete networks, three persuasion styles, one held out from training."
    }
   ]
  },
  {
   "id": "scale",
   "start": 39.496,
   "end": 59.384,
   "sentences": [
    {
     "start": 39.496,
     "end": 50.632,
     "text": "96 real episodes: 3 pilot, 15 training, 78 test, with Gemma 4 31B as the agents and DeepSeek V4 Flash as guardrail model."
    },
    {
     "start": 50.832,
     "end": 59.184,
     "text": "7,944 model calls, under one credit. Preregistered, graded by code, with a 100% agreement audit."
    }
   ]
  },
  {
   "id": "kinetics",
   "start": 59.384,
   "end": 70.032,
   "sentences": [
    {
     "start": 59.384,
     "end": 67.136,
     "text": "The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph."
    },
    {
     "start": 67.336,
     "end": 69.832,
     "text": "Splitting the secret does not stop the spread."
    }
   ]
  },
  {
   "id": "exfil",
   "start": 70.032,
   "end": 82.696,
   "sentences": [
    {
     "start": 70.032,
     "end": 79.824,
     "text": "Split credential: full exfiltration in 1 of 6 ring episodes and 0 of 6 on the complete graph. Solo credential: 3 of 6 and 2 of 6."
    },
    {
     "start": 80.024,
     "end": 82.496,
     "text": "In 30 clean episodes, nothing leaked."
    }
   ]
  },
  {
   "id": "defenses",
   "start": 82.696,
   "end": 118.056,
   "sentences": [
    {
     "start": 82.696,
     "end": 90.64,
     "text": "Now the defenses. A guardrail is a filter that reads every message between agents, and blocks it before delivery if it looks like an attack."
    },
    {
     "start": 90.84,
     "end": 98.832,
     "text": "D1 is the simplest: a word-pattern classifier with no LLM. D2 asks a small LLM to rate each message."
    },
    {
     "start": 99.032,
     "end": 107.864,
     "text": "D3 adds memory: it raises suspicion when the sender was recently flagged. D5 calls the LLM only on unclear messages."
    },
    {
     "start": 108.064,
     "end": 117.856,
     "text": "This ladder is an ablation: each step adds one component, so we can see what the LLM, the context, or the tiering contributes. The control is no guardrail."
    }
   ]
  },
  {
   "id": "guardrails",
   "start": 118.056,
   "end": 143.528,
   "sentences": [
    {
     "start": 118.056,
     "end": 124.728,
     "text": "Result, guardrail by guardrail. With no guardrail, a ring swarm ends with about 6 infected agents of 10."
    },
    {
     "start": 124.928,
     "end": 130.544,
     "text": "With any of the four guardrails, the infection never leaves patient zero: one infected agent."
    },
    {
     "start": 130.744,
     "end": 139.12,
     "text": "The four tie on safety. They differ in cost: D2 and D3 call the LLM on every message, D1 and D5 on none."
    },
    {
     "start": 139.32,
     "end": 143.328,
     "text": "Caveat: six episodes per gate, and a non-adaptive attacker."
    }
   ]
  },
  {
   "id": "results",
   "start": 143.528,
   "end": 165.944,
   "sentences": [
    {
     "start": 143.528,
     "end": 151.568,
     "text": "Offline, AUROC is near 0.998, but the realized false positive rate was 6.4%, not 0.5%."
    },
    {
     "start": 151.768,
     "end": 160.048,
     "text": "Full exfiltration: 0 of 6 gated versus 1 of 6 unprotected, not significant. Utility loss stayed under 0.02."
    },
    {
     "start": 160.248,
     "end": 165.744,
     "text": "No hypothesis is clearly confirmed, and H2 was not identifiable. We report that."
    }
   ]
  },
  {
   "id": "close",
   "start": 165.944,
   "end": 182.64,
   "sentences": [
    {
     "start": 165.944,
     "end": 172.304,
     "text": "Infection chains are measurable, and guardrails contained them in our tests, but at this sample size we claim no more."
    },
    {
     "start": 172.504,
     "end": 181.24,
     "text": "Playbooks stay out of the repository, the canary is synthetic. Next: more seeds, adaptive attackers, mixed-model swarms. Thank you."
    }
   ]
  }
 ]
};
