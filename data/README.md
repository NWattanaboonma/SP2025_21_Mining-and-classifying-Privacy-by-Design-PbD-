# Data

The project produced about **500 MB** of raw data (683,548 collected issues). That is too large to
hand in with the source code, so the raw collections are **not** included in this folder.
Everything needed to understand and re-run the later stages **is** included.

## Included in the repository

| File | Location | What it is |
|---|---|---|
| PbD taxonomy | `05_rag_pipeline/data/PbD Issues Taxonomy.json` | final taxonomy, 60 sub-categories (RQ1) |
| Ground-truth knowledge base | `05_rag_pipeline/data/Ground_data.{xlsx,json}` | 308 annotated issues (80 % split) |
| Test set | `06_evaluation/Testset.xlsx` | 77 annotated issues (20 % split) |
| Coder annotations + agreement | `04_annotation/` | both coders' labels, percent-agreement results |
| Domain keywords | `01_keywords/Keyword_domain.md` | final keyword lists |
| Model outputs | `06_evaluation/Recall_data_Excel/` | outputs of the 12 configurations used in the report |
| Recall@K results | `06_evaluation/EVA_RECALL/`, `Summary_Averages.txt` | evaluation results and chart |

## Not included (large) - stored separately

| Item | Produced by | Expected location if you re-create it |
|---|---|---|
| Collected repositories (`found_repositories_*.csv`) | `02_collect_repositories/` | `data/raw/repositories/` |
| Raw issues per domain (`issues_<Domain>.csv/.json`) | `03_collect_issues/1_get_issues.py` | `data/raw/issues/` |
| Filtered issues (`*_Only_E_No_Empty.csv`, `*_mapped.csv`) | `03_collect_issues/2-4` | `data/raw/issues/` |
| Randomly sampled issues for annotation (385) | `04_annotation/1_random_sample_issues.py` | `04_annotation/` |

`data/raw/` is listed in `.gitignore`, so large files placed there are never committed by accident.

**Totals from the report (Table 5.3):**

| Domain | Repositories collected | After cleaning | Issues collected | After cleaning |
|---|---:|---:|---:|---:|
| General | 8,945 | 4,763 | 469,000 | 283,674 |
| Government | 935 | 514 | 38,632 | 28,143 |
| Health | 1,419 | 839 | 19,772 | 13,641 |
| IoT | 7,146 | 3,963 | 156,144 | 109,527 |
| **Total** | **18,445** | **10,079** | **683,548** | **434,985** |

## Where to get the large files

**Google Drive folder "Data_Final" (view only):** <https://drive.google.com/drive/folders/1FonTJTjPpYDcZgAXEywn3yEw-WoVjkAl?usp=sharing>

It contains:

- the collected GitHub repositories (about 10,000 after cleaning - 10,079 in Table 5.3)
- all collected issue reports, both raw and after each cleaning step (English only, no empty body, keyword-mapped)

To re-run a later step with this data, download the files you need and put them in `data/raw/`
(repositories in `data/raw/repositories/`, issues in `data/raw/issues/`), or run the script from the folder that holds the file.
The folder is view-only: download a copy, do not request edit access.
