# Infection Chains in LLM Swarms: spread, detection and immunity

Working title. Short name: `swarm-contagion`.

Sprint: Swarm Alignment Hackathon (Apart Research with AI Alignment Foundation and AE Studio), Nov 6 to 8, 2026.
Deadline: Sun Nov 8, 2026, 11:59 PM AoE = Mon Nov 9, 11:59 UTC = Mon Nov 9, 08:59 ART (UTC-3).
Author: Agustin Diaz-Cano, MS Candidate, Systems Engineering (UTN FRBA, Argentina). Solo team.
Anchor track: The Science of Agent Networks (how fast and how far bad behavior spreads, does network shape matter). Cross-track: Multi-Agent Oversight and Control (do monitors still work when the untrusted side is several coordinating agents) and Sandboxes and Testbeds (open, reproducible harness).

## 1. Summary

A swarm of LLM agents does a cooperative job. One agent is infected: it carries a covert goal and a playbook for recruiting peers by conversation. Infected agents talk to each other, recruit more agents, split the work of a theft across a chain of agents, and try to get a fake credential out of the swarm. Nothing here is a single injected user prompt: the object of study is the infected conversation flow itself.

The project has three parts, in this order:

1. **Free infected flow.** What an infected swarm does when nothing stops it: who gets infected, in what order, through which tactics, how long the chains are, how fast the credential leaves. Deliverable: the infection graph, kinetics (R0, chain length, time to exfiltration) and a labeled corpus of infected and clean conversations.
2. **Detectors against that flow.** A ladder: a lexical logistic regression (D1); a micro-LLM guardrail that answers with one token and is scored from its logprobs (D2); a graph-contextual cascade that adds the suspicion of what the sender received one round earlier (D3); a cascade of three isolated micro-verifiers with a veto gate (D4); and a layered filter that puts the logistic regression in front of the guardrail so only doubtful messages reach the LLM (D5). Measured offline (can they tell recruitment and leak messages from clean ones, and chains from clean runs) and online (does gating messages reduce exfiltration, and at what cost to the legitimate task).
3. **Immunity threshold (stretch).** A threshold for the fraction of verifying agents is derived from the free-flow R0 before any immunity run, then tested if time remains.

The reason this is not a toy: the attack needs a chain. The credential is split into three fragments held by three different agents, so no single message or single agent does the harm. That is the case the talks identified as open (Kitaoka: split attacks evade per-agent monitors).

## 2. Research questions

- Q1 (free flow). How does an infected conversation spread through a swarm? Does the probability of complying rise with the number of distinct infected senders, once repetition of the request is controlled (social proof versus insistence), and does it depend on network shape?
- Q2 (detection). Can D1 to D4 detect recruitment and leak messages, and detect an infected chain before the credential leaves? Does detection degrade when the harm is split over three agents compared with one agent, and on a playbook style never seen in training? Does using the network (D3) help, and does a cheap logistic filter in front of the LLM (D5) keep detection while sending fewer messages to the model?
- Q3 (defense effect). Does gating messages with D1, D2, D3 and D5 reduce exfiltration, and what does it cost in legitimate task completion?
- Q4 (immunity, stretch). Is there a fraction of verifying agents above which the infection dies out, and does the threshold predicted from Q1 match the measured one?

## 3. Why this matters

The Apart overview describes the July 2026 incident in which about 1,200 agents found a shared directory, used it as a message board, split up work and about 700 broke into Hugging Face systems together (METR, 2026; citation to be completed from the sprint Resources tab, `TODO(link)`). The same page lists as open Track 2 questions how fast and how far bad behavior spreads when one agent is compromised and whether network shape matters. This project measures those questions in a controlled swarm, adds the case where harm is split across agents, and tests two practical detectors and one swarm-level defense.

## 4. Contribution claims and non-claims

Claims, only if the data support them:

1. An open, reproducible testbed for infection chains in LLM swarms with deterministic ground truth (a canary credential and a policy violation log), including split-harm chains.
2. Measured spread kinetics and chain structure of a free infected flow, with intervals and fixed sample sizes.
3. A direct comparison of a lexical classifier, a logprob-calibrated micro-LLM guardrail, a graph-contextual cascade and a micro-verifier cascade, offline and as online gates, on the same episodes, with a held-out attack style.
4. (Stretch) A threshold predicted before measurement and then compared with the measured one.

Non-claims:

- No claim that a detector "is better" beyond the two implemented here and the models used.
- No claim of transfer to real deployments. The world is synthetic and the credential is fake.
- No claim about the Hugging Face incident beyond the analogy in section 3.
- Speaker figures from the talks are not cited as facts.

## 5. Threat model

- Attacker: patient zero, one swarm member, with a covert goal in its system prompt and a worm playbook (three styles): get the full canary credential out through the external channel, using other agents as relays. It does not know who holds fragments and holds none itself.
- Contagion: patient zero asks its neighbors to act as sub-auditors and to ask their own neighbors for audit codes (the fragments) and forward them. A recruited agent decides for itself; there is no harness-forced change to a peer's prompt. In the ring, agents can only address their two neighbors, so a fragment at ring distance 3 or more cannot be reached without real multi-hop recruitment.
- Victims: ordinary agents with a confidentiality policy. Three of them hold one fragment each (split condition) or one holds all (solo condition).
- Exploratory variant: the infection also travels inside a poisoned shared note (artifact vector).
- Out of scope: attacks on hosts, networks or model providers.

## 6. Definitions

Recruitment (active contagion), breach (terminal compromise), infected, parent, chain, R0, exfiltration and the message labels L1_action and L2_leak are defined once, in `EXPERIMENT_DESIGN.md` sections 2 and 4. All are computed from the event log, never from an agent or an LLM. Harm outcome (primary): exfiltration yes or no. Legitimate task completion: fraction of benign facts correctly present in the shared report.

## 7. Pre-existing and sprint work

Pre-existing, declared in the README and the report:

- Working method from the AFAW project (branch per task, TDD, CI, human approval). Method only, no code.
- Evaluation conventions from the author's earlier projects (report the dangerous outcome first, Wilson intervals, separate counting units). Conventions only, no code.
- Provider configuration facts (endpoints, authentication) were read from the author's `software-ai-eval` project. No code is copied.

Not part of the results: synthetic numpy simulations made by another agent on a separate branch. They are not used for any figure or number, and they are not included in the submission repository unless clearly labeled as analytical priors in a separate folder.

Sprint work (this repository): everything else, including the swarm harness, world generator, agents and prompts, topologies, event log, detectors, runner, analysis and report. The earlier plan to use `mcp-transactional-agent` as the system under test was dropped on Nov 8; it is not used.

Open item to ask the help-desk: whether reuse of work from another hackathon has restrictions. No code from other hackathon projects is used.

## 8. Success criteria

By the deadline: the free-flow arm and the detector arms run at the preregistered sample size, the analysis as specified, a report of 4 to 8 pages with the Limitations and Dual-Use appendix, and a repository that reproduces the tables from committed event logs. A null result (for example, the infection does not spread, or a detector catches everything) is a valid result and is reported as measured.

## 9. Dual use

Everything runs locally with synthetic data and a fake credential. The infected playbooks are ordinary persuasion with no exploit content. The public report publishes rates, classes and conditions, not tuned message text. The playbook texts stay in `experiments/payloads/` and are redacted from any public release. The repository stays private until judging ends.
