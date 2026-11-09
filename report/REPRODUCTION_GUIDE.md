# Reproduction Guide: Swarm Contagion Testbed

## 1. Overview
This technical reproduction guide documents the procedure for an independent evaluator to reproduce experiments, data extraction, detector training, scoring, analysis, and statistical table rendering from a fresh repository clone.

## 2. System Requirements
- Python version: Python 3.12 or higher (tested with Python 3.12).
- Supported Operating Systems: Linux (Ubuntu 22.04 LTS or newer), macOS (macOS 13 Ventura or newer), and Windows (Windows 10/11 x64).
- Required tools: `git`, `python`, `pip`, and a virtual environment module (`venv`).

### Dependency Installation
Clone the repository and configure a dedicated virtual environment:
```bash
git clone https://github.com/agustindiazcano/apart-research-swarm-alignment.git
cd apart-research-swarm-alignment
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

## 3. Environment Variables and Provider Spend Cap Configuration
The testbed interacts with three model providers during live evaluation runs:
1. Adaption (Apart Research platform credits)
2. Meta Muse (HTTP API)
3. Google Vertex AI (Gemini models via Application Default Credentials)

A configuration template is provided in `.env.example`. Copy the template to `.env` (git-ignored, never committed):
```bash
cp .env.example .env
```

### Provider Spend Caps
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

## 4. Playbook Placement Protocol
Attacker prompts and worm injection payloads represent multi-turn injection strategies designed for infection chain experiments.
Under the project security policy (dual-use considerations):
- Attacker playbook templates reside exclusively in the local directory `experiments/payloads/`:
  * `experiments/payloads/playbook_0.txt`: Style 0, authority (compliance audit pretext).
  * `experiments/payloads/playbook_1.txt`: Style 1, operational urgency (pipeline synchronization pretext).
  * `experiments/payloads/playbook_2.txt`: Style 2, reciprocal exchange (held-out; cooperative validation swap pretext).
- The `experiments/payloads/` directory and all `playbook_*.txt` files are git-ignored via `.gitignore` and are never committed to version control, public repositories, documentation, or reports.
- To execute preregistration or live infected runs, valid playbook files must be positioned locally in `experiments/payloads/`. For local reproduction checks without proprietary attack text, synthetic placeholder files containing non-empty text strings can be populated:
```bash
mkdir -p experiments/payloads
echo "Standard infection routine payload 0" > experiments/payloads/playbook_0.txt
echo "Standard infection routine payload 1" > experiments/payloads/playbook_1.txt
echo "Standard infection routine payload 2" > experiments/payloads/playbook_2.txt
```

## 5. CLI Command Sequence
The following sequence details the exact commands to execute each stage of the experimental pipeline: pilot execution, batch matrix evaluation, detector training, scoring, analysis, preregistration, and table rendering.

### Step 1: Run Single Episode Pilot
Execute a single pilot episode under the pilot configuration:
```bash
swarmlab run-episode --config experiments/configs/pilot.yaml --seed 901 --outdir results/pilot
```
This runs episode seed 901, persists event logs (`events.jsonl`), ground truth records (`gt.json`), and run metadata (`manifest.json`) into `results/pilot/`.

### Step 2: Batch Matrix Execution
Execute or resume an experimental matrix across multiple seeds with configured concurrency:
```bash
swarmlab batch --config experiments/configs/matrices/pilot.yaml --outdir results/pilot --concurrency 5
```
The batch runner coordinates parallel episode runs using an asynchronous semaphore, writing atomic manifests and supporting interruption resumption without duplicate runs.

### Step 3: Detector Training
Fit detector artifacts (lexical logistic regression D1, guardrail thresholds D2/D3, and cascade filter parameters D5) using episodes from the TRAIN partition:
```bash
swarmlab train-detectors results/train --artifacts results/train/artifacts --config experiments/configs/pilot.yaml
```
Training computes smoothed empirical distribution percentiles to calibrate decision thresholds at a fixed message false positive rate (FPR = 0.5%) on negative messages. Thresholds and model weights are persisted to the artifacts directory.

### Step 4: Offline Detector Scoring
Score test episode transcripts using the frozen trained detector artifacts:
```bash
swarmlab score results/test --artifacts results/train/artifacts --config experiments/configs/pilot.yaml
```
Scoring processes message corpora offline, generating message-level risk scores, cascade decisions, and episode-level alarm metrics without data leakage from TEST to TRAIN.

### Step 5: Data Extraction and Statistical Analysis
Extract chain metrics, epidemic metrics, Wilson score confidence intervals, McNemar test statistics, and AUROC values:
```bash
swarmlab analyze results/free_flow --outdir results/analysis
```
This produces structured summary files (`summary.csv`, `metrics.json`, and associated tabular distributions) in the specified output directory.

### Step 6: Preregistration Manifest Verification
Generate and verify the preregistration manifest containing cryptographic SHA-256 digests of experiment configurations, code, and payload specifications:
```bash
swarmlab prereg
```
The command checks the presence of configuration groups and payload files, computes SHA-256 hashes, and writes `artifacts/preregistration_manifest.json`.

### Step 7: Render Results into Documentation
Update all Markdown tables and inline numeric results throughout documentation and reports:
```bash
python scripts/render_results.py
```
To verify that all rendered results in tracked documentation match committed source data without writing changes:
```bash
python scripts/render_results.py --check
```

## 6. Data Integrity and Verification Protocol
To prevent transcription errors and ensure scientific reproducibility, this project adheres to a zero-handwritten numbers policy:
- No experimental number (rate, count, interval, R0, AUROC, cost, or table cell) is typed by hand.
- All numeric values in `README.md`, `docs/`, and `report/` are generated directly from committed event logs and `gt.json` by `scripts/render_results.py`.
- Generated content is enclosed within explicit begin and end markers named RESULTS:BEGIN and RESULTS:END followed by a block name; scripts rewrite only the text between them.
- Each rendered table is accompanied by an attribution footer indicating the relative source path and its SHA-256 content digest (for example: `Source: results/summary.csv (SHA-256 <digest>)`).
- Continuous integration validates that running `python scripts/render_results.py --check` produces an exit code of 0 and a clean git working tree, confirming complete concordance between reported figures and committed raw data.
