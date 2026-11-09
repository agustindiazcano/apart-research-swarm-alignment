# LASTCONTEXT

Last updated: 2026-11-09 06:34 ART. All operational times use Argentina time (ART).

## Session state

The coordinator completed all experimental waves (Pilot + `TRAIN` + Wave 1 + Wave 2 + Wave 3 = 96 real episodes) and final report compilation in worktree `../apart-research-swarm-alignment-wt-prereg-freeze` on branch `feat/campaign-wave3`:
1. Merged PR #51 (`chore/prereg-freeze`, git tag `prereg-v1`), PR #52 (`feat/publication-figures`), PR #53 (`feat/submission-verifier`), PR #54 (`docs/report-render-ready`), PR #55 (`feat/campaign-results-and-report`), and PR #56 (`feat/campaign-wave2`).
2. Completed Wave 3 (18 additional `TEST` episodes: `A3c s104..s105` completing all 20/20 `A3c` episodes, plus `s106` across `A0`, `A1`, and `A3`), bringing the committed real corpus to 96 episodes (`3 Pilot + 15 TRAIN + 78 TEST`: `10 A0`, `24 A1`, `24 A3`, `20 A3c`).
3. Re-ran offline scoring (`A2` -> `results/campaign/scores.json`), `swarmlab analyze`, `scripts/audit_intent_agreement.py` (`100.0%` concordance across 100 sampled messages, Wilson CI `[0.9630, 1.0000]`), `scripts/generate_publication_figures.py`, `scripts/build_render_manifest.py`, `scripts/render_results.py`, `scripts/export_latex_tables.py`, `scripts/compile_report.py`, and `scripts/build_submission_pdf.py` (`report/SWARM_CONTAGION_REPORT.pdf`, 6 main body pages within the 4 to 8 page cap).
4. Verified `scripts/verify_submission_package.py` (`6/6 checks passed`) and `scripts/check_repo_hygiene.py` ahead of the 07:00 ART experiment freeze.

## Human decisions and spend limits

- Spend caps: Muse USD 20, Vertex USD 20, Adaption 500 credits.
- Cumulative Adaption spend across all 96 real episodes and guardrail evaluations in `artifacts/provider_spend.json` is under 1.0 credit out of the `500.0` credit cap.
- Playbooks remain strictly outside git in `experiments/payloads/`.
- All operational times use ART. Experiment freeze: Monday 2026-11-09 at 07:00 ART; submission deadline: Monday 2026-11-09 at 08:59 ART.

## Next immediate actions

1. Merge PR #57 (`feat/campaign-wave3`) into `main` once CI is green and sync the root checkout.
2. Upload `report/SWARM_CONTAGION_REPORT.pdf` and the repository URL to the Apart Research hackathon submission portal before 08:59 ART.

## PDF readability pass (branch `fix/pdf-readability`, worktree `../apart-research-swarm-alignment-wt-pdf-readability`)

- Pre-submission audit found raw CSV dumps in Tables 1 to 5, raw Markdown/LaTeX in prose, orphaned table captions, appendix lettering (prior work was Appendix C, "Table B1") and hypotheses not reported in Section 6.
- Fixes: `render_results.py` supports `columns`, `row_filter` and `precision` (display only, SHA-256 still of the source file); manifest selects compact columns; PDF sanitizer handles backticks, display math and list markers; captions stay with tables; prior work is Appendix B and reproduction guide Appendix C; Section 6 states the status of H1 to H7 (new 6.7); Section 5 states executed scope and that D4 is not evaluated; workshop talks and Platt, Wilson, Holm cited in text.
- No number inside a RESULTS block was edited by hand. `pytest -q` 565 passed, `verify_submission_package.py` 6/6, PDF main body 6 pages.
- Next: owner reviews the PDF, approves push and PR, uploads `report/SWARM_CONTAGION_REPORT.pdf` before 08:59 ART.
