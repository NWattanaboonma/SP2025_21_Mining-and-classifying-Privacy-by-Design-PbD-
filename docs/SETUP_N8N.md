# n8n workflows (RQ3 identification pipeline)

The identification pipeline (report Section 4.4.3, Figure 4.4) runs in **n8n**, a node-based
workflow tool. There is one workflow per experiment - **12 in total** - stored in
[`05_rag_pipeline/n8n/`](../05_rag_pipeline/n8n/). The table there maps each file to its report ID,
embedding model and chat model.

**To read a workflow without opening n8n**, see
[`05_rag_pipeline/n8n/WORKFLOWS.md`](../05_rag_pipeline/n8n/WORKFLOWS.md). It is generated from the
JSON files by `python tools/n8n_summary.py` - re-run that after changing a workflow.

**To see only these 12 in the n8n web UI**, type `Recall@K` in the **Search** box on the Workflows
page, or select them, add a tag (e.g. `senior-project`) and filter by that tag.

## 1. Install and start n8n

```bash
npm install -g n8n      # once (needs Node.js 18+)
n8n start               # then open http://localhost:5678
```

or with Docker: `docker compose up -d n8n` (see `docker-compose.yml`).

On Windows, run these in **Command Prompt (cmd)**. PowerShell may block `npx`/`n8n` scripts
("running scripts is disabled"); in PowerShell use `npx.cmd` / `n8n.cmd` instead.

## 2. Create the credentials

Open n8n -> **Credentials** -> **Add credential** and create:

| Credential type in n8n | Needed by | Key from |
|---|---|---|
| Qdrant API | all 12 | URL `http://localhost:6333`, no key for local Docker (`SETUP_QDRANT.md`) |
| OpenAI | `GPT_Model_*` (embedding) and every `*_GPT4.1` / `*_GPT5.4` | platform.openai.com |
| Google Gemini (PaLM) API | `Gemini_Model_*` (embedding) and every `*_Gemini*` chat | aistudio.google.com |
| Cohere | `Cohere_Model_*` | dashboard.cohere.com |
| Anthropic | every `*_Claude` | console.anthropic.com |

The workflow files contain **no keys**; after import each node shows a warning until you select
your own credential in it.

## 3. Import the workflows

n8n -> **Workflows** -> **Create** menu (or `...`) -> **Import from file** -> choose a `.json` from
`05_rag_pipeline/n8n/`. Repeat for each workflow you need.

Or all at once from the command line:

```bash
n8n import:workflow --separate --input=05_rag_pipeline/n8n
```

Then open each workflow and re-select the credentials in the nodes that show a warning.

## 4. What a workflow does (node by node)

Taken from the connections in the exported files. Node names differ slightly between workflows
(shown as "name / other name").

```
When clicking 'Execute Workflow'                 manual trigger
  -> Taxonomy JSON                               code node holding the full taxonomy (for ID -> label mapping)
  -> Read/Write Files from Disk                  reads the test-set .xlsx
  -> Input_data -> All_data_Issue                rows of the test set
  -> Loop Over Items                             one issue per iteration
       loop branch:
       -> Issue1                                 Issue_ID, Title, Body; text_to_embed = Title + Body
       -> Emedding Issue / Emedding Issue1       HTTP call to the embedding API (document mode)
       -> Search Qdrant Database / HTTP Request1 POST /collections/pbd-ground-truth-QA*/points/search, limit 10
       -> Format                                 10 hits -> "Example n: Title / Body / Correct Labels"
       -> AI Agent                               system + user prompt (prompts/identification_prompt.md)
            ├─ chat model                        Claude / Gemini / GPT node
            └─ Taxonomy tools                    Qdrant vector store as a tool, pbd-taxonomy-QA*, top-K 10
                 └─ Embeddings <provider>        embeds the agent's search keywords
       -> back to Loop Over Items
       done branch (after all 77 issues):
       -> Clean_code / Gemini / Sonnet4. / ...   parse each JSON answer, map taxonomy IDs to label + path
       -> Convert to File / Convert to File1     writes the result .xlsx
```

If an embedding or agent call fails, its error output goes straight back to **Loop Over Items**, so
the run continues; such issues appear as errors in the output and are excluded from Recall@K (N').

Some workflows still contain a few unconnected nodes left over from earlier experiments
(e.g. `Cleaner_ JSON Parser`, `ChatGPT4.1`, `Code in JavaScript` in `Cohere_Model_Claude`). They do
not run, and are kept so the files stay exactly as used.

## 5. Settings as they were run

| Setting | Value | Where |
|---|---|---|
| Reference examples `N_g` | 10 | `Search Qdrant Database` -> `limit: 10` |
| Taxonomy candidates from the tool | 10 | `Taxonomy tools` -> Limit / top-K |
| Labels requested from the model | exactly 6, ranked | system message (`Ranked_Taxonomy_IDs`) |
| Body length shown per example | first 200 characters | `Format` code node |
| Query embedding mode | same as documents: Cohere `input_type: search_document`, Gemini `taskType: RETRIEVAL_DOCUMENT`, OpenAI default | `Emedding Issue` node |
| OpenAI embedding dimensions | 3072 for the issue query (ground truth); 1536 for the taxonomy tool | `Emedding Issue` / `Embeddings OpenAI` node |
| Chat model IDs | `claude-sonnet-4-6`, `models/gemini-3.1-pro-preview`, `gpt-4.1`, `gpt-5.4` | Chat Model node |
| Temperature / max tokens | not set - provider defaults | Chat Model node options are empty |

These match the Python indexing scripts in `05_rag_pipeline/` (same models, dimensions and
collection names), so collections built with them work with these workflows unchanged.

## 6. Run an experiment

1. Start Qdrant and build both collections for the embedding provider of the workflow:
   ```bash
   python 05_rag_pipeline/build_taxonomy_index.py     --provider openai   # or gemini / cohere
   python 05_rag_pipeline/build_ground_truth_index.py --provider openai
   ```
2. Put the test set where the **Read/Write Files from Disk** node expects it: all 12 workflows read
   `C:\Users\<you>\.n8n-files\test1.xlsx` (n8n's default folder for local files). `test1.xlsx` contains the same
   77 issues, in the same order, as `06_evaluation/Testset.xlsx` (plus the original issue columns, without labels).
   In the published files the path reads `C:\Users\YOUR_WINDOWS_USER\.n8n-files\test1.xlsx` - after importing,
   open **Read/Write Files from Disk** and replace `YOUR_WINDOWS_USER` with your Windows user name
   (or point it to wherever you keep `test1.xlsx`).
3. Open the workflow and click **Execute Workflow**. A full run over 77 issues took 14-47 minutes
   depending on the chat model (report Table 5.4).
4. Download the Excel produced by **Convert to File**, save it in `06_evaluation/Recall_data_Excel/`,
   then run the evaluation (main README, step 06).

## 7. Exporting again after you change a workflow

```bash
n8n export:workflow --all --separate --output=<some temporary folder>
```

Then copy only the `*_Recall@K` files you changed into `05_rag_pipeline/n8n/` and, before
committing, remove the `pinData` and `shared` sections (they can contain test data and your e-mail)
and run `python tools/n8n_summary.py` and `python tools/check_project.py`.
