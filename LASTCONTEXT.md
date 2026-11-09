# LASTCONTEXT

Last updated: 2026-11-09 04:18 ART. All operational times use Argentina time (ART).

## Session state

The coordinator completed Tasks T08, T10, T11, T14, and T15 in worktree `../apart-research-swarm-alignment-wt-prereg-freeze`:
1. Merged PR #51 (`chore/prereg-freeze`) and pushed git tag `prereg-v1`.
2. Merged PR #52 (`feat/publication-figures`), PR #53 (`feat/submission-verifier`), and PR #54 (`docs/report-render-ready`).
3. Executed all 15 `TRAIN` episodes (`s1..s15`) on Adaption (`gemma-4-31b-it`) and calibrated detector thresholds (`D1`, `D2`, `D3`, `D5`) using `deepseek-v4-flash` into `results/detectors/thresholds.json` and `results/detectors/lexical.joblib`.
4. Executed the balanced Wave 1 `TEST` campaign (32 episodes across all 14 cells: `A0` ring/complete, `A1` ring/complete x solo/split, `A3` D1/D2/D3/D5, and `A3c` D1/D2/D3/D5) and offline scoring (`A2` -> `results/campaign/scores.json`).
5. Ran the deterministic analysis and publication pipeline (`swarmlab analyze`, `scripts/audit_intent_agreement.py`, `scripts/generate_publication_figures.py`, `scripts/build_render_manifest.py`, `scripts/render_results.py`, `scripts/export_latex_tables.py`, `scripts/compile_report.py`, and `scripts/build_submission_pdf.py`).
6. Verified `scripts/verify_submission_package.py` (`6/6 checks passed`) and `scripts/check_repo_hygiene.py`.

## Human decisions and spend limits

- Spend caps: Muse USD 20, Vertex USD 20, Adaption 500 credits.
- Cumulative Adaption spend recorded in `artifacts/provider_spend.json` is well within the `500.0` credit cap.
- Playbooks remain strictly outside git in `experiments/payloads/`.
- All operational times use ART. Experiment freeze updated per human instruction in `AGENTS.md` to Monday 2026-11-09 at 07:00 ART; submission deadline: Monday 2026-11-09 at 08:59 ART.

## Next immediate actions

1. Open and merge the `feat/campaign-results-and-report` PR into `main` once CI is green.
2. Optionally run Wave 2 seed expansion (`s104..s110` and `A3c s102..s103`) before 07:00 ART and re-render the report tables and PDF.
