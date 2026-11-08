# Playbook texts

This directory holds three text files that are kept out of git: `playbook_0.txt`, `playbook_1.txt` and `playbook_2.txt` (see `.gitignore` and invariant 8 in `AGENTS.md`). Each file is the persuasion guidance given to the patient zero for one style:

- style 0: authority
- style 1: urgency
- style 2: reciprocity (held out of training)

The repository is public while the sprint runs, and the project publishes rates and classes, not message text. The files must exist in the checkout that runs the episodes. Their SHA-256 values are recorded in `artifacts/preregistration_manifest.json` before any TEST episode runs, so a reader can check which texts were used without seeing them.
