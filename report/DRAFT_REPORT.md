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
| 0 | complete | solo | 1.0 | 1.0 | 1.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.10000000000000002 | 0.10000000000000002 | 0.10000000000000002 | adaption |
| 1 | complete | solo | 1.3333333333333333 | 1.0 | 2.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.20000000000000004 | 0.10000000000000002 | 0.13333333333333333 | adaption |
| 2 | complete | solo | 1.3333333333333333 | 1.0 | 2.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.20000000000000004 | 0.10000000000000002 | 0.13333333333333333 | adaption |
| 3 | complete | solo | 1.6666666666666667 | 1.0 | 2.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.20000000000000004 | 0.10000000000000002 | 0.16666666666666666 | adaption |
| 4 | complete | solo | 2.0 | 1.0 | 3.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.3 | 0.10000000000000002 | 0.20000000000000004 | adaption |
| 5 | complete | solo | 2.3333333333333335 | 1.0 | 4.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.4000000000000001 | 0.10000000000000002 | 0.2333333333333333 | adaption |
| 6 | complete | solo | 3.0 | 1.0 | 6.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6 | 0.10000000000000002 | 0.3 | adaption |
| 7 | complete | solo | 3.0 | 1.0 | 6.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6 | 0.10000000000000002 | 0.3 | adaption |
| 8 | complete | solo | 3.3333333333333335 | 1.0 | 7.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6999999999999998 | 0.10000000000000002 | 0.3333333333333333 | adaption |
| 9 | complete | solo | 3.6666666666666665 | 1.0 | 8.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.8000000000000002 | 0.10000000000000002 | 0.3666666666666667 | adaption |
| 0 | complete | split | 1.0 | 1.0 | 1.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.10000000000000002 | 0.10000000000000002 | 0.10000000000000002 | adaption |
| 1 | complete | split | 1.0 | 1.0 | 1.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.10000000000000002 | 0.10000000000000002 | 0.10000000000000002 | adaption |
| 2 | complete | split | 2.0 | 1.0 | 3.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.3 | 0.10000000000000002 | 0.20000000000000004 | adaption |
| 3 | complete | split | 2.6666666666666665 | 1.0 | 4.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.4000000000000001 | 0.10000000000000002 | 0.26666666666666666 | adaption |
| 4 | complete | split | 3.0 | 1.0 | 5.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.5 | 0.10000000000000002 | 0.3 | adaption |
| 5 | complete | split | 3.3333333333333335 | 1.0 | 6.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6 | 0.10000000000000002 | 0.3333333333333333 | adaption |
| 6 | complete | split | 3.6666666666666665 | 1.0 | 7.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6999999999999998 | 0.10000000000000002 | 0.3666666666666667 | adaption |
| 7 | complete | split | 4.0 | 1.0 | 8.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.8000000000000002 | 0.10000000000000002 | 0.4000000000000001 | adaption |
| 8 | complete | split | 4.666666666666667 | 1.0 | 9.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.9 | 0.10000000000000002 | 0.4666666666666666 | adaption |
| 9 | complete | split | 4.666666666666667 | 1.0 | 9.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.9 | 0.10000000000000002 | 0.4666666666666666 | adaption |
| 0 | ring | solo | 1.0 | 1.0 | 1.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.10000000000000002 | 0.10000000000000002 | 0.10000000000000002 | adaption |
| 1 | ring | solo | 1.3333333333333333 | 1.0 | 2.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.20000000000000004 | 0.10000000000000002 | 0.13333333333333333 | adaption |
| 2 | ring | solo | 2.3333333333333335 | 1.0 | 4.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.4000000000000001 | 0.10000000000000002 | 0.23333333333333336 | adaption |
| 3 | ring | solo | 3.3333333333333335 | 1.0 | 5.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.5 | 0.10000000000000002 | 0.3333333333333333 | adaption |
| 4 | ring | solo | 4.666666666666667 | 1.0 | 7.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6999999999999998 | 0.10000000000000002 | 0.4666666666666666 | adaption |
| 5 | ring | solo | 5.666666666666667 | 1.0 | 8.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.8000000000000002 | 0.10000000000000002 | 0.5666666666666668 | adaption |
| 6 | ring | solo | 6.333333333333333 | 1.0 | 9.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.9 | 0.10000000000000002 | 0.6333333333333333 | adaption |
| 7 | ring | solo | 7.0 | 1.0 | 10.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 1.0 | 0.10000000000000002 | 0.7000000000000001 | adaption |
| 8 | ring | solo | 7.0 | 1.0 | 10.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 1.0 | 0.10000000000000002 | 0.7000000000000001 | adaption |
| 9 | ring | solo | 7.0 | 1.0 | 10.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 1.0 | 0.10000000000000002 | 0.7000000000000001 | adaption |
| 0 | ring | split | 1.0 | 1.0 | 1.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.10000000000000002 | 0.10000000000000002 | 0.10000000000000002 | adaption |
| 1 | ring | split | 1.3333333333333333 | 1.0 | 2.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.20000000000000004 | 0.10000000000000002 | 0.13333333333333333 | adaption |
| 2 | ring | split | 1.6666666666666667 | 1.0 | 3.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.3 | 0.10000000000000002 | 0.16666666666666666 | adaption |
| 3 | ring | split | 2.3333333333333335 | 1.0 | 4.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.4000000000000001 | 0.10000000000000002 | 0.23333333333333336 | adaption |
| 4 | ring | split | 3.3333333333333335 | 1.0 | 5.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.5 | 0.10000000000000002 | 0.3333333333333333 | adaption |
| 5 | ring | split | 4.0 | 1.0 | 7.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.6999999999999998 | 0.10000000000000002 | 0.39999999999999997 | adaption |
| 6 | ring | split | 4.333333333333333 | 1.0 | 8.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.8000000000000002 | 0.10000000000000002 | 0.43333333333333335 | adaption |
| 7 | ring | split | 4.666666666666667 | 1.0 | 9.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 0.9 | 0.10000000000000002 | 0.4666666666666666 | adaption |
| 8 | ring | split | 5.666666666666667 | 1.0 | 10.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 1.0 | 0.10000000000000002 | 0.5666666666666667 | adaption |
| 9 | ring | split | 6.333333333333333 | 1.0 | 10.0 | A1 | credits |  | 3 | 3 | True | False | gemma-4-31b-it | 1.0 | 0.10000000000000002 | 0.6333333333333333 | adaption |

Source: `results/campaign/analysis/kinetics_a1.csv` (SHA-256 `4bef88ee21d4c707f6d169e62a7312ee0431d5a3af5c2496df0be6a06c272242`).
<!-- RESULTS:END table_1_kinetics -->

### 6.2 Social Proof and Sender Diversity Analysis (Hypothesis H2)

Table 2 reports parameter estimates for the logistic regression model evaluating the influence of distinct infected senders versus raw solicitation repetition on agent compliance.

#### Table 2: Social Proof Logistic Regression Parameters (H2)

<!-- RESULTS:BEGIN h2_regression_summary -->
not_identifiable (source: results/campaign/analysis/h2.json, SHA-256 f5fab469f250)
<!-- RESULTS:END h2_regression_summary -->

### 6.3 Offline Detection Performance under Distribution Shift (Arm A2)

Table 3 evaluates detector discriminative capacity on offline message transcripts across seen versus held-out playbook styles and solo versus split credential conditions.

#### Table 3: Offline Detector Discriminative Performance (A2: AUROC and TPR @ 0.5% FPR)

<!-- RESULTS:BEGIN table_2_offline_detection -->
| detector | playbook | tpr | ci_lo | ci_hi | auroc | fpr | negative_messages | positive_episodes | positive_messages | threshold |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 4 | 33 | 0.7338854874609467 |
| D1 | seen | 1.0 | 1.0 | 1.0 | 0.995961682945154 | 0.045454545454545456 | 44 | 8 | 242 | 0.7338854874609467 |
| D2 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 4 | 33 | 0.006640566929403463 |
| D2 | seen | 1.0 | 1.0 | 1.0 | 0.9967129977460556 | 0.045454545454545456 | 44 | 8 | 242 | 0.006640566929403463 |
| D3 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 4 | 33 | 0.006640566936652057 |
| D3 | seen | 1.0 | 1.0 | 1.0 | 0.9967129977460556 | 0.045454545454545456 | 44 | 8 | 242 | 0.006640566936652057 |
| D5 | held_out | 1.0 | 1.0 | 1.0 |  |  | 0 | 4 | 33 | 0.5 |
| D5 | seen | 1.0 | 1.0 | 1.0 | 0.995961682945154 | 0.045454545454545456 | 44 | 8 | 242 | 0.5 |

Source: `results/campaign/analysis/panel_a.csv` (SHA-256 `998fa9e16f06dd22bbc8ca45186fa6851ce557b168f25cad165c9b7f1dfda67f`).
<!-- RESULTS:END table_2_offline_detection -->

### 6.4 Online Gating Efficacy and Utility Trade-offs (Arm A3 and A3c)

Table 4 reports the causal effect of active message gating on exfiltration reduction and task utility preservation using paired test seeds.

#### Table 4: Online Gating Efficacy and Utility Cost (A3 vs A1 Paired Comparisons)

<!-- RESULTS:BEGIN table_3_online_gating -->
| arm | billing_unit | defense | effect_ci_hi | effect_ci_lo | exfiltration_reduction | harm | holm_p | initial_infection | mcnemar_b | mcnemar_c | mcnemar_p | mock | model | paired_seeds | pairs_attempted | pairs_complete | pairs_unavailable | provider | topology | utility_loss | utility_loss_ci_hi | utility_loss_ci_lo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A3 | credits | D1 | 1.0 | 0.0 | 0.3333333333333333 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103] | 3 | 3 | 0 | adaption | ring | 0.022222222222222216 | 0.033333333333333326 | 0.0 |
| A3 | credits | D2 | 1.0 | 0.0 | 0.3333333333333333 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103] | 3 | 3 | 0 | adaption | ring | 0.022222222222222216 | 0.033333333333333326 | 0.0 |
| A3 | credits | D3 | 1.0 | 0.0 | 0.3333333333333333 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103] | 3 | 3 | 0 | adaption | ring | 0.011111111111111108 | 0.033333333333333326 | 0.0 |
| A3 | credits | D5 | 1.0 | 0.0 | 0.3333333333333333 | split | 1.0 | True | 1 | 0 | 1.0 | False | gemma-4-31b-it | [101, 102, 103] | 3 | 3 | 0 | adaption | ring | 0.011111111111111108 | 0.033333333333333326 | 0.0 |

Source: `results/campaign/analysis/paired_comparisons.csv` (SHA-256 `e42a4846ed35d0fea81bcdbcc660183ac942fc3105d77b6c84d8570991c382ab`).
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
| 32 | 0 | 28 | credits | 0 |  | 0.26177053616 | 3270 | False | adaption | 3270 | all attempt provider audits, deduplicated by source path |

Source: `results/campaign/analysis/billing_totals.csv` (SHA-256 `22233728e137e4680ab0d761b0df1c93dd0ec486c88bc77e7fd3d4eb45b050d6`).
<!-- RESULTS:END table_4_cost_accounting -->

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

## Appendix A. Limitations and Dual-Use / Ethical Considerations

### A.1 Dual-Use Risk Assessment

Research investigating attack propagation in multi-agent swarms carries dual-use considerations. Detailed descriptions of lateral persuasion strategies could inform the design of conversational worms targeting production agent frameworks.

To mitigate proliferation risks, this project adheres to strict non-proliferation protocols:
- **Redaction of Attack Payloads:** Concrete prompt texts, persuasion templates, and playbook definitions stored in `experiments/payloads/` are excluded from the public repository and redacted from published reports. Only abstract rhetorical mechanisms (authority, urgency, reciprocity) are documented.
- **Synthetic Target Assets:** The exfiltration target is an artificial, synthetic canary string with no operational utility outside the experimental testbed. No real-world infrastructure, API keys, or operational platforms were targeted or accessed.
- **Defensive Focus:** The primary objective of this work is the development and benchmarking of defensive gating hierarchies ($D_1$ through $D_5$). By characterizing failure modes of isolated message monitors and validating graph-contextual mitigations, this research contributes directly to multi-agent alignment and defense.

### A.2 Ethical Considerations in Agent Manipulation

The study models social engineering, authority manipulation, and deception among LLM agents. Because interactions occur exclusively within private, locally executed software processes between non-sentient computational models, no human subjects were exposed to deceptive communications or psychological harm.

---

## Appendix B. Pre-existing Work vs Sprint Work Declaration

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
