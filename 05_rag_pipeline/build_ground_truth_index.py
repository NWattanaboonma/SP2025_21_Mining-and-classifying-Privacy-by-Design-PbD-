"""
Step 05-B: Index the ground-truth knowledge base into Qdrant
           (report Section 4.4.1, Steps 1.2-1.3)

Input : data/Ground_data.json  -> the 80% knowledge-base split (308 issues).
        Created by convert_xlsx_to_json.py from data/Ground_data.xlsx.
Output: one Qdrant collection of embedded issues. Each point's payload:

    issue_id, title, body, true_labels (e.g. "6.4, 6.5"), is_privacy (bool)

At classification time the pipeline retrieves the top-k (k = 10) most similar
issues from this collection and shows them to the LLM as in-context examples.

Usage (run from the project root):

    python 05_rag_pipeline/build_ground_truth_index.py --provider openai
    python 05_rag_pipeline/build_ground_truth_index.py --provider gemini
    python 05_rag_pipeline/build_ground_truth_index.py --provider cohere
"""

import argparse
import json
import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

from config import (
    GROUND_TRUTH_FILE,
    PROVIDERS,
    get_qdrant_client,
    make_embedder,
)

BATCH_SIZE = 25  # small batches avoid request-size timeouts with 3072-dim vectors


def positive_labels(issue: dict):
    """Taxonomy columns look like '6.4' / '2.3.3'; a value of True means 'assigned'."""
    return [k for k, v in issue.items() if v is True and k and k[0].isdigit()]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--provider", choices=PROVIDERS, required=True, help="embedding provider")
    args = parser.parse_args()

    provider = PROVIDERS[args.provider]
    dims = provider.ground_truth_dims
    collection = provider.ground_truth_collection

    with open(GROUND_TRUTH_FILE, encoding="utf-8") as f:
        issues = json.load(f)
    print(f"Loaded {len(issues)} ground-truth issues from {GROUND_TRUTH_FILE.name}")

    embed = make_embedder(provider, dims)
    qdrant = get_qdrant_client()

    if qdrant.collection_exists(collection):
        print(f"Deleting existing collection: {collection}")
        qdrant.delete_collection(collection)
    qdrant.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
    )

    batch, uploaded = [], 0
    for issue in issues:
        issue_id = issue.get("Issue_ID")
        title = issue.get("Title") or ""
        body = issue.get("Body") or ""
        text = f"{title} {body}".strip()[: provider.max_chars]
        if not text:
            print(f"  skip issue {issue_id}: no content")
            continue

        try:
            vector = embed(text)
        except Exception as exc:
            print(f"  ERROR issue {issue_id}: {exc}")
            continue

        labels = positive_labels(issue)
        batch.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, str(issue_id))),
                vector=vector,
                payload={
                    "issue_id": issue_id,
                    "title": title,
                    "body": body,
                    "true_labels": ", ".join(labels),
                    "is_privacy": len(labels) > 0,
                },
            )
        )
        print(f"  ok issue {issue_id}  labels={labels}")

        if len(batch) >= BATCH_SIZE:
            qdrant.upsert(collection_name=collection, points=batch, wait=True)
            uploaded += len(batch)
            batch = []

    if batch:
        qdrant.upsert(collection_name=collection, points=batch, wait=True)
        uploaded += len(batch)

    total = qdrant.get_collection(collection).points_count
    print(f"\nUploaded {uploaded} points to '{collection}' (collection now holds {total}).")


if __name__ == "__main__":
    main()
