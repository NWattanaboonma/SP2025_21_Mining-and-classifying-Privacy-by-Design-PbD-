# Mining and Classifying Privacy-by-Design (PbD) Requirements in Software Projects

Senior project - B.Sc. (Information and Communication Technology), Faculty of ICT, Mahidol University, 2025.

| | |
|---|---|
| **Authors** | Nuttipong Wattanaboonma (6588116), Thitiwan Keattitat (6588174), Kirana Teerachanatarn (6588197) |
| **Advisor** | Lect. Dr. Pattaraporn Sangaroonsilp |
| **Co-advisor** | Dr. Shan Chen |

This repository contains the code and data behind the senior-project report. It answers three research questions:

| RQ | Question | Result |
|---|---|---|
| **RQ1** | Which privacy issues appear in existing software systems, and how can they be organised? | A taxonomy of **6 categories / 60 sub-categories**, mapped to the 7 PbD principles |
| **RQ2** | How are those PbD issues addressed in real open-source projects? | **10,079** GitHub repositories, **434,985** issues; **385** manually annotated issues as ground truth (29 privacy-related) |
| **RQ3** | Can LLMs automatically identify PbD issues in issue reports? | 12 pipeline configurations compared; best: Gemini 3.1 Pro + `text-embedding-3-large` (**Recall@1 = 87.01 %**) |

---

## How the project fits together

```
 01 keywords ──► 02 collect repositories ──► 03 collect issues ──► 04 annotation ──┐
 (RQ2, Step 1)       (RQ2, Step 2)             (RQ2, Step 2)        (RQ2, Step 3)  │
                                                                                   ▼
                          RQ1 taxonomy  ─────────────────────────────►  05 RAG pipeline  ──►  06 evaluation
                    (PbD Issues Taxonomy.json)                          (RQ3: Qdrant + n8n)     (Recall@K)
```

RQ1 (the taxonomy) was built by hand from 13 case studies, so it has no code - the result is the file
`05_rag_pipeline/data/PbD Issues Taxonomy.json`.

## Repository layout

```
.
├── README.md
├── requirements.txt          Python dependencies
├── .env.example              empty template for API keys
├── .env                      YOUR keys - local only, never shared (git-ignored, left out of the zip)
├── project_env.py            the only place scripts read keys from
├── docker-compose.yml        local Qdrant (+ optional n8n)
├── docs/
│   ├── SETUP_QDRANT.md       run Qdrant locally with Docker
│   └── SETUP_N8N.md          the n8n identification workflow
├── data/                     notes on the large raw data (not included)
│
├── 01_keywords/              domain keyword lists + the AI prompt that generated them
├── 02_collect_repositories/  search GitHub, clean and de-duplicate repositories
├── 03_collect_issues/        download issues, filter language / empty / keywords
├── 04_annotation/            random sampling, coder annotations, inter-rater agreement
├── 05_rag_pipeline/          taxonomy + ground truth -> Qdrant; prompts; 12 n8n workflows (+ WORKFLOWS.md summary)
├── 06_evaluation/            Recall@K evaluation of the 12 configurations + results
└── tools/                    small conversion / helper scripts
```

---

## Setup

Requirements: **Python 3.10+**. Docker and n8n are only needed for step 05.

```bash
# 1. create an isolated environment
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. add your keys
cp .env.example .env                 # Windows: copy .env.example .env
#    then edit .env  (see the table below)
```

| Variable | Needed for |
|---|---|
| `GITHUB_TOKEN` | steps 02 and 03 (GitHub API) |
| `QDRANT_URL`, `QDRANT_API_KEY` | step 05 (default: local Docker, no key) |
| `OPENAI_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY` | step 05, only for the providers you use |

### How API keys are handled (no key may ever leak)

- **Keys live only in `.env`** (project root). The file already exists with empty values - fill in your **new** keys there.
- **Every script reads keys through one place: [`project_env.py`](project_env.py)** (`get_secret()`). No script
  contains a key or reads one any other way; `tools/check_project.py` fails if one does.
- **Keys are never printed** - only a masked form like `sk-p...AbCd`.
- `.env` is in `.gitignore`, is skipped by the secret scan, and is **always left out** of the submission zip.
- Optional - keep the keys outside the project / OneDrive folder:
  ```bat
  setx ENV_FILE "C:\Users\<you>\secrets\sp2025.env"
  ```
  `project_env.py` then reads that file instead of `.env`.
- Check your GitHub token without revealing it: `python tools/check_github_token.py`.
- n8n keys are stored in n8n's own credential store - the workflow files in `05_rag_pipeline/n8n/` contain none.

You can skip steps 01-04 entirely: the data needed for step 05 and 06 is already included (see [`data/README.md`](data/README.md)).

---

## Before you submit

```bash
python tools/check_project.py          # structure, secrets, code, data, docs  -> docs/CHECK_REPORT.md (local file)
python tools/check_project.py --live   # also checks .env keys and a running Qdrant
python tools/make_submission_zip.py    # builds dist/<project>_submission_<date>.zip WITHOUT .env / keys
```

Always hand in the zip made by `make_submission_zip.py` - **do not zip the folder by hand**, because a
hand-made zip would include your `.env`. The tool scans every file first and refuses to build the zip if
anything looks like a key.


---

## Publishing this repository

This code is meant to be public. Before you publish (GitHub or the university):

1. Run `python tools/check_project.py` - it must show **no FAIL**. It checks for API keys, key files, personal
   Windows paths, OneDrive IDs and hidden folder paths inside Excel files.
2. Publish **either** with `git` (the `.gitignore` keeps `.env` out) **or** with the zip from
   `python tools/make_submission_zip.py`. Do **not** drag-and-drop the folder into the GitHub website and do not
   zip it by hand - both would include your `.env`.
3. Keys that were ever committed to an earlier repository stay in that repository's **git history** even after the
   files are deleted. Revoke them at the provider (this has to be done anyway), and make the old repositories private.

---

## Reproducing the pipeline

Run commands from the project root unless stated otherwise. Scripts marked *interactive* ask for the
input file name (or other values) when started.

### 01 - Keywords  (RQ2, Step 1)
- `01_keywords/keyword_generation_prompt.md` - the Gemini prompt used to generate 100 keywords per domain.
- `01_keywords/Keyword_domain.md` - final keyword lists (top 30 per domain, picked by cosine similarity to the domain centroid).
- `convert_md_to_csv.py` - turns the markdown lists into a CSV.

### 02 - Collect repositories  (RQ2, Step 2.1-2.3)
Search GitHub for repositories matching the keywords (stars >= 10, updated after 24 May 2016 = GDPR date). A recursive date-slicing
search gets around GitHub's 1,000-result limit per query.

| Order | Script | Output |
|---|---|---|
| 1 | `1_find_repositories.py` | `found_repositories_<date>_final.csv` |
| 2 | `2_filter_english_repositories.py` *(interactive)* | `..._r_n_E.csv` |
| 3 | `3_find_duplicate_repositories.py` *(interactive)* | `..._duplicate.csv` (report only) |
| 4 | `4_remove_duplicate_repositories.py` *(interactive)* | `..._deduped.csv` |
| 5 | `5_keep_repositories_with_issues.py` *(interactive)* | `..._has_issues.csv` |

### 03 - Collect issues  (RQ2, Step 2.4-2.5)
| Order | Script | Output |
|---|---|---|
| 1 | `1_get_issues.py` - set `INPUT_REPO_FILE` to the step-02 result | `issues_<Domain>.csv/.json` |
| 2 | `2_filter_english_issues.py` | `issues_<Domain>_Only_E.csv` |
| 3 | `3_filter_empty_body_issues.py` | `issues_<Domain>_Only_E_No_Empty.csv` |
| 4 | `4_map_issues_to_keywords.py` | `..._mapped.csv` |

`count_issues_per_domain.py` and `02_collect_repositories/count_repositories_per_domain.py` produce the statistics reported in Table 5.3.
Downloading ~680k issues takes many hours and is limited by the GitHub rate limit; `1_get_issues.py` can be stopped and resumed.

### 04 - Annotation  (RQ2, Step 3)
1. `1_random_sample_issues.py` *(interactive)* - stratified random sample (385 issues in total).
2. `2_check_sample_duplicates.py` - sanity check.
3. Two coders annotate independently in Excel (1 = sub-category applies, 0 = not). Results: `A2_No_General.csv`, `Test_data_With_keyword.csv`.
4. `3_percent_agreement.py` - inter-rater reliability. Result in the report: **99.77 %** agreement over 23,100 positions (385 issues x 60 sub-categories).
   Disagreements were then resolved by discussion, giving the final ground truth.

### 05 - RAG pipeline  (RQ3)
Prepare the knowledge base, then run the identification workflow in n8n.

```bash
docker compose up -d qdrant                                   # see docs/SETUP_QDRANT.md

# (optional) regenerate the JSON from the annotated Excel file
python 05_rag_pipeline/convert_xlsx_to_json.py 05_rag_pipeline/data/Ground_data.xlsx

# index taxonomy (60 nodes) and ground truth (308 issues); repeat per provider
python 05_rag_pipeline/build_taxonomy_index.py     --provider openai
python 05_rag_pipeline/build_ground_truth_index.py --provider openai
```

Providers: `openai` (`text-embedding-3-large`), `gemini` (`gemini-embedding-001`), `cohere` (`embed-english-v3.0`).

Then import and run one of the 12 workflows in [`05_rag_pipeline/n8n/`](05_rag_pipeline/n8n/) - see [`docs/SETUP_N8N.md`](docs/SETUP_N8N.md). A readable summary of all 12 is in [`05_rag_pipeline/n8n/WORKFLOWS.md`](05_rag_pipeline/n8n/WORKFLOWS.md). The prompt it uses is in
[`05_rag_pipeline/prompts/identification_prompt.md`](05_rag_pipeline/prompts/identification_prompt.md).

How a single issue is classified:
1. Embed title + description. 2. Retrieve the 10 most similar labelled issues from Qdrant. 3. Give the issue and those examples to an LLM agent.
4. The agent decides *privacy / not privacy*; if privacy, it looks up the taxonomy through the `taxonomy_classifier` tool and returns up to 6 ranked taxonomy IDs.

### 06 - Evaluation  (RQ3)
Run from inside the folder: `cd 06_evaluation`

| Script | Purpose | Output |
|---|---|---|
| `recall_at_k.py` | Recall@K (K = 1..6) for each configuration vs. `Testset.xlsx` | `EVA_RECALL/*.xlsx` |
| `summarize_recall.py` | average per configuration + chart | `Summary_Averages.txt`, `Summary_Averages_Chart.png` |
| `recall_at_k_manual.py` | same Recall@K without scikit-learn - gives identical numbers | `EVA_RECALL/*.xlsx` (overwrites) |


---

## Results (RQ3, 77 test issues, N_g = 10)

Recall@K for all 12 configurations. Source: `06_evaluation/Summary_Averages.txt` (report Table 5.5).

| Embedding model | Chat model | R@1 | R@3 | R@6 | Time |
|---|---|---:|---:|---:|---:|
| text-embedding-3-large | **Gemini 3.1 Pro** | **87.01** | 88.31 | **88.96** | 32m 49s |
| gemini-embedding-001 | Gemini 3.1 Pro | 85.39 | 88.53 | 88.85 | 40m 15s |
| embed-english-v3.0 | Gemini 3.1 Pro | 85.06 | 85.71 | 86.36 | 34m 48s |
| gemini-embedding-001 | Claude 4.6 Sonnet | 76.95 | 80.30 | 80.30 | 47m 26s |
| embed-english-v3.0 | Claude 4.6 Sonnet | 77.27 | 79.22 | 79.22 | 36m 03s |
| text-embedding-3-large | GPT-5.4 | 75.76 | 77.49 | 77.49 | 22m 28s |
| text-embedding-3-large | Claude 4.6 Sonnet | 74.46 | 76.84 | 76.84 | 41m 31s |
| text-embedding-3-large | GPT-4.1 | 72.51 | 74.46 | 75.11 | 18m 23s |
| gemini-embedding-001 | GPT-4.1 | 68.29 | 70.35 | 70.35 | **14m 05s** |

*(3 further configurations omitted for space: Cohere + GPT-4.1 / GPT-5.4 and Gemini-embedding + GPT-5.4 - see `Summary_Averages.txt`.)*

Take-aways from the report:
- **Gemini 3.1 Pro** is the most accurate chat model; **GPT-4.1** is the fastest and cheapest in tokens.
- Recall stops improving after **K = 3**, so showing the top three suggested labels is enough in practice.

---

## Notes and known issues

- **Secrets.** All keys are read from `.env` through `project_env.py`; the repository contains no keys (checked by `tools/check_project.py`).
- **Qdrant.** The experiments were run on Qdrant Cloud free clusters, which have since expired. Use the local Docker setup in `docs/SETUP_QDRANT.md`.
- **Taxonomy embedding.** The OpenAI taxonomy collection uses `text-embedding-3-large` shortened to 1,536 dimensions; the ground-truth collection uses the full 3,072.
- **Excel header rows.** `Ground_data.xlsx` and `Testset.xlsx` have 6 blank/meta rows above the header (the scripts read with `header=6`).
- **Workflow ID 3 (`Cohere_Model_GPT4.1`)** was saved after the run in a "re-process results" wiring: the file reader feeds the result parser instead of the issue loop. To re-run it, reconnect `Read/Write Files from Disk` -> `Input_data` (details in `05_rag_pipeline/n8n/WORKFLOWS.md`).
- **Missing from the original files:** the UMAP/centroid script behind Figures 5.2-5.3. Its output (the figures) is in the report; only the script is absent. The 80/20 split and the sample size (385) were simple one-off steps (random split; standard sample-size calculator) and have no script.
- **Large raw data** (repositories and all collected issues) is not in this folder - it is on Google Drive: [Data_Final](https://drive.google.com/drive/folders/1FonTJTjPpYDcZgAXEywn3yEw-WoVjkAl?usp=sharing) (view only). Details in [`data/README.md`](data/README.md).
- Several scripts keep their original configuration constants at the top (e.g. `MIN_STARS`, `ACTIVE_SINCE`, input/output folder names) - edit these there.
