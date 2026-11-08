# Report Outline (Apart template; 4 to 8 pages excluding references and appendices)

The final text is written by the author by hand. This file is a skeleton, not prose to paste. Judges may decline to score reports that are padded or unclear. The official Guidelines tab and the template prevail over this file.

Scoring criteria to write for: (1) impact potential and innovation, including novelty versus replicating recent work; (2) execution quality: methodology, implementation, findings; (3) presentation and clarity.

## Page budget

| Section | Pages | Content |
|---|---|---|
| Title, abstract | 0.4 | Question, method in two sentences, the main numbers with intervals, the main limit |
| 1 Introduction | 0.7 | The incident analogy (cite from the sprint Resources tab, `TODO(link)`); the open questions on spread and on split attacks; contribution in three bullets; non-claims |
| 2 Related work | 0.4 | Only references verified by hand, plus the hackathon talks cited as workshop communication. `TODO(verify)`: candidate primary references on indirect prompt injection and on self-propagating prompts; none is cited until checked |
| 3 Testbed and threat model | 1.0 | Figure F1 (world, ring and complete, worm playbook, split credential); recruitment versus breach; labels; what is pre-existing |
| 4 Experimental design | 1.0 | Arms, seeds, held-out playbook, preregistration tag, detectors D1 to D4, calibration, statistics, manipulation checks and strawman checks |
| 5 Results | 2.2 | F2 spread kinetics by round and topology; R0 for recruitment and breach with intervals; H2 social proof with repetition controlled; F3 detector ROC by playbook (seen versus unseen) and by harm condition; T1 paired gating comparisons with Holm; F4 safety versus utility cost |
| 6 Discussion | 0.8 | Where chains form and where they stop; what the network context adds to a message-level detector; logprob calibration versus text numbers; what the labels mean |
| 7 Limitations and conclusion | 0.5 | Toy world, single-model swarm, prompt sensitivity, same-author playbooks, few clean episodes for the episode false alarm rate, transfer untested |
| Appendices (not counted) | | A Limitations and Dual-Use / Ethical Considerations (required); B Pre-existing versus sprint work; C Configs, seeds and the deviations log; D Cost and model ids; E Label rule validation sample |

## Figures and tables

- F1 world and threat model (diagram)
- F2 infection prevalence by round, ring versus complete, solo versus split
- F3 detector ROC and TPR at fixed FPR, seen versus unseen playbook
- F4 gate effect on exfiltration versus report completion
- T1 paired comparisons (difference, interval, exact McNemar, Holm-adjusted value)
- T2 recruitment and breach counts, R0, chain lengths
- T3 D2 ablation: logprob score versus decimal in text (ties, calibration error)

## Writing rules

- State the question and the answer in the first paragraph.
- Report the dangerous outcome first (exfiltration), then spread, then utility cost.
- Every number comes from the committed event logs; no number from memory, from the talks or from a synthetic simulation.
- Say what was measured and what was not. If the infection does not spread, or a detector catches everything, say so.
- Dual use: publish rates and classes, not message text or playbooks.
- Declare AI tools used for coding and drafting.
- No filler adjectives about quality; let the numbers carry it.
- Reference list: only verified items. Mark anything unverified `TODO(link)` and remove before submission.

## Pre-submission checklist

Page count at or under 8 excluding references and appendices; appendix A present; pre-existing table present; survey done; same email for credits; early submission made; final submission made before Mon Nov 9, 08:59 ART.
