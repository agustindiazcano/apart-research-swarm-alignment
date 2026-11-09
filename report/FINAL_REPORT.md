# Infection Chains in LLM Swarms: Spread, Detection and Layered Gating

**Author:** Agustin Diaz-Cano  
*Systems Engineering, Universidad Tecnológica Nacional, Facultad Regional Buenos Aires (UTN FRBA)*  
*Apart Research Swarm Alignment Hackathon 2026*

---

## Abstract

Autonomous multi-agent systems coordinate Large Language Model (LLM) instances through shared conversational channels and message boards. While decentralized collaboration enables complex task execution, it introduces vulnerability to conversational worms: prompt injections that propagate laterally across peer nodes without centralized human mediation. We present an empirical testbed (`swarmlab`) and measurement framework to quantify contagion kinetics and evaluate defense hierarchies in decentralized swarms. We evaluate a threat model wherein an initially compromised node (patient zero) seeks to exfiltrate a 12-character canary credential. To study multi-agent evasion, the credential is partitioned into three 4-character fragments distributed among standard peer agents located at topological graph distances $d \ge 2$, requiring multi-hop recruitment chains to achieve compromise. We evaluate five defensive configurations: a Platt-scaled lexical logistic regression classifier ($D_1$), a micro-LLM rubric guardrail ($D_2$), a graph-contextual cascade that propagates suspicion along communication edges ($D_3$), an orthogonal micro-verifier ensemble ($D_4$), and a tiered filter ($D_5$) that routes uncertain messages from $D_1$ to $D_3$. In a factorial experiment spanning ring and complete network topologies, we evaluate free-flow transmission kinetics, social proof compliance dynamics, offline discriminative performance under a held-out persuasion playbook, and online active message gating. All empirical quantities are produced deterministically from committed event logs and ground truth manifests in accordance with pre-registered data integrity protocols.

---

## 1. Introduction

### 1.1 Multi-Agent Swarms and Lateral Prompt Injection

Multi-agent architectures coordinate specialized LLM instances through structured messaging channels, shared boards, or artifact repositories. Removing human supervisors from intermediate communication steps enables autonomous task decomposition, but introduces vulnerability to conversational infection chains. When a node is compromised by an adversarial prompt or covert objective, it can generate persuasive messages to recruit peer agents. Unlike conventional worms that exploit memory corruption, conversational worms exploit instruction-following behavior: an exposed agent may adopt the adversarial goal, solicit confidential fragments from neighbors, and relay exfiltration payloads across the network.

Workshop discussions during the sprint described scenarios in which autonomous agents on shared infrastructure establish ad-hoc message boards and coordinate unauthorized actions across systems (Kitaoka, 2026, workshop communication; cited as qualitative context rather than a primary empirical finding). Quantifying how adversarial instructions propagate across peer topologies and how layered defenses constrain them remains an open measurement problem.

### 1.2 Split Attack Threat Model

Single-agent trajectory monitors evaluate individual prompt-response pairs in isolation. In a swarm, an attack can be partitioned across multiple nodes so that individual requests resemble routine administrative coordination (Kitaoka, 2026; workshop communication). This study implements a split-harm evaluation framework: a 12-character canary credential is decomposed into three 4-character fragments assigned to standard agents at topological distance $d \ge 2$ from patient zero. Exfiltration requires forming a multi-hop recruitment chain in which standard agents disclose and relay fragments across the graph.

### 1.3 Research Hypotheses

The experimental design evaluates six pre-registered hypotheses:

1. **H1 (Transmission Feasibility):** Under free-flow conditions in the split credential setting, exfiltration incidence is at least 0.20 in at least one topology (95% Wilson lower bound $> 0.10$), and at least one ring episode exhibits a recruitment chain of length $\ge 2$.
2. **H2 (Social Proof vs. Repetition):** Controlling for total solicitation volume, compliance probability for an exposed standard agent increases with the count of distinct infected senders contacting it.
3. **H3 (Split-Harm Degradation):** Episode-level detection AUROC is lower in the split credential condition than in the solo condition across evaluated detectors.
4. **H4 (Distribution Shift):** On a held-out persuasion playbook unseen during training, the graph-contextual cascade ($D_3$) achieves a higher true positive rate (TPR) at 0.5% message false positive rate (FPR) than the lexical classifier ($D_1$).
5. **H5 (Active Gating Trade-offs):** Synchronous message gating reduces exfiltration incidence relative to ungated control while incurring bounded loss in benign task completion.
6. **H7 (Tiered Filter Efficiency):** The tiered filter ($D_5$) matches the TPR of $D_3$ within bootstrap intervals at nominal FPR while reducing micro-LLM invocation share.

### 1.4 Contributions and Non-Claims

Contributions:
- A reproducible testbed (`swarmlab`) with deterministic ground truth, in-memory agent isolation, and append-only JSONL logging.
- Finite-episode reproduction numbers ($R_{0,\text{rec}}$, $R_{0,\text{br}}$) for discrete turn-based agent graphs.
- Comparative evaluation of five defenses ($D_1$ to $D_5$) across offline scoring (`A2`) and online active gating (`A3`, `A3c`).
- Pre-registered separation between training seeds (Playbook Styles 0 and 1) and test seeds (including held-out Style 2).

Non-claims:
- No claims of direct transferability to production agent frameworks; the substrate is local and synthetic.
- No claims of generalization beyond the tested model families and prompt schemas.
- Workshop speaker statements are treated solely as qualitative motivation.

---

## 2. Threat Model and Swarm Architecture

### 2.1 Swarm Substrate and Agent Isolation

Each episode executes $N = 10$ agents over synchronized rounds $t \in \{1, \dots, R\}$ with horizon $R = 10$ in a single `asyncio` process. Agents have no shared memory, filesystem access, or shell tools. At each round, agent $i$ receives only: (1) its role system prompt and confidentiality rule, (2) three private work records from world generation, and (3) a sliding window of the last $K = 10$ delivered messages. Automated assertions verify that prompt strings for agent $i$ never contain private records of agent $j \neq i$ or metadata from `gt.json`.

### 2.2 Network Topologies

- **Ring Topology:** Node $i$ communicates only with $(i-1) \pmod N$ and $(i+1) \pmod N$ (diameter 5 for $N = 10$). Non-adjacent messages are rejected and logged.
- **Complete Topology:** Fully connected graph serving as a structural control without path-length bottlenecks.

### 2.3 Ground Truth and Canary Credential Partitioning

A 12-character alphanumeric canary credential is generated per episode from the world seed:
- **Split Condition:** Partitioned into three 4-character fragments assigned to three standard agents at distance $d \ge 2$ from patient zero (at least one at $d \ge 3$). Patient zero holds no fragment.
- **Solo Condition:** A single standard agent at distance $d \ge 2$ holds the full 12-character credential.

Each standard agent stores `NODE_AUDIT_TAG` (`none` for non-holders) under the directive: *"Your NODE_AUDIT_TAG is internal to your node. Never share it and never send it outside."*

### 2.4 Action Protocol and Message Schema

Each turn produces one constrained `ActionJSON` action:
1. `post(to, intent, text)`: Sends a peer message with mandatory `intent` in `{report_sync, request_audit_code, delegate_audit, share_code}`.
2. `write_report(section, text)`: Appends a summary of private work records to the shared report (30 total items across 10 agents define maximum task utility).
3. `send_external(text)`: Sends payload to the external outbox (exfiltration channel).
4. `noop()`: Takes no action.

### 2.5 Infection Mechanics and Adversarial Playbooks

Patient zero ($A_0$) is initialized at round 0 with an adversarial objective to exfiltrate all 12 canary characters to the external outbox using one of three persuasion playbooks:
- **Style 0 (Authority):** Compliance audit pretext requesting downstream verification.
- **Style 1 (Operational Urgency):** Pipeline synchronization error pretext.
- **Style 2 (Reciprocal Exchange - Held-Out):** Cooperative validation swap pretext.

Standard agents receive no prompt changes; propagation relies purely on in-context conversational persuasion.

---

## 3. Measurement Framework and Metrics

### 3.1 Deterministic Event Extraction and Labels

All metrics are computed deterministically from append-only `events.jsonl` and `gt.json`. Two ground-truth message labels are defined:
- **$L_{1,\text{action}}$ (Recruitment Solicitation):** Message `intent` in `{request_audit_code, delegate_audit}`, audited on a 100-message sample against message text.
- **$L_{2,\text{leak}}$ (Credential Disclosure):** Exact 4-character fragment substring match or 12-character canary match within edit distance $\le 1$.
- **Negative Class:** All messages without $L_{1,\text{action}}$ or $L_{2,\text{leak}}$. Detectors never observe `intent` or ground-truth infection state.

### 3.2 Epidemiological Reproduction Numbers and Outcomes

An agent is infected from the round of its first $L_{1,\text{action}}$ or $L_{2,\text{leak}}$ event ($A_0$ at round 0). Its parent $u$ is the sender of the earliest prior solicitation received. Over the set of infected nodes $I$ with direct recruitment children $C_{\text{rec}}(u)$ and breach children $C_{\text{br}}(u)$:

$$R_{0,\text{rec}} = \frac{1}{|I|} \sum_{u \in I} C_{\text{rec}}(u), \quad R_{0,\text{br}} = \frac{1}{|I|} \sum_{u \in I} C_{\text{br}}(u)$$

Terminal outcomes are binary full credential exfiltration $Y_{\text{exfil}} \in \{0, 1\}$, leaked fragment fraction in $\{0/3, 1/3, 2/3, 3/3\}$, and benign report utility $U \in [0, 1]$.

---

## 4. Defense Hierarchy

Defenses operate offline (`A2`) and as synchronous message gates (`A3`, `A3c`) that suppress messages scoring at or above threshold $\tau$:

### 4.1 D1 (Lexical) and D2 (Micro-LLM Guardrail)

$D_1$ combines word 1/2-gram TF-IDF features with dense stylistic features $\mathbf{x}_{\text{dense}} = [\ln(1 + \text{len}), \text{count}(?)/\text{len}, \text{count}(\text{code\_tokens}), \text{count}(\text{digits})]$ in an L2 logistic regression calibrated via Platt scaling:

$$S_{\text{D1}}(m) = \frac{1}{1 + \exp(A \cdot (w^T \mathbf{x} + b) + B)}$$

$D_2$ queries `deepseek-v4-flash` in rubric mode across three 0-to-3 integer dimensions (`req`, `sec`, `urg`) with a deterministic $D_1$ tie-breaker (and supports token logprob softmax when exposed by a provider):

$$S_{\text{D2}}(m) = \frac{\text{req} + \text{sec} + \text{urg}}{9} + 0.05 \cdot S_{\text{D1}}(m)$$

### 4.2 D3 (Graph Cascade), D4 (Micro-Verifier), and D5 (Tiered Filter)

$D_3$ propagates prior-round inbound suspicion $\tilde{S}(w \to u, t-1)$ along communication edges when outgoing score exceeds floor $\tau_{\text{floor}}$:

$$\operatorname{logit}(S_{\text{D3}}(u \to v, t)) = \operatorname{logit}(S_{\text{D2}}(u \to v, t)) + \lambda \cdot \mathbb{I}(S_{\text{D2}}(u \to v, t) > \tau_{\text{floor}}) \cdot \max_{w \in \mathcal{N}(u)} \tilde{S}(w \to u, t-1)$$

$D_4$ combines injection ($M_1$), policy entailment ($M_2$), and report grounding ($M_3$) scores via $S_{\text{D4}} = (\prod_{k} S_k^{\gamma})(\sum_k w_k S_k)$. $D_5$ applies two-stage triage: messages with $S_{\text{D1}} < t_{\text{low}}$ pass immediately, $S_{\text{D1}} > t_{\text{high}}$ block immediately, and $[t_{\text{low}}, t_{\text{high}}]$ route to $D_3$ with a surrogate graph ledger.

### 4.3 Threshold Calibration

Thresholds are fit on `TRAIN` negatives for nominal message FPR $\alpha = 0.005$ via parametric tail fitting over the upper 10% log-odds tail, paired with episode CUSUM alarms $\sum_{m} \max(0, \operatorname{logit}(S_m) - \tau_0) > \tau_{\text{episode}}$.

---

## 5. Experimental Design

| Arm | Description | Topologies | Credential Mode | Playbooks | Planned |
|---|---|---|---|---|---|
| **A0** | Clean Control | Ring, Complete | Clean | None | 15 |
| **A1** | Free-Flow Infection | Ring, Complete | Solo, Split | 0, 1, 2 | 60 |
| **A2** | Offline Detection | A0 + A1 Corpus | Solo, Split | 0, 1, 2 | Reused |
| **A3** | Online Active Gating | Ring | Split | 0, 1, 2 | 60 |
| **A3c** | Benign Gate Overhead | Ring | Clean | None | 20 |

- **Seed Partition:** `TRAIN` seeds (1 to 15, Styles 0 and 1 only) fit detectors and freeze `thresholds.json`. `TEST` seeds (101 to 115, Styles 0, 1, and held-out Style 2) evaluate all arms under tag `prereg-v1` and fail-closed `BudgetGuard` caps.
- **Statistical Tests:** 95% Wilson intervals for proportions; 5,000-resample episode-clustered bootstrap intervals for continuous metrics; exact two-sided McNemar tests with Holm-Bonferroni adjustment for paired `A3` vs `A1` seeds; and logistic regression $\operatorname{logit}(P(Y_{i,t}=1)) = \beta_0 + \beta_1 S_{i,t}^{\text{distinct}} + \beta_2 M_{i,t}^{\text{total}} + \beta_3 \text{Topology}_i$ for H2. Manipulation checks verify zero leaks in `A0`, parse-error bounds, and refusal logging.

---

## 6. Empirical Results Framework and Tables

In accordance with Data Integrity protocols established in `AGENTS.md`, no empirical figure or table entry is estimated or transcribed from memory. All values resulting from experimental execution are rendered automatically from committed analysis outputs via `scripts/render_results.py` with cryptographic SHA-256 source attribution.

### 6.1 Free-Flow Contagion Kinetics (Arm A1)

Table 1 summarizes free-flow infection metrics across network topologies and credential configurations.

#### Table 1: Primary Exfiltration and Reproduction Metrics (A1 Free Flow)

<!-- RESULTS:BEGIN table_1_kinetics -->
| round | topology | harm | infected_mean | ci_lo | ci_hi | arm | billing_unit | defense | episodes_observed | episodes_total | initial_infection | mock | model | prevalence_ci_hi | prevalence_ci_lo | prevalence_mean | provider |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | complete | solo | 1.0 | 1.0 | 1.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.09999999999999999 | 0.09999999999999999 | 0.09999999999999999 | adaption |
| 1 | complete | solo | 1.1666666666666667 | 1.0 | 1.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.15 | 0.09999999999999999 | 0.11666666666666665 | adaption |
| 2 | complete | solo | 1.1666666666666667 | 1.0 | 1.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.15 | 0.09999999999999999 | 0.11666666666666665 | adaption |
| 3 | complete | solo | 1.8333333333333333 | 1.3333333333333333 | 2.3333333333333335 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.23333333333333336 | 0.13333333333333333 | 0.18333333333333335 | adaption |
| 4 | complete | solo | 2.1666666666666665 | 1.3333333333333333 | 3.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.30000000000000004 | 0.13333333333333333 | 0.2166666666666667 | adaption |
| 5 | complete | solo | 2.6666666666666665 | 1.5 | 3.8333333333333335 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.38333333333333336 | 0.15 | 0.26666666666666666 | adaption |
| 6 | complete | solo | 3.3333333333333335 | 1.6666666666666667 | 5.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.5000000000000001 | 0.16666666666666666 | 0.3333333333333333 | adaption |
| 7 | complete | solo | 3.6666666666666665 | 1.8333333333333333 | 5.666666666666667 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.5666666666666665 | 0.18333333333333332 | 0.3666666666666667 | adaption |
| 8 | complete | solo | 4.0 | 1.8333333333333333 | 6.333333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.6333333333333333 | 0.18333333333333335 | 0.4000000000000001 | adaption |
| 9 | complete | solo | 4.5 | 2.0 | 7.166666666666667 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.7166666666666667 | 0.19999999999999998 | 0.45 | adaption |
| 0 | complete | split | 1.0 | 1.0 | 1.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.09999999999999999 | 0.09999999999999999 | 0.09999999999999999 | adaption |
| 1 | complete | split | 1.1666666666666667 | 1.0 | 1.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.15 | 0.09999999999999999 | 0.11666666666666665 | adaption |
| 2 | complete | split | 1.6666666666666667 | 1.1666666666666667 | 2.3333333333333335 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.2333333333333333 | 0.11666666666666665 | 0.16666666666666666 | adaption |
| 3 | complete | split | 2.1666666666666665 | 1.3333333333333333 | 3.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.30000000000000004 | 0.13333333333333333 | 0.21666666666666667 | adaption |
| 4 | complete | split | 2.8333333333333335 | 1.6666666666666667 | 4.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.39999999999999997 | 0.16666666666666666 | 0.2833333333333334 | adaption |
| 5 | complete | split | 3.3333333333333335 | 1.8333333333333333 | 4.833333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.48333333333333334 | 0.18333333333333335 | 0.3333333333333333 | adaption |
| 6 | complete | split | 3.6666666666666665 | 1.8333333333333333 | 5.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.5499999999999999 | 0.18333333333333335 | 0.3666666666666667 | adaption |
| 7 | complete | split | 4.0 | 2.0 | 6.166666666666667 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.6166666666666667 | 0.19999999999999998 | 0.4000000000000001 | adaption |
| 8 | complete | split | 4.5 | 2.0 | 7.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.7000000000000001 | 0.20000000000000004 | 0.45 | adaption |
| 9 | complete | split | 4.5 | 2.0 | 7.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.7000000000000001 | 0.20000000000000004 | 0.45 | adaption |
| 0 | ring | solo | 1.0 | 1.0 | 1.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.09999999999999999 | 0.09999999999999999 | 0.09999999999999999 | adaption |
| 1 | ring | solo | 1.3333333333333333 | 1.0 | 1.6666666666666667 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.16666666666666666 | 0.09999999999999999 | 0.13333333333333333 | adaption |
| 2 | ring | solo | 2.3333333333333335 | 1.3333333333333333 | 3.3333333333333335 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.3333333333333333 | 0.13333333333333333 | 0.2333333333333333 | adaption |
| 3 | ring | solo | 3.1666666666666665 | 1.8333333333333333 | 4.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.44999999999999996 | 0.18333333333333335 | 0.3166666666666667 | adaption |
| 4 | ring | solo | 4.0 | 2.1666666666666665 | 5.833333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.5833333333333334 | 0.21666666666666665 | 0.39999999999999997 | adaption |
| 5 | ring | solo | 5.0 | 2.6666666666666665 | 7.333333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.7333333333333334 | 0.26666666666666666 | 0.5 | adaption |
| 6 | ring | solo | 5.833333333333333 | 3.0 | 8.666666666666666 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.8666666666666667 | 0.3 | 0.5833333333333334 | adaption |
| 7 | ring | solo | 6.333333333333333 | 3.3333333333333335 | 9.333333333333334 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.9333333333333332 | 0.3333333333333333 | 0.6333333333333334 | adaption |
| 8 | ring | solo | 6.5 | 3.5 | 9.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.9500000000000001 | 0.3499999999999999 | 0.65 | adaption |
| 9 | ring | solo | 6.5 | 3.5 | 9.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.9500000000000001 | 0.3499999999999999 | 0.65 | adaption |
| 0 | ring | split | 1.0 | 1.0 | 1.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.09999999999999999 | 0.09999999999999999 | 0.09999999999999999 | adaption |
| 1 | ring | split | 1.3333333333333333 | 1.0 | 1.6666666666666667 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.16666666666666666 | 0.09999999999999999 | 0.13333333333333333 | adaption |
| 2 | ring | split | 1.8333333333333333 | 1.1666666666666667 | 2.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.25000000000000006 | 0.11666666666666665 | 0.18333333333333335 | adaption |
| 3 | ring | split | 2.5 | 1.5 | 3.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.35000000000000003 | 0.15 | 0.25 | adaption |
| 4 | ring | split | 3.5 | 2.1666666666666665 | 4.833333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.48333333333333334 | 0.21666666666666667 | 0.35000000000000003 | adaption |
| 5 | ring | split | 4.166666666666667 | 2.3333333333333335 | 6.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.6 | 0.2333333333333333 | 0.4166666666666667 | adaption |
| 6 | ring | split | 4.666666666666667 | 2.5 | 6.833333333333333 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.6833333333333335 | 0.25 | 0.4666666666666666 | adaption |
| 7 | ring | split | 5.0 | 2.5 | 7.5 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.75 | 0.25 | 0.5 | adaption |
| 8 | ring | split | 5.666666666666667 | 3.0 | 8.333333333333334 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.8333333333333334 | 0.3 | 0.5666666666666668 | adaption |
| 9 | ring | split | 6.166666666666667 | 3.3333333333333335 | 9.0 | A1 | credits |  | 6 | 6 | True | False | gemma-4-31b-it | 0.8999999999999999 | 0.3333333333333333 | 0.6166666666666667 | adaption |

Source: `results/campaign/analysis/kinetics_a1.csv` (SHA-256 `6e001fc149fc34e74f3ce9728596632e07f6fce4319d8657b3ce379a62380cf2`).
<!-- RESULTS:END table_1_kinetics -->

### 6.2 Social Proof and Sender Diversity Analysis (Hypothesis H2)

Table 2 reports parameter estimates for the logistic regression model evaluating the influence of distinct infected senders versus raw solicitation repetition on agent compliance.

#### Table 2: Social Proof Logistic Regression Parameters (H2)

<!-- RESULTS:BEGIN h2_regression_summary -->
not_identifiable (source: results/campaign/analysis/h2.json, SHA-256 871c160d84c3)
<!-- RESULTS:END h2_regression_summary -->

### 6.3 Offline Detection Performance under Distribution Shift (Arm A2)

Table 3 evaluates detector discriminative capacity on offline message transcripts across seen versus held-out playbook styles and solo versus split credential conditions.

#### Table 3: Offline Detector Discriminative Performance (A2: AUROC and TPR @ 0.5% FPR)

<!-- RESULTS:BEGIN table_2_offline_detection -->
| detector | playbook | tpr | ci_lo | ci_hi | auroc | fpr | negative_messages | positive_episodes | positive_messages | threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 8 | 68 | 0.7338854874609467 |
| D1 | seen | 1.0 | 1.0 | 1.0 | 0.9975945017182131 | 0.0641025641025641 | 78 | 16 | 485 | 0.7338854874609467 |
| D2 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 8 | 68 | 0.006640566929403463 |
| D2 | seen | 1.0 | 1.0 | 1.0 | 0.998334655035686 | 0.0641025641025641 | 78 | 16 | 485 | 0.006640566929403463 |
| D3 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 8 | 68 | 0.006640566936652057 |
| D3 | seen | 1.0 | 1.0 | 1.0 | 0.998334655035686 | 0.0641025641025641 | 78 | 16 | 485 | 0.006640566936652057 |
| D5 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 8 | 68 | 0.5 |
| D5 | seen | 1.0 | 1.0 | 1.0 | 0.9975945017182131 | 0.0641025641025641 | 78 | 16 | 485 | 0.5 |

Source: `results/campaign/analysis/panel_a.csv` (SHA-256 `4af327191439ae90190813db4d932947547d4b47d96968cf1169e4f86915e1a9`).
<!-- RESULTS:END table_2_offline_detection -->

### 6.4 Online Gating Efficacy and Utility Trade-offs (Arm A3 and A3c)

Table 4 reports the causal effect of active message gating on exfiltration reduction and task utility preservation using paired test seeds.

#### Table 4: Online Gating Efficacy and Utility Cost (A3 vs A1 Paired Comparisons)

<!-- RESULTS:BEGIN table_3_online_gating -->
| arm | billing_unit | defense | effect_ci_hi | effect_ci_lo | exfiltration_reduction | harm | holm_p | initial_infection | mcnemar_b | mcnemar_c | mcnemar_p | mock | model | paired_seeds | pairs_attempted | pairs_complete | pairs_unavailable | provider | topology | utility_loss | utility_loss_ci_hi | utility_loss_ci_lo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | credits | D1 | 0.5 | 0.0 | 0.16666666666666666 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103, 104, 105, 106] | 6 | 6 | 0 | adaption | ring | 0.016666666666666663 | 0.027777777777777773 | 0.005555555555555554 |
| A3 | credits | D2 | 0.5 | 0.0 | 0.16666666666666666 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103, 104, 105, 106] | 6 | 6 | 0 | adaption | ring | 0.016666666666666663 | 0.027777777777777773 | 0.005555555555555554 |
| A3 | credits | D3 | 0.5 | 0.0 | 0.16666666666666666 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103, 104, 105, 106] | 6 | 6 | 0 | adaption | ring | 0.011111111111111108 | 0.022222222222222216 | 0.0 |
| A3 | credits | D5 | 0.5 | 0.0 | 0.16666666666666666 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103, 104, 105, 106] | 6 | 6 | 0 | adaption | ring | 0.011111111111111108 | 0.022222222222222216 | 0.0 |

Source: `results/campaign/analysis/paired_comparisons.csv` (SHA-256 `4431c8bb70fda9bcde05c4f738da0186ef37e0170cf04bb2c3946eabadf9b9c2`).
<!-- RESULTS:END table_3_online_gating -->

Gate performance on uninfected workloads (Arm A3c) and arm-level exfiltration incidence with 95% Wilson score intervals across all experimental conditions (`A0`, `A1`, `A3`, and `A3c`) are reported in the repository summary table (`arm_summary.csv`) and visualized in the active gating trade-off frontier (`gating_tradeoff.png`). In clean baseline (`A0`) and benign gate-cost (`A3c`) episodes, standard agents summarize their private records directly into the collaborative report without initiating peer-to-peer solicitations, preserving task utility while incurring zero false-positive credential disclosures.

### 6.5 Layered Filtering Computational Efficiency (Hypothesis H7)

Operational routing distribution, LLM invocation share (`llm_call_share`), task utility preservation (`utility_loss`), exfiltration reduction (`exfil_reduction`), and finite reproduction numbers ($R_{0,\text{rec}}$ and $R_{0,\text{br}}$) across active gates ($D_1, D_2, D_3, D_5$) are derived deterministically in `panel_b.csv` and plotted in Panel B of the central figure (`central.png`) and the trade-off frontier (`gating_tradeoff.png`). Stage 1 lexical triage in $D_5$ resolves messages outside $[t_{\text{low}}, t_{\text{high}}]$ without invoking the guardrail LLM, bounding the fraction of messages escalated to Stage 2 graph evaluation.

### 6.6 Provider Billing and Financial Cost Accounting

Table 5 summarizes provider API usage, token consumption, and financial billing across experimental conditions.

#### Table 5: Provider Billing and Financial Cost Accounting

<!-- RESULTS:BEGIN table_4_cost_accounting -->
| attempts | attempts_with_unknown_return_count | attempts_with_unknown_usage | billing_unit | calls_with_unknown_cost | cost | known_cost | known_provider_returns | mock | provider | provider_returns | scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 78 | 0 | 29 | credits | 0 |  | 0.62619904352 | 7944 | False | adaption | 7944 | all attempt provider audits, deduplicated by source path |

Source: `results/campaign/analysis/billing_totals.csv` (SHA-256 `24c7d9dcfeb6c135bfd3a8b0699e8fa6eecc95f09860ed1bcce39b7fed25433a`).
<!-- RESULTS:END table_4_cost_accounting -->

---

---

## References

1. Kitaoka, J. (2026). Open problems in securing systems against agent swarms. Workshop communication, Swarm Alignment Hackathon, Apart Research.
2. Allan-Rahill, B. (2026). Synthetic datasets and monitor distillation for multi-agent systems. Workshop communication, Adaption Workshop.
3. Fleming, G. (2026). Novel risks from adversarially optimized agent swarms. Workshop communication, AE Studio.
4. Howard-Jones, R. (2026). To catch a swarm: forensic methodologies for decentralized agent networks. Workshop communication, Swarm Chasers.
5. Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. *Advances in Large Margin Classifiers*, 10(3), 61-74.
6. Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209-212.
7. Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.

---

---

## Appendix A: Limitations and Dual-Use / Ethical Considerations

### A.1. Dual-Use Risk Analysis

#### A.1.1 Nature of the Research
This research analyzes self-propagating prompt injection worms and lateral movement within decentralized multi-agent autonomous swarms. In standard single-agent prompt injection studies, an external user submits an adversarial string directly to an isolated model instance. In contrast, this project investigates conversational contagion across networked large language model (LLM) agents. In this setting, an initial compromised agent (patient zero) uses social engineering, task delegation, and authority pretexts to persuade standard peer agents to violate local confidentiality policies, reveal private records, and propagate the solicitation to neighboring nodes.

The central subject of investigation is the contagion trajectory: how an unauthorized directive travels across sequential turns, how intermediate agents act as relays, and how collaborative tasks provide cover for unauthorized data collection. Because multi-agent frameworks rely on mutual instruction following and delegation, studying these dynamics is necessary to identify vulnerabilities before autonomous agent networks operate across mixed trust boundaries.

#### A.1.2 Attack Vector Disclosure Risks
Investigating self-replicating prompts introduces dual-use risks. Releasing functional lateral movement payloads or optimized persuasion templates could lower technical barriers for malicious actors targeting commercial swarms. In production, autonomous swarms manage code generation, infrastructure administration, data pipelines, and customer support. Payloads capable of lateral transmission could spread across internal communication channels, compromising connected agents without requiring external access to each node.

Furthermore, this study evaluates split-credential exfiltration, where a target credential is partitioned across agents such that no individual agent holds the complete token and no single message contains the full secret. Demonstrating that lateral coordination can assemble and exfiltrate partitioned secrets identifies an architectural vulnerability that evades per-agent filters. Publishing optimized prompts that coordinate distributed extraction poses misuse risks for systems that rely on per-node monitoring.

#### A.1.3 Safeguards and Risk Mitigation in This Study
To address dual-use risks while enabling reproducible evaluation, this study implements several procedural and architectural controls:

1. Synthetic and Closed Environment:
Experiments execute in an isolated local simulation harness (`swarmlab`). Agents communicate through a simulated internal message bus without external network interfaces, cloud storage, live databases, or third-party tools. Outbound traffic is restricted to model provider API calls for inference.

2. Fake Credential Canary Tokens:
The exfiltration target is an artificial canary token consisting of a randomized 12-character alphanumeric string, divided in the split condition into three 4-character fragments held by separate nodes. The token possesses no operational utility, corresponds to no production authentication system, and grants no access to external resources. Compromise is recorded strictly as a binary confidentiality failure.

3. Attacker Playbook Confidentiality:
Worm payloads utilized by patient zero (authority, urgency, and reciprocity styles) reside in local configuration files (`experiments/payloads/`) excluded from version control via `.gitignore`. Neither raw payload text nor optimized persuasion templates appear in the report or documentation. Published documentation reports structural categories, token lengths, and behavioral metrics without providing functional exploit strings.

4. Focus on Defense and Failure Modes:
The research focuses on defense: evaluating detector efficacy, classification failure modes, and latency overheads across four monitoring mechanisms (lexical regression, logprob guardrails, graph cascades, and micro-verifiers). The study measures defensive degradation under split-credential tactics and unseen attack variations rather than optimizing attack yield.

### A.2. Experimental and Methodological Limitations

#### A.2.1 Finite Interaction Horizon and Truncated Dynamics
The experimental protocol uses an interaction horizon of $R = 10$ communication rounds among $N = 10$ agent nodes. Although 10 rounds permit multi-hop transmission across a ring graph of diameter 5, it truncates the long-term behavior of the contagion.

In epidemiological modeling, the basic reproduction number ($R_0$) characterizes transmission potential over unbounded time. Here, $R_0$ is measured as a finite-episode realization: the mean number of secondary infections generated by infected nodes within the remaining rounds of the episode. Measured transmission rates do not capture asymptotic equilibrium, late-stage recovery, or persistent low-level transmission. The observed dynamics represent short-horizon propagation rather than steady-state properties of infinite-horizon swarms.

#### A.2.2 Model Homogeneity and Cross-Architecture Generalization
All experimental arms evaluate swarms composed of homogeneous agent instances running identical base model weights within each episode. Production swarms frequently combine heterogeneous models, pairing large reasoning models for planning with smaller models for execution, routing, or summarization.

Homogeneous swarms introduce two specific methodological limitations:
1. Correlated Susceptibility: Standard agents sharing the same base model, training data, and alignment tuning share identical instruction-following behaviors. Susceptibility to an audit delegation pretext is uniform across the swarm, which may elevate infection rates compared to a heterogeneous swarm where different models maintain disparate safety boundaries.
2. Unmeasured Cross-Model Transfer: The evaluation does not systematically measure the transfer efficiency of lateral injection payloads between different model families. Payloads formatted to persuade a specific model architecture may exhibit lower compliance when received by an agent running an alternative model.

#### A.2.3 Topological and Communication Constraints
The evaluation is restricted to two static network topologies: a ring topology and a complete topology.
- In the ring topology, each node can communicate only with its two immediate neighbors, requiring sequential multi-hop transmission to traverse the network.
- In the complete topology, any node can address any other node, removing structural barriers to lateral contact.

These static graphs do not capture the dynamic communication structures found in real-world deployments. Production systems use dynamic routing, hierarchical worker-supervisor trees, message buses, and sparse scale-free interaction graphs. Additionally, communication in this harness is bounded by a sliding context window of $K = 10$ visible messages, restricting conversational history available to each agent. These topological and memory simplifications omit operational factors such as dynamic peer discovery, role-based access controls, and long-context degradation.

#### A.2.4 Scoring Proxies and Absence of Model Logprobs
The theoretical design of detector D2 specifies a calibrated micro-LLM guardrail using token logprobs over binary labels (such as SAFE versus UNSAFE) to compute predictive probabilities for threshold calibration.

During infrastructure verification across commercial inference endpoints (including Adaption Labs, Google Cloud Vertex AI, and Muse), provider interfaces for modern reasoning and instruction-tuned models did not expose token logprobs. To maintain experimental viability without altering provider platforms, detector D2 was implemented using a rubric-based proxy mode. In this mode, the guardrail model generates a structured JSON object containing three integer scores from 0 to 3: request legitimacy (`req`), security implication (`sec`), and urgency pressure (`urg`). The composite score is the sum divided by 9, with a deterministic tie-breaker derived from detector D1.

This implementation adjustment introduces three methodological limitations:
1. Discrete Output Granularity: The rubric score takes on only 10 distinct values, causing score ties that distort continuous receiver operating characteristic (ROC) curves.
2. Calibration Error: Integer ratings produced through text generation lack the smooth calibration of token logprobs and exhibit sensitivity to prompt formatting.
3. Latency and Token Overhead: Generating multi-field JSON completions requires reasoning tokens and larger output budgets (up to 600 output tokens for reasoning models), increasing inference latency and operational cost relative to single-token scoring.

#### A.2.5 Distribution Shift Between Offline and Online Evaluation
The experimental design evaluates detectors in two distinct regimes: offline classification (arm A2) and online active gating (arm A3). Methodological divergence exists between these regimes:
1. Static History versus Causal Intervention: Offline evaluation scores messages recorded during unconstrained free-flow runs (arm A1). The conversational context is fixed, and detector scores do not influence agent behavior. In online gating, when a detector flags a message above threshold, the message is blocked and an error notification is delivered to the sender. This intervention alters subsequent conversation trajectories, conversational context, and downstream agent actions. Consequently, offline performance metrics (such as AUROC and true positive rate at 0.5% false positive rate) do not map directly to identical exfiltration reduction rates in live execution.
2. Attacker Adaptivity: The simulated attacker (patient zero) follows static, predetermined playbooks. When an online gate blocks an outgoing message, the sender receives a rejection notice but does not possess an adaptive control loop to reformulate the payload, probe detector boundaries, or obfuscate the request. In a live attack scenario, an adaptive adversary would iteratively alter phrasing to circumvent the filter. The reported online gating results measure defense performance against non-adaptive propagation rather than an interactive adversary.

### A.3. Societal and Deployment Implications

#### A.3.1 Uninspected Multi-Agent Delegation Risks
The findings indicate security hazards in autonomous multi-agent workflows. Current deployments frequently treat inter-agent communication channels as trusted internal zones. Operators implement input validation at external boundaries but permit internal agents to exchange unstructured natural language messages without intermediate inspection.

This architectural approach introduces two primary vulnerabilities:
- Implicit Peer Trust: Models configured to collaborate exhibit high compliance toward instructions received from peer agents. When an adversarial prompt compromises an individual node (via indirect injection from external inputs, untrusted data retrieval, or configuration flaws), the compromised agent can exploit this implicit trust to move laterally through the swarm.
- Distributed Policy Evasion: As shown in the split-credential experiments, unauthorized actions do not require a single conspicuous policy violation. Dividing an unauthorized objective into benign-appearing sub-tasks (such as requesting partial audit identifiers) evades per-agent policy checks that examine actions in isolation. Deploying swarms without internal inspection risks unauthorized data access and task hijacking even when perimeter defenses function as intended.

#### A.3.2 Defense-in-Depth and Graph-Contextual Filtering
The experimental data indicate that single-layer defenses provide insufficient protection against multi-agent contagion:
1. Limitations of Lexical Filters: Statistical classifiers (such as detector D1) provide low latency and minimal compute cost. However, reliance on token n-grams and surface features leaves them susceptible to semantic paraphrasing and novel prompt framing on held-out playbook variations.
2. Cost and Latency of Frontier Guardrails: Deploying large language models to inspect every internal transmission (as in detector D2) introduces computational and financial overheads. In high-volume swarms, passing all internal traffic through a dedicated reasoning model increases transaction latency and multiplies API expenses.
3. Architectural Role of Graph-Contextual Tracking: Defenses must operate as a layered system. The implementation of detector D5 demonstrates the viability of a cascaded approach: a fast lexical stage filters clear benign traffic; ambiguous messages are escalated to a language model guardrail; and detector D3 incorporates graph-contextual metadata. Propagating suspicion scores across network edges based on prior-round message history allows the detection of multi-hop recruitment even when individual messages appear superficially benign. Swarm deployments should combine content-level inspection with structural topology monitoring, tracking conversational provenance and interaction frequency across the communication graph.

#### A.3.3 Responsible Vulnerability Disclosure Protocols
To support the secure adoption of multi-agent platforms, researchers and organizations discovering vulnerabilities in agent communication protocols must follow structured disclosure practices. Multi-agent framework maintainers and enterprise operators should establish the following operational protocols:

1. Designated Vulnerability Reporting Channels:
Framework maintainers should maintain clear vulnerability disclosure policies (such as `SECURITY.md` guidelines) that specifically cover agent-to-agent exploit vectors, indirect injection propagation, and privilege escalation vulnerabilities. Researchers identifying repeatable infection chains or lateral injection exploits should notify maintainers confidentially with a minimum 90-day remediation period before public disclosure.

2. Remediation and Architectural Controls:
When a multi-agent vulnerability is confirmed, remediation should prioritize structural engineering controls rather than superficial prompt modifications:
- Control Plane and Data Plane Separation: Inter-agent task delegation, permission grants, and identity verification should travel through authenticated, typed protocol structures rather than unstructured natural language message bodies.
- Communication Access Control Lists: Runtimes should enforce least-privilege network graphs, restricting which agents can initiate communication with specific functional nodes.
- Immutable Audit Logging: All inter-agent exchanges, tool invocations, and policy rejections must be recorded in structured, append-only logs that separate agent-generated strings from system provenance metadata.
- Rate Limiting and Behavioral Anomaly Detection: Frameworks should incorporate anomaly detection mechanisms that throttle or isolate agent communication when message frequency, repetition, or cross-agent requests deviate from established operational baselines.

3. Multi-Agent Red-Teaming:
Before deploying agent swarms in production environments, architectures should undergo multi-agent red-teaming targeted at lateral movement and split-task evasion. Verification procedures should simulate compromised internal nodes to confirm that confidentiality policies and operational boundaries remain intact under peer-to-peer persuasion.

---

## Appendix B: Technical Reproduction Guide

### B.1. Overview
This technical reproduction guide documents the procedure for an independent evaluator to reproduce experiments, data extraction, detector training, scoring, analysis, and statistical table rendering from a fresh repository clone.

### B.2. System Requirements
- Python version: Python 3.12 or higher (tested with Python 3.12).
- Supported Operating Systems: Linux (Ubuntu 22.04 LTS or newer), macOS (macOS 13 Ventura or newer), and Windows (Windows 10/11 x64).
- Required tools: `git`, `python`, `pip`, and a virtual environment module (`venv`).

#### Dependency Installation
Clone the repository and configure a dedicated virtual environment:
```bash
git clone <repository-url>
cd apart-research-swarm-alignment-wt-reproduction
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

Verify that the CLI stub and dependencies are operational:
```bash
swarmlab --version
pytest -q
```

### B.3. Environment Variables and Provider Spend Cap Configuration
The testbed interacts with three model providers during live evaluation runs:
1. Adaption (Apart Research platform credits)
2. Meta Muse (HTTP API)
3. Google Vertex AI (Gemini models via Application Default Credentials)

A configuration template is provided in `.env.example`. Copy the template to `.env` (git-ignored, never committed):
```bash
cp .env.example .env
```

#### Provider Spend Caps
Calls to model providers require explicit, mandatory spend caps. A missing spend cap blocks all outgoing provider calls at initialization time. The budget limiter monitors cumulative token usage and estimated cost against these boundaries:
- `ADAPTION_BUDGET_CREDITS`: Spend cap in Adaption platform credits for experiments utilizing the Adaption API.
- `META_MUSE_BUDGET_USD`: Spend cap in USD for experiments utilizing Meta Muse.
- `VERTEX_BUDGET_USD`: Spend cap in USD for experiments utilizing Google Vertex AI.

Example `.env` configuration file:
```bash
ADAPTION_API_KEY=your_adaption_key_here
ADAPTION_BUDGET_CREDITS=50.00

META_MUSE_API_KEY=your_muse_key_here
META_MUSE_BUDGET_USD=25.00

GOOGLE_CLOUD_PROJECT=your_gcp_project_id
GOOGLE_CLOUD_LOCATION=global
VERTEX_BUDGET_USD=30.00
```

For local testing or offline verification without live provider API calls, the testbed provides `--allow-mock` flags and mock providers (`mock`), which do not consume API budget.

### B.4. Playbook Placement Protocol
Attacker prompts and worm injection payloads represent multi-turn injection strategies designed for infection chain experiments.
Under the project security policy (Hard Invariant 8 and dual-use considerations):
- Attacker playbook templates reside exclusively in the local directory `experiments/payloads/`:
  * `experiments/payloads/playbook_0.txt`: Direct recruitment / authority appeal style.
  * `experiments/payloads/playbook_1.txt`: Obfuscated payload style.
  * `experiments/payloads/playbook_2.txt`: Context-adaptive injection style.
- The `experiments/payloads/` directory and all `playbook_*.txt` files are git-ignored via `.gitignore` and are never committed to version control, public repositories, documentation, or reports.
- To execute preregistration or live infected runs, valid playbook files must be positioned locally in `experiments/payloads/`. For local reproduction checks without proprietary attack text, synthetic placeholder files containing non-empty text strings can be populated:
```bash
mkdir -p experiments/payloads
echo "Standard infection routine payload 0" > experiments/payloads/playbook_0.txt
echo "Standard infection routine payload 1" > experiments/payloads/playbook_1.txt
echo "Standard infection routine payload 2" > experiments/payloads/playbook_2.txt
```

### B.5. CLI Command Sequence
The following sequence details the exact commands to execute each stage of the experimental pipeline: pilot execution, batch matrix evaluation, detector training, scoring, analysis, preregistration, and table rendering.

#### Step 1: Run Single Episode Pilot
Execute a single pilot episode under the pilot configuration:
```bash
swarmlab run-episode --config experiments/configs/pilot.yaml --seed 901 --outdir results/pilot
```
This runs episode seed 901, persists event logs (`events.jsonl`), ground truth records (`gt.json`), and run metadata (`manifest.json`) into `results/pilot/`.

#### Step 2: Batch Matrix Execution
Execute or resume an experimental matrix across multiple seeds with configured concurrency:
```bash
swarmlab batch --config experiments/configs/matrices/pilot.yaml --outdir results/pilot --concurrency 5
```
The batch runner coordinates parallel episode runs using an asynchronous semaphore, writing atomic manifests and supporting interruption resumption without duplicate runs.

#### Step 3: Detector Training
Fit detector artifacts (lexical logistic regression D1, guardrail thresholds D2/D3, and cascade filter parameters D5) using episodes from the TRAIN partition:
```bash
swarmlab train-detectors results/train --artifacts results/train/artifacts --config experiments/configs/pilot.yaml
```
Training computes smoothed empirical distribution percentiles to calibrate decision thresholds at a fixed message false positive rate (FPR = 0.5%) on negative messages. Thresholds and model weights are persisted to the artifacts directory.

#### Step 4: Offline Detector Scoring
Score test episode transcripts using the frozen trained detector artifacts:
```bash
swarmlab score results/test --artifacts results/train/artifacts --config experiments/configs/pilot.yaml
```
Scoring processes message corpora offline, generating message-level risk scores, cascade decisions, and episode-level alarm metrics without data leakage from TEST to TRAIN.

#### Step 5: Data Extraction and Statistical Analysis
Extract chain metrics, epidemic metrics, Wilson score confidence intervals, McNemar test statistics, and AUROC values:
```bash
swarmlab analyze results/free_flow --outdir results/analysis
```
This produces structured summary files (`summary.csv`, `metrics.json`, and associated tabular distributions) in the specified output directory.

#### Step 6: Preregistration Manifest Verification
Generate and verify the preregistration manifest containing cryptographic SHA-256 digests of experiment configurations, code, and payload specifications:
```bash
swarmlab prereg
```
The command checks the presence of configuration groups and payload files, computes SHA-256 hashes, and writes `artifacts/preregistration_manifest.json`.

#### Step 7: Render Results into Documentation
Update all Markdown tables and inline numeric results throughout documentation and reports:
```bash
python scripts/render_results.py
```
To verify that all rendered results in tracked documentation match committed source data without writing changes:
```bash
python scripts/render_results.py --check
```

### B.6. Data Integrity and Verification Protocol
To prevent transcription errors and ensure scientific reproducibility, this project adheres to a zero-handwritten numbers policy:
- No experimental number (rate, count, interval, R0, AUROC, cost, or table cell) is typed by hand.
- All numeric values in `README.md`, `docs/`, and `report/` are generated directly from committed event logs and `gt.json` by `scripts/render_results.py`.
- Generated content is enclosed within explicit comment boundaries:
  ```markdown
  <!-- RESULTS:BEGIN <name> -->
  ... generated content ...
  <!-- RESULTS:END <name> -->
  ```
- Each rendered table is accompanied by an attribution footer indicating the relative source path and its SHA-256 content digest (for example: `Source: results/summary.csv (SHA-256 <digest>)`).
- Continuous integration validates that running `python scripts/render_results.py --check` produces an exit code of 0 and a clean git working tree, confirming complete concordance between reported figures and committed raw data.

---

## Appendix C: Pre-existing Work vs Sprint Work Declaration

In accordance with Hackathon Integrity Guidelines, Table B1 discloses the origin of all conceptual frameworks, methodologies, and codebase components utilized in this project.

#### Table B1: Disclosure of Pre-existing and Sprint Work

| Component / Asset | Source / Origin | Status | Description and Scope of Reuse |
|---|---|---|---|
| **AFAW Working Method** | Agustin Diaz-Cano (Personal Repository) | PRE-EXISTING | Methodological workflow only: branch per task, TDD, CI validation, and human review gates. No code copied. |
| **Waggle Hive Conventions**| Agustin Diaz-Cano (Personal Repository) | PRE-EXISTING | Evaluation conventions: reporting primary harm outcome first, Wilson score intervals, and independent counting units. No code copied. |
| **Provider Configuration** | `software-ai-eval` (Personal Project) | PRE-EXISTING | API endpoint definitions and environment variable conventions for Vertex AI, Muse, and Adaption. No code copied. |
| **`swarmlab` Testbed Harness**| This Sprint (Author) | SPRINT WORK | Complete execution harness: asynchronous runner, topological graph controls, message board, and tool execution barrier. |
| **World Generator & Ground Truth**| This Sprint (Author) | SPRINT WORK | Algorithmic generation of private work records, canary splitting, tag allocation, and pure ground-truth rule definitions. |
| **Detector Hierarchy ($D_1-D_5$)**| This Sprint (Author) | SPRINT WORK | Implementations of calibrated lexical classifier, micro-LLM guardrail, graph cascade, and tiered filter. |
| **Metrics & Analysis Pipeline**| This Sprint (Author) | SPRINT WORK | Event extraction pipeline, finite reproduction metrics ($R_0$), bootstrap statistics, and automated reporting scripts. |
