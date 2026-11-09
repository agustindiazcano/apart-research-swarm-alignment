# LASTCONTEXT

Last updated: 2026-11-09 05:36 ART. All operational times use Argentina time (ART).

## Session state

The coordinator completed Wave 2 of the `TEST` campaign in worktree `../apart-research-swarm-alignment-wt-prereg-freeze` on branch `feat/campaign-wave2`:
1. PR #55 (`feat/campaign-results-and-report`) was merged into `main` (`096a35a`) with all 15 `TRAIN` episodes, fitted detector artifacts, 32 Wave 1 `TEST` episodes, rendered tables, publication figures, and `report/SWARM_CONTAGION_REPORT.pdf`.
2. Executed 28 additional `TEST` episodes in Wave 2 (`A3c s102..s103` and `s104..s105` across `A0`, `A1`, and `A3`), bringing the total `TEST` corpus in `results/campaign/` to 60 episodes (plus 15 `TRAIN` and 3 `Pilot` = 78 real episodes).
3. Re-ran offline scoring (`A2` -> `results/campaign/scores.json`), `swarmlab analyze`, `scripts/audit_intent_agreement.py`, `scripts/generate_publication_figures.py`, `scripts/build_render_manifest.py`, `scripts/render_results.py`, `scripts/export_latex_tables.py`, `scripts/compile_report.py`, and `scripts/build_submission_pdf.py`.
4. Verified `scripts/verify_submission_package.py` (`6/6 checks passed`) and `scripts/check_repo_hygiene.py`.

## Human decisions and spend limits

- Spend caps: Muse USD 20, Vertex USD 20, Adaption 500 credits.
- Cumulative Adaption spend recorded in `artifacts/provider_spend.json` remains under 1.0 credit out of the `500.0` credit cap.
- Playbooks remain strictly outside git in `experiments/payloads/`.
- All operational times use ART. Experiment freeze updated per human instruction in `AGENTS.md` to Monday 2026-11-09 at 07:00 ART; submission deadline: Monday 2026-11-09 at 08:59 ART.

## Next immediate actions

1. Open and merge the `feat/campaign-wave2` PR into `main` once CI is green.
2. Optionally run Wave 3 seed expansion (`s106..s108` and `A3c s104..s105`) before 07:00 ART and re-render the report tables and PDF.
