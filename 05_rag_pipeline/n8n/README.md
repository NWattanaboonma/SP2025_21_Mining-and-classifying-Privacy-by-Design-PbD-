# n8n workflows (RQ3 identification pipeline)

> **Want to read a workflow?** Open [`WORKFLOWS.md`](WORKFLOWS.md) - a plain-English summary of all 12
> (models, collections, input file and the nodes in run order). The `.json` files are only for importing into n8n.

One workflow per experimental configuration - 12 in total, matching report Tables 5.4 and 5.5.
How to import and run them: [`../../docs/SETUP_N8N.md`](../../docs/SETUP_N8N.md).
The prompt inside them: [`../prompts/identification_prompt.md`](../prompts/identification_prompt.md).

**Naming:** `<EmbeddingModel>_Model_<ChatModel>_Recall@K.json` - the first name is the
**embedding** model, the second is the **chat** model. `GPT_Model` = OpenAI `text-embedding-3-large`.

| Report ID | File | Embedding model | Chat model | Qdrant collections |
|---:|---|---|---|---|
| 1 | `Cohere_Model_Claude_Recall@K.json` | embed-english-v3.0 | claude-sonnet-4-6 | `pbd-*-QA-cohere` |
| 2 | `Cohere_Model_Gemini_Recall@K.json` | embed-english-v3.0 | gemini-3.1-pro-preview | `pbd-*-QA-cohere` |
| 3 | `Cohere_Model_GPT4.1_Recall@K.json` | embed-english-v3.0 | gpt-4.1 | `pbd-*-QA-cohere` |
| 4 | `Cohere_Model_GPT5.4_Recall@K.json` | embed-english-v3.0 | gpt-5.4 | `pbd-*-QA-cohere` |
| 5 | `Gemini_Model_Claude_Recall@K.json` | gemini-embedding-001 | claude-sonnet-4-6 | `pbd-*-QA-gemini` |
| 6 | `Gemini_Model_GeminiPro_Recall@K.json` | gemini-embedding-001 | gemini-3.1-pro-preview | `pbd-*-QA-gemini` |
| 7 | `Gemini_Model_GPT4.1_Recall@K.json` | gemini-embedding-001 | gpt-4.1 | `pbd-*-QA-gemini` |
| 8 | `Gemini_Model_GPT5.4_Recall@K.json` | gemini-embedding-001 | gpt-5.4 | `pbd-*-QA-gemini` |
| 9 | `GPT_Model_Gemini_Recall@K.json` | text-embedding-3-large | gemini-3.1-pro-preview | `pbd-*-QA` |
| 10 | `GPT_Model_GPT4.1_Recall@K.json` | text-embedding-3-large | gpt-4.1 | `pbd-*-QA` |
| 11 | `GPT_Model_GPT5.4_Recall@K.json` | text-embedding-3-large | gpt-5.4 | `pbd-*-QA` |
| 12 | `GPT_Model_Claude_Recall@K.json` | text-embedding-3-large | claude-sonnet-4-6 | `pbd-*-QA` |

`pbd-*-QA` = the taxonomy collection `pbd-taxonomy-QA...` (used by the agent's tool) and the
ground-truth collection `pbd-ground-truth-QA...` (used for the 10 reference examples).

## What was changed when these files were added to the repository

The files were exported with `n8n export:workflow --all --separate` and then cleaned:

- kept only the 12 `*_Recall@K` workflows (older experiments were left out)
- removed pinned test data, the owner/sharing block (contained a personal e-mail) and n8n instance metadata
- input file: all 12 now read `test1.xlsx` (4 of them pointed to `test2.xlsx` / `checker.xlsx`, which were only used to resume runs after internet drops)
- replaced the expired Qdrant Cloud URL with `http://localhost:6333` (see `docs/SETUP_QDRANT.md`)
- **no API keys are stored in these files** - nodes only reference credentials by name; you create
  the credentials in your own n8n (see `docs/SETUP_N8N.md`)

Nothing else (nodes, prompts, code, model settings) was changed.
