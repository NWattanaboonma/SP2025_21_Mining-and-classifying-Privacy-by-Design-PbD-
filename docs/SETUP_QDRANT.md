# Running Qdrant locally (replaces the expired free cloud tier)

The original experiments used a free **Qdrant Cloud** cluster. Free clusters expire, so this
project now defaults to a **local Qdrant** running in Docker. Nothing else in the code changes:
the scripts only read `QDRANT_URL` / `QDRANT_API_KEY` from `.env`.

## 1. Start Qdrant

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then from the project root:

```bash
docker compose up -d qdrant
```

(or, without compose:)

```bash
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/qdrant_storage:/qdrant/storage" qdrant/qdrant
```

Check that it works - open <http://localhost:6333/dashboard> in your browser.
The `qdrant_storage/` folder keeps your vectors between restarts.

## 2. Point the project at it

In `.env` (copied from `.env.example`):

```
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

Leave `QDRANT_API_KEY` empty for a local instance.

## 3. Build the collections

Run once per embedding provider you want to reproduce (needs that provider's API key in `.env`):

```bash
python 05_rag_pipeline/build_taxonomy_index.py     --provider openai
python 05_rag_pipeline/build_ground_truth_index.py --provider openai
# repeat with --provider gemini and --provider cohere
```

Expected result (visible in the dashboard):

| Collection | Points | Vector size |
|---|---|---|
| `pbd-taxonomy-QA` | 60 | 1536 |
| `pbd-ground-truth-QA` | 308 | 3072 |
| `pbd-taxonomy-QA-gemini` / `pbd-ground-truth-QA-gemini` | 60 / 308 | 3072 |
| `pbd-taxonomy-QA-cohere` / `pbd-ground-truth-QA-cohere` | 60 / 308 | 1024 |

The scripts delete and re-create a collection each time, so re-running is safe.

## 4. Use it from n8n

In n8n create a **Qdrant API** credential:

| n8n runs... | Qdrant URL to enter |
|---|---|
| directly on your computer (`npx n8n` / desktop app) | `http://localhost:6333` |
| inside Docker | `http://host.docker.internal:6333` |

## Cost note

Rebuilding all collections calls the embedding APIs about 370 times per provider
(60 taxonomy labels + 308 issues) - a few cents in total.

## Using Qdrant Cloud instead

Create a free cluster at <https://cloud.qdrant.io>, then set in `.env`:

```
QDRANT_URL=https://<your-cluster-id>.<region>.cloud.qdrant.io:6333
QDRANT_API_KEY=<your key>
```

Free clusters are deleted after a period of inactivity, which is why local Docker is the default.
