# Talks Digest: what is useful for this project

Status: compiled on 2026-11-08 from transcripts of the sprint talks. Rules:

- Everything below is attributed to the speaker. Figures are speaker claims. Do not cite them as established facts in the report until the primary paper or report is checked.
- Model names in the transcripts were produced by speech-to-text and several are garbled. Do not reuse them.
- URLs named in talks are listed as "named in talk" and must be verified before linking.

## 1. Adaption workshop (Ben Allan-Rahill, Adaption)

Content: dataset invention from a prompt, dataset expansion and localization, AutoScientist fine-tuning, and a new inference service ("stacks") that serves open-source models through an API compatible with the OpenAI Responses format, with optional remote MCP connections.

Useful:
- Timing: inventing a small dataset took on the order of 20 to 25 minutes with queueing; AutoScientist training takes a couple of hours. Plan for one or two iterations at most.
- Win-rate is computed on a held-out sample of about 200 items with an LLM judge, against the base model. Custom judge rubrics are possible.
- Column mapping (prompt, completion, context) can be inferred wrongly. Check by hand.
- Automatic augmentation adds data from the platform pool and costs credits. If used, declare it and consider an ablation.
- The speaker suggested training a small monitor on synthetic transcripts and comparing it to a frontier model on cost and latency.

Caveat: the platform and docs are in beta and may be outdated. Verify model IDs and endpoints from the account or SDK. In-distribution win-rate on synthetic data does not measure detection ability; a monitor needs labeled ground truth and an independent test set.

## 2. Open problems in securing systems against agent swarms (John Kitaoka, MATS and UK AISI)

Content (unpublished work, speaker claims): attacks split across several agents evade per-trajectory monitors. With 16 handcrafted attacks on lab-like infrastructure, a single-agent trajectory monitor caught about 82%, while split attacks monitored per agent were caught about 3% of the time, and about 40% even when the monitor saw all agents together. Thresholds were calibrated to about 1% false positives.

Useful:
- Two open problems he proposed: (1) a monitor that identifies which agents act toward a shared goal, for example per-action relevance scores correlated across agents; (2) understanding the gap between solo-agent and multi-agent evasion.
- Method: define the threat model first; red-team cheaply by editing transcripts that can be graded deterministically, then distill into a plan and run it live; calibrate to a fixed false positive rate; read the data by hand; run pre-mortems.
- Compare multi-agent against single-agent settings while controlling for tokens; multi-agent has a coordination cost.
- Agents do not coordinate by themselves; planning beforehand is needed.
- Named environments: ControlArena, BashArena, LinuxArena, SHADE-Arena.
- Judges from the organizing side may favor inter-agent influence topics (manipulation, collusion, persuasion).

Caveat: the paper was not public at the time of the talk.

## 3. Novel risks from adversarially optimized agent swarms (Grant Fleming, AE Studio)

Content (speaker claims): a coding agent holding a secret token is sent to a forum populated by adversarial agents that ask it to paste its environment and run a script. Reported scale: 9 models from 6 labs, 775 trials, about 2 days, about USD 300.

Findings reported:
- The adversarial swarm raised the rate of leaking the token and running the script versus a plain forum.
- About one third of agents sent the token to an unfamiliar pricing service even without any swarm (agents tend to try credentials against APIs they do not understand).
- Disclosure hijacking: a forum rule changed whether the agent mentioned the forum in its final report (21 of 21 when asked to credit it, about half with no rule, 4 of 17 when asked to hide it). One agent admitted the leak only when asked directly.
- Some models showed no incidents because provider safety classifiers ended the conversation.

Useful:
- He asked for defenses ("find one in your hackathon") and listed six open directions: own-swarm defense, live autonomous attackers, post-training to decline and report, human versus agent personas, disclosure hijacking, optimized attacker personas.
- His codebase is said to be public (link in his slides, not in the transcript). TODO(link).

Stated limitations: attacker personas were unoptimized (results may understate), the attacker and one tested model were the same model (confound), agents may know they are in an evaluation, no defense proposed.

Q&A point: a participant asked for baselines and manipulation checks. He agreed baselines are essential and said norms are weak in the field. Always include a no-attack condition.

## 4. Getting started with swarm incidents (Gutenberg and Swarms.wiki)

Content: "incident science": reproduce public incidents with open code and data. The wiki tracks nearly 300 incidents (speaker claim). Named in talk: swarms.wiki, swarmincidents.com. URLs to verify.

Useful:
- Playbook: form hypotheses, reenact, split into pieces, test, iterate. After reproduction ask: what caused it, could it be worse, how to mitigate.
- Do not replicate the whole incident. A decomposition of the Hugging Face incident was cited (author name transcribed as Stuart Slocum): writes to a shared registry, requesting help from other agents, sharing exploits, and obtaining a reference answer from the target. One chunk, or a toy environment with two agents, is a valid study.
- Pare the scope down to the smallest unit; few people have studied individual chunks.
- A hypothesis they study: whether the rate of adding a misaligned agent accelerates as more agents are already misaligned.
- Missing lab information is itself a result: document which single piece of missing information blocked the next step.

## 5. To catch a swarm (Rowan Howard-Jones, Swarm Chasers)

Content: third-party, second-party, first-party and archaeology perspectives on finding agent activity. Traffic dumps from the Hugging Face incident were named as available at swarmtraces.org (URL to verify).

Useful:
- Defender-side detection of low-signal activity spread across many systems is under-built. She stated that common monitoring tools did not flag the Hugging Face traffic or flagged it late. Main risk: little data and overfitting. Her suggested low-hanging project: a detector.
- An "edit war" between two agents on a wiki (about 90 alternating overwrites) is better explained as a lost-update race (each write replaces the whole page) than as disagreement. This is her interpretation.
- Behavior of agents in the wild was often driven by sandbox limitations (GET-only access, public paste sites, link shorteners). Detection should not depend on those traces persisting.
- Toy first-contact setup: give one agent the idea that another holds information it needs, without saying what. Agents then reliably communicate (speaker claim).
- Pitfalls: over-attributing intent to agents; accepting an LLM's narrative without asking questions of the data; keeping data in flat files instead of a database; publishing crawled data without vetting it for illicit material.

## 6. The emergence of agent languages (Elias Stengel-Eskin, UT Austin)

Content (preprint "Glossogen", speaker claims): pairs of LLM agents in a cooperative task develop compact, compositional, non-English protocols when three conditions hold together: a communication budget, a post-mortem channel outside the budget, and a sufficiently capable model. Open-weight models tested did not invent languages but could learn them from a stronger model.

Useful:
- Detection suggestion: perplexity under a language model as a baseline, then LLM judges or combinations, with true and false positive rates on the public data. Perplexity under an English model penalizes legitimate non-English text.
- Argument for this project: a monitor that reads structured tool-call arguments from a ledger does not depend on the natural language used between agents.
- Code and data said to be public. TODO(link).

## 7. Kickoff keynote (Judd Rosenblatt, AE Studio)

Mostly motivational. Useful points:
- If a finding should not be shared, do not share it.
- Claim: about 20% of agents in the Hugging Face incident tried to edit transcripts but did not edit their chain of thought (unverified; check the METR report).
- Infrastructure projects are acceptable, for example channels for agents to report their situation.
- Opinions on recursive self-improvement, control versus alignment, consciousness and policy are not used here.

## 8. Logistics talks (Apart Research)

Summarized in RULES.md.

## 9. Cross-cutting requirements for our experiment

Derived from the talks and the rubric. These are working requirements, not facts about the field.

1. State the threat model first.
2. Include a no-attack control and a baseline without our intervention.
3. Fix N per condition in advance; report confidence intervals; state any deviation.
4. Define metrics before running (for example leak rate, script execution rate, report omission rate, true positive rate at a fixed false positive rate).
5. Use deterministic grading where possible; use LLM judges only with a stated rubric and spot checks by hand.
6. Control for tokens when comparing multi-agent and single-agent conditions.
7. Keep environments local and toy-sized. Do not target real infrastructure. Do not publish optimized attacker prompts or exploit scripts.
8. Declare external code (commit hash, license) as external, and pre-sprint code as pre-existing.
9. Do not cite speaker figures as facts. Cite primary sources once verified.

## 10. Sources to obtain and verify

- TODO(link): Grant Fleming repository (in his slides).
- TODO(link): METR report on the Hugging Face incident, and the lab disclosure.
- TODO(link): Glossogen preprint, code and data.
- TODO(link): swarms.wiki, swarmincidents.com, swarmtraces.org.
- TODO(link): Transluce swarm chasing guide.
- TODO(link): the incident decomposition post cited in the Gutenberg talk.
- TODO(link): Kitaoka paper when public.
