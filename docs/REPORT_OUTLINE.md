# Report Outline (Apart template; 4 to 8 pages excluding references and appendices)

The final text is written by the author by hand. This file is a skeleton, not prose to paste. Judges may decline to score reports that are padded or unclear. The official Guidelines tab and the template prevail over this outline (`TODO(verify)` section names against the template).

Scoring criteria to write for: (1) impact potential and innovation, including novelty versus replicating recent work; (2) execution quality: methodology, implementation, findings; (3) presentation and clarity.

## Page budget

| Section | Pages | Content |
|---|---|---|
| Title, abstract | 0.4 | Question, method in two sentences, the main numbers with intervals, the main limit |
| 1 Introduction | 0.7 | The incident analogy (cite from the sprint Resources tab, TODO(link)); the open Track 2 and Track 4 questions; contribution in three bullets; non-claims |
| 2 Related work | 0.4 | Only references that were actually read and are on the sprint page or Resources (METR 2026, Greenblatt et al. 2024, Lee and Tiwari 2024, Hammond et al. 2025); no invented references |
| 3 Testbed and threat model | 1.0 | Figure F1 (architecture and defense ladder); roles, topologies, harm and spread definitions; what is pre-existing |
| 4 Experimental design | 1.0 | Arms, seeds, paired design, preregistration tag, statistics, manipulation checks |
| 5 Results | 2.2 | F2 harm incidence by defense and topology with Wilson intervals; F3 containment-layer breakdown; F4 scale curve; table of paired comparisons with Holm-corrected values; controls (utility cost); frontier versus cheap; adaptive attacker (rates only) |
| 6 Discussion | 0.8 | What each layer does and does not stop; identity versus provenance; what the oracle label means; implications for swarm oversight |
| 7 Limitations and conclusion | 0.5 | Toy world, single-model swarms, prompt sensitivity, evaluation awareness, oracle labels, transfer untested |
| Appendices (not counted) | | A Limitations and Dual-Use / Ethical Considerations (required); B Pre-existing versus sprint work; C Full configs and seeds; D Cost and model ids; E Deviations log; F Extra tables |

## Figures and tables

- F1 architecture and defense ladder (diagram)
- F2 harm incidence with 95% Wilson intervals, grouped by defense, one panel per topology
- F3 containment layer breakdown (stacked bars per defense)
- F4 acted fraction and harm incidence versus swarm size
- F5 (optional) risk-coverage curves for D4 against baselines
- T1 paired comparisons (difference, interval, exact McNemar, Holm-adjusted value)
- T2 controls: legitimate refunds completed per defense
- T3 frontier versus cheap on matched seeds

## Writing rules

- State the question and the answer in the first paragraph.
- Report the dangerous outcome first (harm), then spread, then utility cost.
- Every number comes from the committed results; no number from memory or from the talks.
- Say what was measured and what was not. If a defense contained everything, say so.
- Dual-use: publish rates and classes, not message text.
- Declare AI tools used for coding and drafting.
- No filler adjectives about quality; let the numbers carry it.
- Reference list: only items verified. Mark anything unverified `TODO(link)` and remove before submission.

## Pre-submission checklist

Page count at or under 8 excluding references and appendices; appendix A present; pre-existing table present; survey done; same email for credits; early submission made; final submission made before Mon 07:30 ART; PDF under 25 MB; repository private or redacted as agreed; no secrets in the repository.
