"""
Step 05-A: Index the PbD taxonomy into Qdrant  (report Section 4.4.1, Step 1.3)

Each taxonomy node (e.g. "6.4  Failure to enforce access permissions") is
embedded and stored with this payload:

    taxonomy_id, label, sources, path, top_level_category

The collection is DELETED and re-created on every run, so the script is safe to
re-run.

Usage (run from the project root):

    python 05_rag_pipeline/build_taxonomy_index.py --provider openai
    python 05_rag_pipeline/build_taxonomy_index.py --provider gemini
    python 05_rag_pipeline/build_taxonomy_index.py --provider cohere
"""

import argparse
import json
import uuid

from qdrant_client.models import Distance, PointStruct, VectorParams

from config import (
    PROVIDERS,
    TAXONOMY_FILE,
    get_qdrant_client,
    make_embedder,
)


def flatten_taxonomy(node: dict, path=None, result=None):
    """Walk the nested taxonomy JSON and return one dict per node that has a label."""
    path = path or []
    result = [] if result is None else result
    for key, value in node.items():
        if isinstance(value, dict) and "label" in value:
            result.append(
                {
                    "taxonomy_id": key,
                    "label": value["label"],
                    "sources": value.get("sources", []),
                    "path": path + [key],
                }
            )
        elif isinstance(value, dict):
            flatten_taxonomy(value, path + [key], result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--provider", choices=PROVIDERS, required=True, help="embedding provider")
    args = parser.parse_args()

    provider = PROVIDERS[args.provider]
    dims = provider.taxonomy_dims
    collection = provider.taxonomy_collection

    with open(TAXONOMY_FILE, encoding="utf-8") as f:
        items = flatten_taxonomy(json.load(f)["root"])
    print(f"Found {len(items)} taxonomy items")

    embed = make_embedder(provider, dims)
    qdrant = get_qdrant_client()

    if qdrant.collection_exists(collection):
        qdrant.delete_collection(collection)
    qdrant.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=dims, distance=Distance.COSINE),
    )

    points = []
    for item in items:
        try:
            vector = embed(item["label"])
        except Exception as exc:  # keep going; report at the end
            print(f"  ERROR embedding {item['taxonomy_id']}: {exc}")
            continue

        points.append(
            PointStruct(
                # deterministic id -> re-running does not create duplicates
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, item["taxonomy_id"])),
                vector=vector,
                payload={
                    "taxonomy_id": item["taxonomy_id"],
                    "label": item["label"],
                    "sources": ", ".join(map(str, item["sources"])),
                    "path": " > ".join(item["path"]),
                    "top_level_category": item["path"][0],
                },
            )
        )
        print(f"  ok {item['taxonomy_id']}: {item['label']}")

    qdrant.upsert(collection_name=collection, points=points)
    total = qdrant.get_collection(collection).points_count
    print(f"\nUploaded {len(points)} points to '{collection}' (collection now holds {total}).")


if __name__ == "__main__":
    main()
