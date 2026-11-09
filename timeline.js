window.TIMELINE = {
 "total": 194.296,
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
   "end": 58.208,
   "sentences": [
    {
     "start": 39.496,
     "end": 50.632,
     "text": "96 real episodes: 3 pilot, 15 training, 78 test, with Gemma 4 31B as the agents and DeepSeek V4 Flash as guardrail model."
    },
    {
     "start": 50.832,
     "end": 58.008,
     "text": "7,944 model calls, under one credit. Preregistered, with a 100% agreement audit."
    }
   ]
  },
  {
   "id": "kinetics",
   "start": 58.208,
   "end": 68.856,
   "sentences": [
    {
     "start": 58.208,
     "end": 65.96,
     "text": "The infection spreads: by round nine, 6 to 6.5 of 10 agents are infected on a ring, 4.5 on the complete graph."
    },
    {
     "start": 66.16,
     "end": 68.656,
     "text": "Splitting the secret does not stop the spread."
    }
   ]
  },
  {
   "id": "exfil",
   "start": 68.856,
   "end": 81.52,
   "sentences": [
    {
     "start": 68.856,
     "end": 78.648,
     "text": "Split credential: full exfiltration in 1 of 6 ring episodes and 0 of 6 on the complete graph. Solo credential: 3 of 6 and 2 of 6."
    },
    {
     "start": 78.848,
     "end": 81.32,
     "text": "In 30 clean episodes, nothing leaked."
    }
   ]
  },
  {
   "id": "defenses",
   "start": 81.52,
   "end": 116.88,
   "sentences": [
    {
     "start": 81.52,
     "end": 89.464,
     "text": "Now the defenses. A guardrail is a filter that reads every message between agents, and blocks it before delivery if it looks like an attack."
    },
    {
     "start": 89.664,
     "end": 97.656,
     "text": "D1 is the simplest: a word-pattern classifier with no LLM. D2 asks a small LLM to rate each message."
    },
    {
     "start": 97.856,
     "end": 106.688,
     "text": "D3 adds memory: it raises suspicion when the sender was recently flagged. D5 calls the LLM only on unclear messages."
    },
    {
     "start": 106.888,
     "end": 116.68,
     "text": "This ladder is an ablation: each step adds one component, so we can see what the LLM, the context, or the tiering contributes. The control is no guardrail."
    }
   ]
  },
  {
   "id": "guardrails",
   "start": 116.88,
   "end": 142.352,
   "sentences": [
    {
     "start": 116.88,
     "end": 123.552,
     "text": "Result, guardrail by guardrail. With no guardrail, a ring swarm ends with about 6 infected agents of 10."
    },
    {
     "start": 123.752,
     "end": 129.368,
     "text": "With any of the four guardrails, the infection never leaves patient zero: one infected agent."
    },
    {
     "start": 129.568,
     "end": 137.944,
     "text": "The four tie on safety. They differ in cost: D2 and D3 call the LLM on every message, D1 and D5 on none."
    },
    {
     "start": 138.144,
     "end": 142.152,
     "text": "Caveat: six episodes per gate, and a non-adaptive attacker."
    }
   ]
  },
  {
   "id": "results",
   "start": 142.352,
   "end": 162.248,
   "sentences": [
    {
     "start": 142.352,
     "end": 150.392,
     "text": "Offline, AUROC is near 0.998, but the realized false positive rate was 6.4%, not 0.5%."
    },
    {
     "start": 150.592,
     "end": 156.352,
     "text": "Full exfiltration: 0 of 6 gated versus 1 of 6 unprotected, not significant."
    },
    {
     "start": 156.552,
     "end": 162.048,
     "text": "No hypothesis is clearly confirmed, and H2 was not identifiable. We report that."
    }
   ]
  },
  {
   "id": "integrity",
   "start": 162.248,
   "end": 179.808,
   "sentences": [
    {
     "start": 162.248,
     "end": 173.6,
     "text": "Data integrity: no number is typed by hand, neither by a person nor by the AI agent. A script reads the committed logs and fills the README, and every table and figure of the paper."
    },
    {
     "start": 173.8,
     "end": 179.608,
     "text": "This removes human error and AI hallucination, and each table carries a hash of its source file."
    }
   ]
  },
  {
   "id": "close",
   "start": 179.808,
   "end": 194.296,
   "sentences": [
    {
     "start": 179.808,
     "end": 183.96,
     "text": "Infection chains are measurable, and guardrails contained them in our tests."
    },
    {
     "start": 184.16,
     "end": 192.896,
     "text": "Playbooks stay out of the repository, the canary is synthetic. Next: more seeds, adaptive attackers, mixed-model swarms. Thank you."
    }
   ]
  }
 ]
};
