"""
Shared configuration for the RAG pipeline scripts (step 05).

All secrets are read through `project_env.get_secret()` (from `.env` in the project
root, or the file named by ENV_FILE). NEVER hardcode API keys in source files.

Embedding providers evaluated in the report (Section 4.4.2):

    provider  model                    vector size   notes
    --------  -----------------------  ------------  ----------------------------------
    openai    text-embedding-3-large   3072 / 1536*  *taxonomy is truncated to 1536 dims
    gemini    gemini-embedding-001     3072
    cohere    embed-english-v3.0       1024
"""

import os
from dataclasses import dataclass
from pathlib import Path

import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from project_env import get_secret, get_setting  # noqa: E402  (all secrets go through here)

DATA_DIR = Path(__file__).resolve().parent / "data"
TAXONOMY_FILE = DATA_DIR / "PbD Issues Taxonomy.json"
GROUND_TRUTH_FILE = DATA_DIR / "Ground_data.json"


# --------------------------------------------------------------------------- #
# Qdrant
# --------------------------------------------------------------------------- #
# Default = a local Qdrant started with Docker (see docs/SETUP_QDRANT.md).
# For Qdrant Cloud, set QDRANT_URL and QDRANT_API_KEY in `.env`.
QDRANT_URL = get_setting("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = get_secret("QDRANT_API_KEY", required=False)


def get_qdrant_client(timeout: float = 180.0):
    from qdrant_client import QdrantClient

    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=timeout)


# --------------------------------------------------------------------------- #
# Embedding providers
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    env_key: str                # environment variable holding the API key
    taxonomy_dims: int          # vector size used for the taxonomy collection
    ground_truth_dims: int      # vector size used for the ground-truth collection
    taxonomy_collection: str
    ground_truth_collection: str
    max_chars: int              # issue text is truncated to this length before embedding


PROVIDERS = {
    "openai": Provider(
        name="openai",
        model="text-embedding-3-large",
        env_key="OPENAI_API_KEY",
        taxonomy_dims=1536,
        ground_truth_dims=3072,
        taxonomy_collection="pbd-taxonomy-QA",
        ground_truth_collection="pbd-ground-truth-QA",
        max_chars=20000,
    ),
    "gemini": Provider(
        name="gemini",
        model="gemini-embedding-001",
        env_key="GEMINI_API_KEY",
        taxonomy_dims=3072,
        ground_truth_dims=3072,
        taxonomy_collection="pbd-taxonomy-QA-gemini",
        ground_truth_collection="pbd-ground-truth-QA-gemini",
        max_chars=8000,
    ),
    "cohere": Provider(
        name="cohere",
        model="embed-english-v3.0",
        env_key="COHERE_API_KEY",
        taxonomy_dims=1024,
        ground_truth_dims=1024,
        taxonomy_collection="pbd-taxonomy-QA-cohere",
        ground_truth_collection="pbd-ground-truth-QA-cohere",
        max_chars=8000,
    ),
}


def require_key(provider: Provider) -> str:
    return get_secret(provider.env_key)


# --------------------------------------------------------------------------- #
# Embedding helper
# --------------------------------------------------------------------------- #
def make_embedder(provider: Provider, dims: int):
    """Return a function `embed(text) -> list[float]` for the given provider.

    The text is embedded as a *document* (to be stored and searched later).
    """
    key = require_key(provider)

    if provider.name == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=key)

        def embed(text: str):
            kwargs = {"model": provider.model, "input": text}
            if dims != 3072:  # text-embedding-3-large supports shortened vectors
                kwargs["dimensions"] = dims
            return client.embeddings.create(**kwargs).data[0].embedding

    elif provider.name == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)

        def embed(text: str):
            result = client.models.embed_content(
                model=provider.model,
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return result.embeddings[0].values

    elif provider.name == "cohere":
        import cohere

        client = cohere.Client(key)

        def embed(text: str):
            response = client.embed(
                texts=[text],
                model=provider.model,
                input_type="search_document",
            )
            return response.embeddings[0]

    else:  # pragma: no cover
        raise ValueError(f"Unknown provider: {provider.name}")

    return embed
